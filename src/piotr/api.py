"""Piotr API

This module allows to interact with/instrument Piotr virtual devices in a
pythonic way. It exposes a main class, :py:class:`Piotr`, that is able to
interact with running instances and to automate things.
"""
import re
import signal
import logging
import psutil
from os import kill, killpg
from os.path import basename
from time import sleep

from piotr.cmdline import CmdlineModule, module, command
from piotr.user import UserDirectory as ud
from piotr.util import confirm, enforce_root
from piotr.qemu import QemuGuestEnum, QemuPlatforms
from piotr.qemu.guest import QemuGuest, QemuGuestNotFound
from piotr.device import Device as _Device, create_device
from piotr.package import package_create, package_import, BadPackageError
from piotr.exceptions import DeviceConfigError

GDB_PROT_DONE = 'done'
GDB_PROT_CONN = 'connected'
GDB_PROT_RUN = 'running'

class DeviceNotFound(Exception):
    pass

# import avatar2 if available
try:
    from avatar2.protocols.gdb import GDBProtocol
    from avatar2.targets import TargetStates
    from avatar2.message import AvatarMessage, UpdateStateMessage, BreakpointHitMessage
    
    use_avatar2 = True

    class Debugger(object):
        """This class is a wrapper for avatar2's GDBProtocol class that will handle
        gdb-multiarch.
        """

        TARGET_UNKNOWN=-1
        TARGET_STOPPED=0
        TARGET_RUNNING=1
        TARGET_EXITED=2

        def __init__(self, inst_name, pid, ip=None, port=4444, gdb='gdb-multiarch'):
            self.log = logging.getLogger('gdb-%s-%d' % (inst_name, pid))
            self.state = self.TARGET_UNKNOWN
            self.__dbg_ip = '127.0.0.1' if ip is None else ip
            self.__port = port
            self.__debugger = GDBProtocol(
                origin=self,
                gdb_executable=gdb,
                async_message_handler=self.on_debugger_msg
            )
            self.__debugger.remote_connect(self.__dbg_ip, self.__port)
            self.__pid = pid
            self.__gdb_executable = gdb


        def __str__(self):
            return 'Debugger(pid=%d, gdb="%s", ip="", port=%d)' % (
                self.__pid,
                self.__gdb_executable,
                self.dbg_ip,
                self.__port
            )

        def __repr__(self):
            return str(self)


        def on_debugger_msg(self, message):
            """Process async message sent by gdb

            :param message: message
            """
            if isinstance(message, UpdateStateMessage):
                if message.state == TargetStates.RUNNING:
                    self.state = self.TARGET_RUNNING
                elif message.state == TargetStates.STOPPED:
                    self.state = self.TARGET_STOPPED
                elif message.state == TargetStates.EXITED:
                    self.state = self.TARGET_EXITED
            elif isinstance(message, BreakpointHitMessage):
                # breakpoint has been hit, target is stopped
                self.state = self.TARGET_STOPPED

        def wait(self, blocking=True):
            """Wait for target to be stopped."""
            while blocking:
                if self.state == self.TARGET_STOPPED or self.state == self.TARGET_EXITED:
                    break
                sleep(0.001)

        def cont(self, blocking=True):
            """Continue execution."""
            if self.__debugger.cont():
                while blocking:
                    if self.state == self.TARGET_RUNNING:
                        break
                    sleep(0.001)
                return True
            else:
                return False

        def stop(self):
            """Stop execution of target."""
            self.__debugger.stop()

        def set_abi(self, abi):
            """Set ABI."""
            self.__debugger.set_abi(abi)

        def set_breakpoint(self, line, hardware=False, temporary=False, regex=False, condition=None, ignore_count=0, thread=0, pending=False):
            """Inserts a breakpoint

            :param hardware: Hardware breakpoint
            :type hardware: bool
            :param temporary: Tempory breakpoint
            :type temporary: bool
            :param regex: If set, inserts breakpoints matching the regex
            :type regex: str
            :param condition: If set, inserts a breakpoint with specified condition
            :type condition: str
            :param ignore_count: Amount of times the bp should be ignored
            :type ignore_count: int
            :param thread: Threadno in which this breakpoints should be added
            :type thread: int
            :returns: The number of the breakpoint
            """
            return self.debugger.set_breakpoint(
                line,
                hardware=hardware,
                temporary=temporary,
                regex=regex,
                condition=condition,
                ignore_count=ignore_count,
                thread=thread,
                pending=pending
            )

        def remove_breakpoint(self, bkpt):
            """Deletes a breakpoint"""
            return self.__debugger.remove_breakpoint(bkpt)

        def write_memory(self, address, wordsize, val, num_words=1, raw=False):
            """Writes memory

            :param address:   Address to write to
            :param wordsize:  the size of the write (1, 2, 4 or 8)
            :param val: the written value
            :type val:  int if num_words == 1 and raw == False
                        list if num_words > 1 and raw == False
                        str or byte if raw == True
            :param num_words: The amount of words to read
            :param raw:       Specifies whether to write in raw or word mode
            :returns:         True on success else False
            """
            return self.__debugger.write_memory(
                address,
                wordsize,
                val,
                num_words=num_words,
                raw=raw
            )

        def read_memory(self, address, wordsize=4, num_words=1, raw=False):
            """reads memory
            :param address:   Address to write to
            :param wordsize:  the size of a read word (1, 2, 4 or 8)
            :param num_words: the amount of read words
            :param raw:       Whether the read memory should be returned unprocessed
            :return:          The read memory
            """
            return self.__debugger.read_memory(
                address,
                wordsize=wordsize,
                num_words=num_words,
                raw=raw
            )

        def read_register(self, reg):
            """Read register"""
            return self.__debugger.read_register(reg)

        def write_register(self, reg, value):
            return self.__debugger.write_register(reg, value)

        def step(self):
            return self.__debugger.step()

        def console_command(self, cmd, rexpect=GDB_PROT_DONE):
            return self.__debugger.console_command(cmd, rexpect=rexpect)

        def get_symbol(self, symbol):
            return self.__debugger.get_symbol(symbol)

        def set_gdb_variable(self, variable, value):
            return self.__debugger.set_gdb_variable(variable, value)


        def set_fork_mode(self, mode='child'):
            return self.__debugger.set_gdb_variable(
                'follow-fork-mode',
                mode
            )
except Exception as exc:
    use_avatar2 = False

    class Debugger(object):
        def __init__(self, inst_name, pid, ip=None, port=4444, gdb='gdb-multiarch'):
            raise Exception('Debugger class cannot be used because Avatar2 is not installed.')


class Process:
    """This class holds information about a process on the emulated system."""

    def __init__(self, pid=-1, user=None, path=None):
        self.__pid = pid
        self.__user = user
        self.__path = path

    def __repr__(self):
        return str(self)

    def __str__(self):
        return 'Process(pid=%d, user="%s", path="%s")' % (
            self.__pid,
            self.__user if self.__user is not None else '?',
            self.__path if self.__path is not None else '?'
        )

    @property
    def pid(self):
        return self.__pid

    @property
    def user(self):
        return self.__user

    @property
    def path(self):
        return self.__path


class Instance:
    """
    This class represents a Piotr running device instance and allows to interact
    with it, execute commands into the emulated host and target (if Qemu agent
    is supported by the device), enumerate and manipulate process.

    :param guest: Qemu guest
    :type guest: piotr.qemu.QemuPlatform
    :param device: Name of parent device, as referenced in Piotr devices list
    :type device: str
    """
    def __init__(self, guest, device):
        self.__guest= guest
        self.__pid = guest.get_pid()
        self.__device = Device(device)
        self.__sock = guest.get_sock()
        self.__name = guest.get_name()
        self.debugger = None

    def __str__(self):
        return 'Instance(name="%s", device="%s")' % (self.__name, self.__device.name)

    def __repr__(self):
        return str(self)

    @property
    def device(self):
        return self.__device

    @property
    def name(self):
        return self.__name

    @property
    def sock(self):
        return self.__sock

    def stop(self):
        """
        Stop instance.
        """
        # Loop on all processes and look for our instance
        for p in psutil.process_iter():
            p_env = p.environ()
            if 'PIOTR_INSTNAME' in p_env and p_env['PIOTR_INSTNAME'] == self.__name:
                p.send_signal(signal.SIGTERM)

        # Clean the execution environment
        self.__guest.stop()


    def exec_host(self, command, wait=True):
        """
        Execute a command in host.
        """
        nibbles = command.split(' ')
        if len(nibbles) > 0:
            executable = nibbles[0]
            args = [arg for arg in nibbles[1:] if len(arg)>0]
            guest = QemuGuest(self.__name)
            return guest.run_command(executable, args, wait=wait)
        else:
            return None


    def exec_target(self, command, wait=True):
        """Execute a command in guest.

        :param command: command to execute
        :type command: str
        :param return_output: wait for the process to end and return output
        :type return_output: bool
        :return: command output or executable PID
        """
        nibbles = command.split(' ')
        if len(nibbles) > 0:
            executable = nibbles[0]
            args = [arg for arg in nibbles[1:] if len(arg)>0]

            guest = QemuGuest(self.__name)
            guest_args = ['/target']
            guest_args.extend([executable])
            guest_args.extend(args)
            return guest.run_command(
                'chroot', guest_args,
                wait=wait
            )
        else:
            # Error.
            return None

    def debug(self, pid, ip='0.0.0.0', port=4444, gdb_executable='gdb-multiarch'):
        """
        Runs a gdb server and attaches it to a process.
        """
        # Attach a gdbserver to the target PID
        guest = QemuGuest(self.__name)
        result = guest.run_command(
            'gdbserver', [
                '%s:%d' % (ip, port),
                '--attach',
                '%d' % pid
            ],
            wait=False
        )

        # is it a fail ?
        if result is None:
            return None

        # If avatar2 is installed, return a GDBTarget
        if use_avatar2:

            # Wait for gdbserver to be available
            sleep(2)
            
            # Instanciate our GDB
            self.debugger = Debugger(
                self.__name,
                pid,
                ip=None if ip=='0.0.0.0' else ip,
                port=port,
                gdb=gdb_executable
            )
            return self.debugger
        else:
            return result

    def ps(self):
        """
        Run `ps` on this target and return a list of processes.

        :return: list of processes
        """
        # Runs ps command
        guest = QemuGuest(self.__name)
        result = guest.run_command(
            'ps', [],
            wait=True
        )

        # Parse result
        processes = []
        for l in result.split(b'\n')[1:]:
            res = re.match(b'^\s+([0-9]+)\s+(\S+)\s+(.*)$', l)
            if res is not None:
                processes.append(
                    Process(
                        pid=int(res.group(1)),
                        user=res.group(2).decode('latin-1'),
                        path=res.group(3).decode('latin-1')
                    )
                )

        return processes

    def pid(self, process_name):
        """Find process ID from process name
        :param process_name: process name
        :type process_name: str
        :return: PID of the process, None on error
        """
        processes = self.ps()
        for process in processes:
            if process.path.split(' ')[0] == process_name:
                return process.pid

        # Not found :(
        return None
        

    def kill(self, pid, sig=9):
        """
        Kill a processus.
        """
        guest = QemuGuest(self.__name)
        result = guest.run_command(
            'kill', [
                '-%d' % sig,
                '%d' % pid
            ],
            wait=True
        )
        return result

    def target_start(self):
        """
        Run target in host.
        """
        self.exec_host('target-start', wait=False)

    def get_sysroot(self):
        """Return this instance root path"""
        return self.__device.get_sysroot()



class Device:
    """
    API Device object.
    """

    def __init__(self, deviceName):
        self.__device = deviceName

    def __str__(self):
        return 'Device(name="%s")' % self.__device

    def __repr__(self):
        return str(self)

    @property
    def name(self):
        return self.__device

    def run(self, alias=None, background=False):
        """
        Run emulated device.
        """
        if ud.get().hasDevice(self.__device):
            device = _Device(self.__device)
            device_name = alias

            # Check if we can emulate this platform
            if QemuPlatforms.has(device.getPlatform()):
                platform_clazz = QemuPlatforms.get(device.getPlatform())
            else:
                warning('Device', 'Unknown qemu platform `%s`. Falling back to `virt`.' % device.getPlatform())
                platform_clazz = QemuPlatforms.get('virt')

            guest = platform_clazz(device, name=device_name)

            # Check if specific privileges are required.
            if guest.requires_privileges():
                enforce_root()

            # Start emulated device
            guest.start(background=background)
            if not background:
                guest.wait()
                guest.stop()
                return None
            else:
                return Instance(
                    guest,
                    self.__device
                )
        else:
            raise DeviceNotFound()

    def get_sysroot(self):
        """Return this device root fs path"""
        if ud.get().hasDevice(self.__device):
            device = _Device(self.__device)
            return device.getRootfsPath()
        else:
            return None


class Piotr:
    """
    Piotr main API.
    """

    @staticmethod
    def devices():
        """
        Enumerate registered devices.
        """
        for device in ud.get().getDevices():
            yield Device(device.name)

    @staticmethod
    def instances():
        """
        Enumerate running instances.
        """
        qemu_enum = QemuGuestEnum()
        for pid,instance,sock,inst_name in qemu_enum.listGuests():
            yield Instance(pid, instance, sock, inst_name)

    @staticmethod
    def instance(inst_name):
        """
        Find an existing instance by name
        """
        for instance in Piotr.instances():
            if instance.name == inst_name:
                return instance

