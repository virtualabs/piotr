"""
Qemu module

This module provides a series of helpers in order to support new Qemu platforms,
such as `versatilepb`, `vexpress`, `virt` or others.

The default implementation is QemuPlatform, which provides a basic setup:
- one hard drive
- one network tap with own nic
- one nic
"""
import sys
import psutil

class QemuGuestEnum(object):
    """
    Qemu Piotr guest enumerator.
    """

    @staticmethod
    def listGuests():
        """
        List running Qemu guests.
        """
        for proc in psutil.process_iter():
            try:
                # Get environment
                procEnv = proc.environ()
                if 'PIOTR_GUEST' in procEnv:
                    if 'qemu' in proc.exe():
                        yield (
                            proc.pid,
                            procEnv['PIOTR_GUEST'],
                            procEnv['PIOTR_SOCK'] if 'PIOTR_SOCK' in procEnv else None,
                            procEnv['PIOTR_INSTNAME'] if 'PIOTR_INSTNAME' in procEnv else None
                        )
            except psutil.AccessDenied as exc:
                pass

    @staticmethod
    def getInstanceNames():
        """
        Check if an instance name already exists.
        """
        names = []
        for proc in psutil.process_iter():
            try:
                # Get environment
                procEnv = proc.environ()
                if 'PIOTR_GUEST' in procEnv:
                    if 'qemu' in proc.exe():
                        if 'PIOTR_INSTNAME' in procEnv:
                            names.append(procEnv['PIOTR_INSTNAME'])
            except psutil.AccessDenied as exc:
                pass

        return names

    @staticmethod
    def getInstanceByName(name):
        for proc in psutil.process_iter():
            try:
                # Get environment
                procEnv = proc.environ()
                if 'PIOTR_GUEST' in procEnv:
                    if 'qemu' in proc.exe():
                        if 'PIOTR_INSTNAME' in procEnv:
                            if procEnv['PIOTR_INSTNAME'] == name:
                                return {
                                    'pid': proc.pid,
                                    'guest': procEnv['PIOTR_GUEST'],
                                    'agent': procEnv['PIOTR_SOCK'] if 'PIOTR_SOCK' in procEnv else None,
                                    'name': procEnv['PIOTR_INSTNAME'] if 'PIOTR_INSTNAME' in procEnv else None
                                }
            except psutil.AccessDenied as exc:
                pass

        return None


class QemuPlatforms:
    """
    This class holds the different registered Qemu platforms, with name
    and associated classes.

    Qemu platforms are classes decorated by qemu_platform(), that will
    automagically registers them.

    Supported platforms can be listed by using the list() method, and
    corresponding classes can be retrieved with the get() method.
    """

    platforms = {}

    @staticmethod
    def register(platform_name, platform_clazz):
        """
        Register a platform into this platform directory.

        @param  str     platform_name   Platform name
        @param  class   platform_class  Corresponding platform class
        """
        if platform_name not in QemuPlatforms.platforms:
            QemuPlatforms.platforms[platform_name] = platform_clazz
        else:
            QemuPlatforms.platforms[platform_name] = platform_clazz

    @staticmethod
    def list(sorted=False):
        platforms = []
        for i in QemuPlatforms.platforms:
            platforms.append((i, QemuPlatforms.platforms[i]))
        if sorted:
            platforms.sort()
        return platforms

    @staticmethod
    def has(platform):
        return (platform in QemuPlatforms.platforms)

    @staticmethod
    def get(platform):
        if platform in QemuPlatforms.platforms:
            return QemuPlatforms.platforms[platform]
        else:
            return None

class qemu_platform:
    """
    Qemu platform decorator.

    Registers a QemuPlatform-inherited class as a Qemu platform.
    """

    def __init__(self, platform_name):
        """
        Save platform name.
        """
        self.__name = platform_name

    def __call__(self, clazz):
        QemuPlatforms.register(self.__name, clazz)
        return clazz


#from piotr.qemu.platform import QemuPlatform
from piotr.qemu.virt import QemuPlatformVirt
