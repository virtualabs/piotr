"""
Device commandline module.

Registers the DeviceModule class into the ModulesRegistry and expose the
following
"""
import signal
from os import kill
from os.path import basename
from piotr.cmdline import CmdlineModule, module, command
from piotr.user import UserDirectory as ud
from piotr.util import confirm, enforce_root
from piotr.qemu import QemuGuestEnum, QemuPlatforms
from piotr.device import Device, create_device
from piotr.package import package_create, package_import, BadPackageError
from piotr.exceptions import DeviceConfigError, KernelNotFound


@module('device', 'List, import, export emulated devices')
class DeviceModule(CmdlineModule):

    def __init__(self):
        super().__init__()

    @command('List available devices')
    def list(self, options):
        """
        List available devices.
        """
        self.title(' Installed devices:')
        print('')
        count = 0
        for device in ud.get().getDevices():
            device_line = (self.term.bold + '{device:<20}' + self.term.normal + \
                '{extra:<60}').format(
                device='  > %s:' % basename(device.getPath()),
                extra='{name} (platform: {platform}, cpu: {cpu})'.format(
                    name=device.name,
                    platform=device.platform if device.platform is not None else 'generic',
                    cpu=device.cpu if device.cpu is not None else '-'
            ))
            print(device_line)
            count +=1
        print('')
        print(' %d device(s) available' % count)
        print('')


    @command('List running instances')
    def running(self, options):
        """
        List running instances of devices
        """
        count = 0
        self.title(' Running instances:\n')
        self.important('    {col_inst_name:<40}{col_device_name:<40}'.format(
            col_inst_name='Instance name',
            col_device_name='Device'
        ))
        qemu_enum = QemuGuestEnum()
        for pid,instance,sock,inst_name in qemu_enum.listGuests():
            device = ud.get().getDevice(instance)
            instance_line = '  > {pid:<40}{device:<40}'.format(
                #pid=pid,
                pid=inst_name,
                device=device.name if device is not None else '?'
            )
            print(instance_line)
            count += 1
        print('\n %d running instance(s)\n' % count)

        if count == 0:
            enforce_root()


    @command('Start an emulated device', ['device name','?instance name'])
    def start(self, options):
        """
        Start a specific device in qemu.
        """
        if len(options) >= 1:
            if ud.get().hasDevice(options[0]):
                try:
                    device = Device(options[0])
                    if len(options) >= 2:
                        device_name = options[1]
                    else:
                        device_name = None
                except DeviceConfigError as devConfigError:
                    self.error("Error while parsing configuration file: %s" % devConfigError.get_message())
                    return
                except KernelNotFound as kernelError:
                    self.error("Unable to find a suitable kernel for device %s ! Please check your available kernels and device configuration." % options[0])
                    return

                # If this device has network redirections, we need to check it won't conflict
                # with the redirections already in place in running instances.
                if device.hasRedirects():
                    device_redirects = device.getRedirects()
                    used_ports = []
                    for redirect in device_redirects:
                        used_ports.append('%s/%d' % (redirect['proto'], redirect['local']))
                    for pid, devname, devsock, devinst in QemuGuestEnum.listGuests():
                        _d = Device(devname)
                        if _d.hasRedirects():
                            for redirect in _d.getRedirects():
                                redir = '%s/%d' % (redirect['proto'], redirect['local'])
                                if redir in used_ports:
                                    # Port is already in use, cannot start Qemu !
                                    self.error(
                                        'Target device requires local port %s available, but it is already used by instance "%s"' % (
                                            redir,
                                            devinst
                                        )
                                    )
                                    return

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
                guest.start()
                guest.wait()
                guest.stop()
            else:
                self.error('Unable to find the device %s' % options[0])
        else:
            self.important('You must provide a device name to emulate.')

    @command('Stop a running instance', ['instance name'])
    def stop(self, options):
        """
        Stop a running instance of a device.
        """
        if len(options) >= 1:
            # Get instance name
            instance = options[0]

            # First, check if the running PID belong to one of our running devices
            pids = {}
            for pid,guest,sock,inst_name in QemuGuestEnum().listGuests():
                pids[inst_name] = pid

            if len(pids.keys()) == 0:
                enforce_root()
                self.error('No running instance found.')
            else:
                if instance in pids:
                    # Try to send the kill signal to this PID
                    try:
                        kill(pids[instance], signal.SIGTERM)
                        print('Running instance has been killed.')
                    except OSError as error:
                        self.error('Unable to kill this running instance')
                else:
                    self.error('Running instance not found !')
        else:
            self.important('You must provide the instance name to stop.')

    @command('Remove a device', ['device name'])
    def remove(self, options):
        """
        Remove a device from directory
        """
        if len(options) >= 1:
            device_name = options[0]
            if ud.get().hasDevice(device_name):

                # Root access required
                enforce_root()

                if confirm('Are you sure you want to remove this device'):
                    ud.get().removeDevice(device_name)
                    self.important('Device %s successfully removed.' % device_name)
                else:
                    self.warning('Device has not been removed (canceled by user)')
            else:
                self.error('Unknown device %s' % device_name)
        else:
            self.important('You must specify a device name to remove.')

    @command('Import a device', ['device package path'])
    def add(self, options):
        """
        Import a device package
        """
        if len(options) >= 1:
            package_path = options[0]

            # Root access required
            enforce_root()

            if package_path.endswith('.piotr'):
                try:
                    package_import(options[0])
                except BadPackageError as error:
                    self.error('Cannot import package %s.' % options[0])
            else:
                self.important('Device package must have extension `.piotr`')

    @command('Export a device', ['device name', 'target file'])
    def export(self, options):
        """
        Export a device to a specific output file
        """
        if len(options) >= 2:
            # Get device name
            devname = options[0]

            # Root access required
            enforce_root()

            # Target file must end with '.piotr'
            target_file = options[1]
            if not target_file.endswith('.piotr'):
                target_file += '.piotr'

            # Get selected device
            if ud.get().hasDevice(devname):
                device = Device(devname)
                package_create(device, target_file)
                print('Package %s has been created.' % target_file)
            else:
                self.error('Cannot find target device.')
        else:
            self.important('You must provide the device name in order to export its content.')


    @command('Create a new device with default skeleton', ['device name'])
    def create(self, options):
        """
        Create a new device skeleton
        """
        if len(options) >= 1:
            # Get device name
            devname = str(options[0])

            # Root access required
            enforce_root()

            # Call our helper to create a device skeleton
            if ud.get().hasDevice(devname):
                self.error('Device `%s` already exists !' % devname)
            else:
                try:
                    # Create device skeleton
                    create_device(devname)
                    self.important('Device ̀`%s` created.' % devname.replace('/','_'))
                except Exception as error:
                    print(error)
                    self.error('Unable to create device `%s`' % devname)
