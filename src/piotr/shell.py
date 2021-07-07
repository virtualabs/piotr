"""
Piotr Shell helper.

This module provides a single function called `guest_shell` that executes
shell commands into a host or a guest (a target running inside a host).
"""
import os.path
import sys
import argparse
import logging
from blessings import Terminal
from piotr.util.logger import Logger
from piotr.exceptions import SudoRequired

from piotr.qemu import QemuGuestEnum
from piotr.qemu.guest import QemuGuest, QemuGuestNotFound
from piotr.util.cmdparser import parse_command

term = Terminal()

def __split_padding(message):
    for i in range(len(message)):
        if message[i]!=' ' and message[i]!='\t':
            return (message[:i], message[i:])
    return message

def error(message):
    """
    Display an error in red.
    """
    padding,message = __split_padding(message)
    print(padding + term.red + message + term.normal)


def show_warning():
    """
    Display a warning telling the user this is not a *real* shell, so he/she
    wouldn't expect it to work as is.
    """
    print('>> PIOTR v1.0')
    print('>>')
    print('>> This is an interactive pseudo-shell with limitations:')
    print('>>   - all commands are executed from the root directory')
    print(">>   - stderr is not captured and won't be displayed")
    print(">>   - no commands history")
    print(">>   - no real-time standard output, commands are executed")
    print(">>     and results shown once done")
    print('')


def get_instance_from_name(inst_name):
    """
    Retrieve
    """
    pass

def interactive_shell(guest, guest_shell=False):
    """
    Spawn an interactive shell
    """
    if guest_shell:
        prompt = '[Guest]# '
    else:
        prompt = '[Host]# '

    # Display a warning about this pseudo-shell
    show_warning()

    command = ''
    sys.stdout.write(prompt)
    while command.split(' ')[0].lower() != 'exit':
        command = input()
        if command != 'exit':
            args = parse_command(command)

            if len(args)>0:
                if guest_shell:
                        guest_args = ['/target']
                        guest_args.extend(args)
                        result = guest.run_command(
                            'chroot', guest_args
                        )
                else:
                    result = guest.run_command(args[0], args[1:])

                if result is None:
                    error('Command %s not found.' % command)
                else:
                    # Display result
                    sys.stdout.write(result.decode("utf-8"))
            sys.stdout.write(prompt)

def debug_process():
    """
    Debug a specific process
    """
    parser = argparse.ArgumentParser('Piotr Gdbserver helper')
    parser.add_argument(
        '--log-level',
        '-l',
        dest='loglevel',
        type=str,
        default='warning',
        help='Specifies the logging level (info, debug, warning, error, critical)'
    )
    parser.add_argument(
        '--instance',
        '-t',
        dest='instance',
        type=str,
        default=None,
        help='Specifies the target running instance'
    )
    parser.add_argument(
        '--ip',
        '-i',
        dest='target_ip',
        type=str,
        default='0.0.0.0',
        help='Specifies the IP address gdbserver will listen on on the target device'
    )
    parser.add_argument(
        '--port',
        '-p',
        dest='target_port',
        type=int,
        default=4444,
        help='Specifies the port gdbserver will use on the target device'
    )
    parser.add_argument(
        'pid',
        type=int,
        help='PID of target process running on target device'
    )

    # Parse args
    args = parser.parse_args()
    try:
        # Pick instance
        if args.instance is None:
            # Get instances names
            instances = QemuGuestEnum.getInstanceNames()
            # If there is only one instance, get it
            if len(instances) == 1:
                instance = instances[0]
            elif len(instances) > 1:
                # Too many instances, user must specify a target instance
                error('Multiple instances running, you must specify one with `-i` option.')
                sys.exit(-1)
            else:
                # No running instance or not enough rights
                error('No instance running, or you may not have the permission to enumerate processes.')
                sys.exit(-2)
        else:
            instance = args.instance

        # Enumerate processes
        guest = QemuGuest(instance)
        print('Starting gdbserver on the target instance (%s)' % guest.name)
        result = guest.run_command(
            'gdbserver', [
                '%s:%d' % (args.target_ip, args.target_port),
                '--attach',
                '%d' % args.pid
            ],
            wait=False
        )

        if result is None:
            error('`gdbserver` command not available.')
        else:
            print('Gdbserver is now running on instance with PID %d' % result)

    except QemuGuestNotFound as notfound:
        error('Instance %s not found.' % args.instance)
    except Exception as err:
        error(str(err))



def host_ps():
    """
    Enumerate processes from host.
    """
    parser = argparse.ArgumentParser('Piotr Shell helper')
    parser.add_argument(
        '--log-level',
        '-l',
        dest='loglevel',
        type=str,
        default='warning'
    )
    parser.add_argument(
        '--instance',
        '-t',
        dest='instance',
        type=str,
        default=None
    )

    # Parse args
    args = parser.parse_args()
    try:
        # Pick instance
        if args.instance is None:
            # Get instances names
            instances = QemuGuestEnum.getInstanceNames()
            # If there is only one instance, get it
            if len(instances) == 1:
                instance = instances[0]
            elif len(instances) > 1:
                # Too many instances, user must specify a target instance
                error('Multiple instances running, you must specify one with `-i` option.')
                sys.exit(-1)
            else:
                # No running instance or not enough rights
                error('No instance running, or you may not have the permission to enumerate processes.')
                sys.exit(-2)
        else:
            instance = args.instance

        # Enumerate processes
        guest = QemuGuest(instance)
        result = guest.run_command(
            '/bin/ps', ['aux']
        )

        if result is None:
            error('`ps` command not available.')
        else:
            # Display result
            sys.stdout.write(result.decode("utf-8"))

    except QemuGuestNotFound as notfound:
        error('Instance %s not found.' % args.instance)
    except Exception as err:
        error(str(err))


def guest_shell():
    """
    Main routine for piotr-shell.
    """
    parser = argparse.ArgumentParser('Piotr Shell helper')
    parser.add_argument(
        '--log-level',
        '-l',
        dest='loglevel',
        type=str,
        default='warning'
    )
    parser.add_argument(
        '--instance',
        '-t',
        dest='instance',
        type=str,
        default=None
    )
    parser.add_argument(
        '--guest',
        '-g',
        dest='guest',
        action='store_true',
        default=False
    )
    parser.add_argument(
        '--interactive',
        '-i',
        dest='interactive',
        action='store_true',
        default=False
    )
    parser.add_argument(
        'command',
        nargs=argparse.REMAINDER,
        default=[]
    )

    # Parse args
    args = parser.parse_args()
    try:
        # Pick instance
        if args.instance is None:
            # Get instances names
            instances = QemuGuestEnum.getInstanceNames()
            # If there is only one instance, get it
            if len(instances) == 1:
                instance = instances[0]
            elif len(instances) > 1:
                # Too many instances, user must specify a target instance
                error('Multiple instances running, you must specify one with `-i` option.')
                sys.exit(-1)
            else:
                # No running instance or not enough rights
                error('No instance running, or you may not have the permission to enumerate processes.')
                sys.exit(-2)
        else:
            instance = args.instance


        # If interactive mode
        if args.interactive:

            # Execute command in guest
            guest = QemuGuest(instance)

            interactive_shell(guest, args.guest)
        else:
            # Check command
            if len(args.command) >= 1:
                command = args.command[0]
                command_args = args.command[1:]

                # Execute command in guest
                guest = QemuGuest(instance)

                if args.guest:
                        guest_args = ['/target']
                        guest_args.extend([command])
                        guest_args.extend(command_args)
                        result = guest.run_command(
                            'chroot', guest_args
                        )
                else:
                    result = guest.run_command(command, command_args)

                if result is None:
                    error('Command %s not found.' % command)
                else:
                    # Display result
                    sys.stdout.write(result.decode("utf-8"))
            else:
                error('You must provide a command to execute.')

    except QemuGuestNotFound as notfound:
        error('Instance %s not found.' % args.instance)
    except Exception as err:
        error(str(err))
