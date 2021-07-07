"""
Kernel commandline module.

Registers the DeviceModule class into the ModulesRegistry and expose the
following methods:

- list: list kernels installed in our user directory
- add: add kernel in our user directory
- remove: remove kernel from our user directory

"""
from os.path import basename
from piotr.cmdline import CmdlineModule, module, command
from piotr.user import UserDirectory as ud
from piotr.util import confirm

@module('kernel', 'List, add, remove Linux kernels')
class KernelModule(CmdlineModule):

    def __init__(self):
        super().__init__()

    @command('List available kernels')
    def list(self, options):
        """
        List available kernels.
        """
        self.title(' Installed kernels:')
        print('')
        count = 0
        for kernel in ud.get().getKernels():
            kernel_line = (self.term.bold + '{kernel:<80}' + self.term.normal + \
                '\n    {extra}\n').format(
                kernel='  > %s' % kernel['name'],
                extra='Linux version {version}, platform: {platform}, cpu: {cpu} ({endian})'.format(
                    version=kernel['version'],
                    platform=kernel['platform'] if 'platform' in kernel else 'unknown',
                    cpu=kernel['cpu'],
                    endian='little-endian' if kernel['endian']=='little' else 'big-endian'
                )
            )
            print(kernel_line)
            count += 1

        print('')
        print(' %d kernel(s) available' % count)
        print('')

    @command('Remove a specific kernel', ['kernel'])
    def remove(self, options):
        """
        Remove kernel from our repository.

        Expects options[0] to be the name of the target kernel to remove.
        """
        if len(options) >= 1:
            # Ask for confirm
            if confirm('Are you sure to remove this kernel'):
                # Remove kernel by name
                if ud.get().removeKernel(options[0]):
                    print('Kernel %s successfully removed.' % options[0])
                else:
                    self.error('An error occurred while removing kernel.')
        else:
            self.important(' You must provide a kernel name to remove.')


    @command('Add a specific kernel', ['path'])
    def add(self, options):
        """
        Add kernel to our kernel repository.
        """
        if len(options) >= 1:
            if ud.get().addKernel(options[0]):
                print('Kernel successfully added to our registry.')
            else:
                self.error('An error occurred while importing kernel.')
        else:
            self.important(' You must provide a kernel file to add.')
