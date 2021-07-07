"""
DTB commandline module.

Allows to:

- list DTBs
- remove a specific DTB
- add a specific DTB
"""

from os.path import basename
from piotr.cmdline import CmdlineModule, module, command
from piotr.user import UserDirectory as ud
from piotr.util import confirm

@module('dtb', 'List, add, remove DTB files')
class DtbModule(CmdlineModule):

    def __init__(self):
        super().__init__()

    @command('List available DTBs')
    def list(self, options):
        """
        List available DTBs.
        """
        self.title(' Installed DTBs:')
        print('')
        count = 0
        for dtb in ud.get().getDtbs():
            dtb_line = (self.term.bold + '{dtb:<40}' + self.term.normal + '{extra:<40}').format(
                dtb='  > %s' % dtb['name'],
                extra='(platform: {platform}, cpu: {cpu})'.format(
                    platform=dtb['platform'],
                    cpu=dtb['cpu']
                )
            )
            print(dtb_line)
            count += 1

        print('')
        print(' %d DTB(s) available' % count)
        print('')

    @command('Remove a specific DTB', ['dtb name'])
    def remove(self, options):
        """
        Remove DTB from our repository.

        Expects options[0] to be the name of the target DTB to remove.
        """
        if len(options) >= 1:
            # Ask for confirm
            if confirm('Are you sure to remove this DTB'):
                # Remove kernel by name
                if ud.get().removeDtb(options[0]):
                    ('DTB %s successfully removed.' % options[0])
                else:
                    self.error('An error occurred while removing DTB.')
        else:
            self.important(' You must provide a DTB name to remove.')


    @command('Add a specific DTB', ['path'])
    def add(self, options):
        """
        Add DTB to our DTB repository.
        """
        if len(options) >= 1:
            if ud.get().addDtb(options[0]):
                print('DTB successfully added to our registry.')
            else:
                self.error('An error occurred while importing DTB.')
        else:
            self.important(' You must provide a DTB to add.')
