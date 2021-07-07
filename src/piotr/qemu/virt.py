from os import environ, mkdir
from os.path import exists, join, dirname, basename
from pathlib import Path

from piotr.qemu import qemu_platform, QemuGuestEnum
from piotr.util.logger import info, warning, debug, error
from piotr.util.namegen import get_random_name
from piotr.qemu.platform import QemuPlatform

@qemu_platform('virt')
class QemuPlatformVirt(QemuPlatform):
    """
    Qemu-system-arm 'virt' platform
    """

    def __init__(self, device, name=None):
        super().__init__(device, name)

    

    
    