"""
FS commandline module.

Allows to:

- list host filesystems
- remove a specific host filesystem
- add a specific host filesystem
"""

from os.path import basename
from piotr.cmdline import CmdlineModule, module, command
from piotr.user import UserDirectory as ud
from piotr.util import confirm

@module('fs', 'List, add, remove Piotr host filesystems')
class FsModule(CmdlineModule):

    def __init__(self):
        super().__init__()

    @command('List available host filesystems')
    def list(self, options):
        """
        List available FSs.
        """
        self.title(' Installed host filesystems:')
        print('')
        count = 0
        for fs in ud.get().getHostFilesystems():
            fs_line = (self.term.bold + '{fs:<40}' + self.term.normal + \
                '{extra:<40}').format(
                fs='  > %s' % fs['file'],
                extra='(version {version}, platform: {platform}, cpu: {cpu} ({endian}), type: {fstype})'.format(
                    version=fs['version'],
                    platform=fs['platform'],
                    cpu=fs['cpu'],
                    fstype=fs['type'],
                    endian='little-endian' if fs['endian']=='little' else 'big-endian'
                )
            )
            print(fs_line)
            count += 1

        print('')
        print(' %d filesystem(s) available' % count)
        print('')

    @command('Remove a specific filesystem', ['fs name'])
    def remove(self, options):
        """
        Remove filesystem from our repository.

        Expects options[0] to be the name of the target filesystem to remove.
        """
        if len(options) >= 1:
            # Ask for confirm
            if confirm('Are you sure to remove this filesystem'):
                # Remove kernel by name
                if ud.get().removeHostFs(options[0]):
                    print('Filesystem %s successfully removed.' % options[0])
                else:
                    self.error('An error occurred while removing host filesystem.')
        else:
            self.important(' You must provide a host filesystem name to remove.')


    @command('Add a specific host filesystem', ['path'])
    def add(self, options):
        """
        Add kernel to our kernel repository.
        """
        if len(options) >= 1:
            if ud.get().addHostFs(options[0]):
                print('Host filesystem successfully added to our registry.')
            else:
                self.error('An error occurred while importing host filesystem.')
        else:
            self.important(' You must provide a filesystem file to add.')
