"""
Show all information (call list() on every possible module).
"""

from os.path import basename
from piotr.cmdline import CmdlineModule, module, ModulesRegistry
from piotr.user import UserDirectory as ud
from piotr.qemu import QemuGuestEnum


@module('showall', "Show all available devices, DTBs, filesystems and kernels")
class ShowAllModule(CmdlineModule):
    """
    Call every module's list() method if any.
    """

    def __init__(self):
        super().__init__()

    def help(self):
        """
        Use the help function to call every possible module list().
        """
        # Loop on every module and call the list() method if available.
        for name, clazz in ModulesRegistry.enumerate():
            if hasattr(clazz, 'list'):
                inst = clazz()
                list_method = getattr(inst, 'list')
                if callable(list_method):
                    list_method([])
            print('')
