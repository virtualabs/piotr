"""
Piotr main utility

Main commands:

$ piotr list guests
"""

import argparse
import logging

from blessings import Terminal

from os.path import basename
from piotr.device import Device
from piotr.user import UserDirectory
from piotr.util.logger import Logger
from piotr.exceptions import SudoRequired

# Load command line modules
from piotr.cmdline import ModulesRegistry
from piotr.cmdline.device import DeviceModule
from piotr.cmdline.kernel import KernelModule
from piotr.cmdline.fs import FsModule
from piotr.cmdline.dtb import DtbModule
from piotr.cmdline.showall import ShowAllModule

LOG_LEVELS = {
    'info': logging.INFO,
    'debug': logging.DEBUG,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
}

TERM = Terminal()

def print_modules():
    # List available modules
    print('available modules:\n')
    for module_name, module_clazz in ModulesRegistry.enumerate():
        if hasattr(module_clazz, 'module_desc'):
            module_desc = getattr(module_clazz, 'module_desc')
        else:
            module_desc = ''
        print(
            (TERM.bold + '  {module:<40}' + TERM.normal + '{desc:<40}').format(
                module=module_name,
                desc=module_desc
            )
        )


def main():
    parser = argparse.ArgumentParser('Piotr - Python IoT Research Framework')
    parser.add_argument(
        '--log-level',
        '-l',
        help='Debug level (info, debug, warning, error, critical)',
        type=str,
        default='error',
        dest='loglevel'
    )
    parser.add_argument(
        'module',
        nargs='?',
        default=None,
    )
    parser.add_argument(
        'options',
        nargs='*',
        default=[],
    )
    # Parse arguments
    args = parser.parse_args()
    if args.module is not None:
        # Process loglevel
        if args.loglevel in LOG_LEVELS:
            Logger.setLevel(LOG_LEVELS[args.loglevel])
        else:
            print('[WARNING] Unknown log level (%s)' % args.loglevel)

        # Dispatch command
        try:
            if ModulesRegistry.has(args.module.lower()):
                module = ModulesRegistry.get(args.module.lower())()
                if len(args.options) >= 1:
                    module.dispatch(args.options[0], args.options[1:])
                else:
                    module.help()
            else:
                print(TERM.bold + 'You must specify a valid command !' + TERM.normal)
                print('')
                print_modules()
        except SudoRequired as error:
            print(TERM.bold + 'This command requires root access, run piotr with sudo.' + TERM.normal)

    else:
        # Show help
        parser.print_help()
        print_modules()

if __name__ == '__main__':
    main()
