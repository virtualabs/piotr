"""
Exceptions.
"""

class KernelNotFound(Exception):
    """
    This exception is raised when Piotr cannot find or access a kernel.
    """
    pass

class KernelFormatError(Exception):
    """
    This exception is raised when Piotr encounters a badly formated
    kernel file.
    """
    def __init__(self, message):
        super().__init__(self)
        self.__message = message

    def str(self):
        return '<KernelFormatError message="%s"/>' % self.__message

    def repr(self):
        return str(self)

class UserDirAccessError(Exception):
    """
    This exception is raised when Piotr cannot access local user directory.
    """
    pass


class DeviceConfigMissing(Exception):
    pass

class DeviceConfigError(Exception):
    def __init__(self, msg):
        super().__init__(self)
        self.__message = msg

    def str(self):
        return '<DeviceConfigError message="%s"/>' % self.__message

    def repr(self):
        return str(self)

    def get_message(self):
        return self.__message


class DeviceNotFound(Exception):
    pass

class HostFsError(Exception):
    pass

class KernelError(Exception):
    pass

class DtbError(Exception):
    pass

class SudoRequired(Exception):
    pass
