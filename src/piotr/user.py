"""
User-related functions.
"""
import piotr
import shutil
from inspect import getfile
from os import listdir, mkdir, unlink, geteuid, environ
from os.path import expanduser, join, isfile, exists, basename, isdir, dirname
from shutil import copyfile, rmtree
from piotr.exceptions import UserDirAccessError, KernelNotFound,\
    DeviceConfigError, DeviceNotFound, DeviceConfigMissing, KernelFormatError
from piotr.util.kernel import getKernInfo
from piotr.util.device import DeviceConfig
from piotr.util.hostfs import getHostFsInfo
from piotr.util.dtb import getDtbInfo
from piotr.util.logger import debug, info, warning, error, Logger

def version_tuple(v):
    return tuple(map(int, (v.split('.'))))

class UserDirectory:

    """
    The UserDirectory class provides an interface to Piotr's local user storage:
     - User linux kernels (managed by Piotr)
     - User devices
     - User host filesystem

    This class allows:

     - list, add and remove custom kernels from installed kernels
     - get information from installed kernels (version, platform, tags, ...)
     - list installed custom devices
     - export/import a custom device (useful for sharing)
     - list, add and remove custom host filesystems

    Basically, this class stores all the user materials.
    """

    instance = None

    @staticmethod
    def get():
        if UserDirectory.instance is None:
            UserDirectory.instance = UserDirectory()
        return UserDirectory.instance

    def __init__(self):
        """
        Constructor
        """
        self.__baseDir = self.getPath()
        self.__kernelDir = join(self.__baseDir, 'kernels')
        self.__deviceDir = join(self.__baseDir, 'devices')
        self.__hostDir = join(self.__baseDir, 'hostfs')
        self.__dtbDir = join(self.__baseDir, 'dtbs')

        # Create directories if required.
        if not self.ready():
            if not self.create():
                raise UserDirAccessError()

    def getPath(self):
        """
        Retrieve the path of Piotr's local user directory. User directory is
        usually located at '~/.piotr/'.

        @return string Local user directory
        """
        if geteuid() == 0:
            # Look for 'SUDO_USER' in environ
            if 'SUDO_USER' in environ:
                userHome = expanduser('~'+environ['SUDO_USER'])
            else:
                userHome = expanduser('~')
        else:
            warning('User', 'Piotr must be run with sudo in order to access network.')
            userHome = expanduser('~')
        return join(userHome, '.piotr')

    def ready(self):
        """
        Check if current user Piotr directory exists.

        @return bool    True if it exists, False otherwise.
        """
        return  exists(self.__baseDir) and \
                exists(self.__kernelDir) and \
                exists(self.__deviceDir) and \
                exists(self.__hostDir) and \
                exists(self.__dtbDir)

    def create(self):
        """
        Create Piotr's local user directory.
        """
        try:
            # Create default directory
            if not exists(self.__baseDir):
                mkdir(self.__baseDir)

            # Create subdirectories:
            #  - kernels
            #  - devices
            #  - hostfs
            for subdir in ['kernels', 'devices', 'hostfs', 'dtbs']:
                if not exists(join(self.__baseDir, subdir)):
                    mkdir(join(self.__baseDir, subdir))

            # Copy our stock kernels and hostfs if not present (for Linux 5.10.7)
            module_path = dirname(getfile(piotr))
            stock_kernel = join(module_path, 'data/virt.cortex-a7.little-5.10.7')
            stock_fs = join(module_path, 'data/virt.cortex-a7.little-5.10.7.ext2')
            user_kernel = join(self.__baseDir, 'kernels', 'virt.cortex-a7.little-5.10.7')
            user_fs = join(self.__baseDir, 'hostfs', 'virt.cortex-a7.little-5.10.7.ext2')
            try:
                if not exists(user_kernel):
                    shutil.copyfile(stock_kernel, user_kernel)
                if not exists(user_fs):
                    shutil.copyfile(stock_fs, user_fs)
            except OSError as err:
                debug('piotr.user', 'Cannot copy stock fs/kernel into user directory')
                warning('Piotr', "Cannot install Piotr's kernel and filesystem into user directory.")
                pass

            # Success
            return True
        except Exception as e:
            # An error occured.
            return False

    ####################################
    # User kernels
    ####################################

    def getKernels(self):
        """
        List installed kernels.
        """
        # Loop on kernels stored in piotr local user directory.
        for candidate in listdir(self.__kernelDir):
            candidatePath = join(self.__kernelDir, candidate)
            if isfile(candidatePath):
                try:

                    # Try to load kernel from name and image
                    kernelInfo = getKernInfo(candidatePath)
                    kernelInfo['filepath'] = candidate
                    yield kernelInfo

                except KernelNotFound as notfound:

                    # Yield a warning
                    debug('util.user:getKernels', 'Cannot load info from kernel %s' % candidate)
                    warning('User:Kernels', 'Cannot load info from kernel file %s' % candidate)

                except KernelFormatError as badformat:

                    # Yield a warning
                    debug('util.user:getKernels', 'Bad kernel format for kernel %s' % candidate)
                    warning('User:Kernels', 'Cannot load info from kernel file %s (bad format)' % candidate)

    def hasKernel(self, kernelName):
        """
        Check if user has a specific kernel registered.

        @param  string  kernelName  Target kernel name.
        """
        return exists(join(self.__kernelDir, kernelName))


    def getKernelPath(self, kernelName):
        """
        Return kernel full path from kernelName.
        """
        if self.hasKernel(kernelName):
            return join(self.__kernelDir, kernelName)
        else:
            return None

    def findCompatibleKernel(self, version, platform=None, cpu=None, endian='little'):
        """
        Look for a compatible kernel from the ones already installed.

        This routine will iterate over all the kernels installed and
        will pick the best match based on:
        - kernel version (MUST be the exact same version number)
        - target platform
        - target cpu
        - target endianness

        @param  string  version     Target kernel version
        @param  string  platform    Target platform
        @param  string  cpu         Target cpu
        @param  string  endian      Target endianness, 'little' by default
        @return                     Kernel name if found, None otherwise
        """
        possibleKernels = []

        # Search the kernels to pick the best option
        last_version = (0,0,0)
        last_kernel = None
        for kernel in self.getKernels():
            # We should check platform, cpu and endianness first
            if 'platform' in kernel  and 'cpu' in kernel and 'endian' in kernel:
                if kernel['platform']==platform and kernel['cpu']==cpu and kernel['endian']==endian:
                    if version is not None:
                        if version_tuple(version) == version_tuple(kernel['version']):
                            return kernel['name']
                    elif version_tuple(kernel['version']) > last_version:
                        last_version = version_tuple(kernel['version'])
                        last_kernel = kernel

        # If we found a recent kernel that matches platform, cpu and endianness then use it.
        # This behavior is allowed only if version is None.
        if last_kernel is not None:
            return last_kernel['name']

        # Pick the best remaining candidate based on platform and endianness (if no version provided)
        if len(possibleKernels) > 0 and version is None:
            for kernel in possibleKernels:
                if 'platform' in kernel and kernel['platform']==platform:
                    if endian is not None and kernel['endian']==endian:
                        return kernel['name']
            return None
        else:
            return None

    def getKernel(self, kernelName):
        """
        Return a specific kernel information.

        @param      string   kernelName  Kernel name to retrieve.
        @return     object               Kernel information, none on error
        """
        if self.hasKernel(kernelName):
            kernelPath = join(self.__kernelDir, kernelName)
            if isfile(kernelPath):
                try:
                    # Try to load kernel from name and image
                    kernelInfo = getKernInfo(kernelPath)
                    kernelInfo['filepath'] = kernelName
                    return kernelInfo
                except KernelNotFound as notfound:
                    # Yield a warning
                    debug('util.user:getKernel', 'Cannot load info from kernel %s' % kernelName)
                    warning('User:Kernel', 'Cannot load info from kernel file %s' % kernelName)
                except KernelFormatError as badformat:
                    # Yield a warning
                    debug('util.user:getKernel', 'Bad kernel format for kernel %s' % kernelName)
                    warning('User:Kernel', 'Cannot load info from kernel file %s (bad format)' % kernelName)
        else:
            return None

    def removeKernel(self, kernelName):
        """
        Delete kernel from user kernels.

        @param string  kernelName   Kernel name to remove.
        @return bool    True on success, False otherwise.
        """
        if self.hasKernel(kernelName):
            unlink(self.getKernelPath(kernelName))
            return True
        else:
            return False

    def addKernel(self, kernelPath):
        """
        Add kernel to user kernels. Kernel name must match naming rules.

        @param  string  kernelPath  Kernel full path
        @return bool    True on success, False otherwise
        """
        try:
            # Load kernel information
            kernInfo = getKernInfo(kernelPath)

            # If kernel has no raw_info key, that means kernel name does not
            # comply with rules. We issue a warning, but add the kernel with
            # default naming.
            if 'raw_info' not in kernInfo:
                error('User:Kernels', 'Kernel `%s` does not comply with kernel name rules' % kernelPath)
                return False
            else:
                kernelName = basename(kernInfo['filepath'])

            # Install kernel into our directory
            copyfile(kernelPath, join(self.__kernelDir, kernelName))
            return True

        except Exception as exc:
            return False


    ####################################
    # User devices
    ####################################

    def getDevices(self):
        """
        List installed devices.
        """
        # Loop on devices stored in piotr local user directory.
        for candidate in listdir(self.__deviceDir):
            candidatePath = join(self.__deviceDir, candidate)
            if isdir(candidatePath):
                try:

                    # Try to load device config file
                    deviceInfo = DeviceConfig(candidatePath)
                    yield deviceInfo

                except DeviceNotFound as notfound:

                    # Yield a warning
                    debug('util.user:getDevices', 'Cannot load device config from device %s' % candidate)
                    warning('User:Devices', 'Cannot load info from device %s' % candidate)

                except DeviceConfigError as devError:

                    # Yield a warning
                    debug('util.user:getDevices', devError.get_message())
                    warning('User:Devices', 'Cannot load info from device %s (configuration error)' % candidate)

                except DeviceConfigMissing as configMissing:
                    debug('util.user:getDevices', 'Configuration file missing for device %s' % candidate)
                    warning('User:Devices', 'Configuration file config.yaml not found in device %s directory' % candidate)

    def hasDevice(self, deviceName):
        """
        Check if user has the required device.

        @param  string  deviceName  Device name
        @return bool                True if device exists and is valid, false otherwise.
        """
        return  exists(join(self.__deviceDir, deviceName)) and \
                exists(join(self.__deviceDir, deviceName, 'config.yaml')) and \
                isfile(join(self.__deviceDir, deviceName, 'config.yaml'))


    def getDevicePath(self, deviceName):
        """
        Return device path from device name.

        @param  string  deviceName  Target device's name
        @return string              Device path
        """
        if self.hasDevice(deviceName):
            return join(self.__deviceDir, deviceName)
        else:
            return None

    def getDevice(self, deviceName):
        """
        Return device information.

        @param  string  deviceName  Device name
        @return object              Device configuration.
        """
        if self.hasDevice(deviceName):
            devicePath = join(self.__deviceDir, deviceName)
            if isdir(devicePath):
                try:

                    # Try to load device config file
                    deviceInfo = DeviceConfig(devicePath)
                    return deviceInfo

                except DeviceNotFound as notfound:

                    # Yield a warning
                    debug('util.user:getDevice', 'Cannot load device config from device %s' % deviceName)
                    warning('User:Device', 'Cannot load info from device %s' % deviceName)

                except DeviceConfigError as devError:

                    # Yield a warning
                    debug('util.user:getDevice', devError.getMessage())
                    warning('User:Device', 'Cannot load info from device %s (configuration error)' % deviceName)
        else:
            return None

    def removeDevice(self, deviceName):
        """
        Remove a device

        @param  str     deviceName  Name of device to remove.
        @return bool                True on success, False otherwise
        """
        if self.hasDevice(deviceName):
            device_dir = join(self.__deviceDir, deviceName)
            try:
                rmtree(device_dir, ignore_errors=True)
                return True
            except Exception as err:
                return False
        else:
            return False


    ####################################
    # Host filesystems
    ####################################

    def getHostFilesystems(self):
        """
        Enumerate host filesystems.
        """
        # Loop on devices stored in piotr local user directory.
        for candidate in listdir(self.__hostDir):
            hostPath = join(self.__hostDir, candidate)
            if isfile(hostPath):
                fsInfo = getHostFsInfo(candidate)
                if fsInfo is not None:
                    fsInfo['filepath'] = hostPath
                    yield fsInfo

    def hasHostFs(self, hostfsName):
        """
        Check if a host FS is present.
        """
        return  exists(join(self.__hostDir, hostfsName)) and \
                getHostFsInfo(hostfsName) is not None

    def findCompatibleHostFs(self, version, platform=None, cpu=None, endian=None):
        """
        Find the latest compatible hostfs for target platform/cpu/endianness
        """
        possibleHostFs = []

        # Search the kernels to pick the best option
        last_version = (0,0,0)
        last_fs = None
        for hostfs in self.getHostFilesystems():
            # We should check platform, cpu and endianness first
            if 'platform' in hostfs  and 'cpu' in hostfs and 'endian' in hostfs:
                if hostfs['platform']==platform and hostfs['cpu']==cpu and hostfs['endian']==endian:
                    if version is not None:
                        if version_tuple(version) == version_tuple(hostfs['version']):
                            return hostfs['name']
                    elif version_tuple(hostfs['version']) > last_version:
                        last_version = version_tuple(hostfs['version'])
                        last_fs = hostfs

        # If we found a recent fs that matches platform, cpu and endianness then return it
        if last_fs is not None:
            return last_fs['name']

        # Pick the best remaining candidate based on platform and endianness
        if len(possibleHostFs) > 0 and version is None:
            for hostfs in possibleHostFs:
                if 'platform' in hostfs and hostfs['platform']==platform:
                    if endian is not None and hostfs['endian']==endian:
                        return hostfs['name']
            return None
        else:
            return None

    def getHostFsPath(self, hostfsName):
        """
        Get HostFS path from name.

        @param  string  hostfsName  Host filesystem filename
        """
        if self.hasHostFs(hostfsName):
            return join(self.__hostDir, hostfsName)
        else:
            return None

    def removeHostFs(self, hostfsName):
        """
        Remove Host FS.

        @param  string  hostfsName  Host FS filename.
        @return bool                True if removed, false otherwise.
        """
        if self.hasHostFs(hostfsName):
            unlink(self.getHostFsPath(hostfsName))
            return True
        else:
            return False

    def addHostFs(self, hostfsPath):
        """
        Add Host filesystem to our filesystems.

        @param  string  hostfsPath  Source hostFS path
        @return bool                True on success, False otherwise.
        """
        try:
            # Load kernel information
            hostfsInfo = getHostFsInfo(basename(hostfsPath))

            if hostfsInfo is not None:
                # Install kernel into our directory
                copyfile(hostfsPath, join(self.__hostDir, basename(hostfsPath)))
                return True
            else:
                return False

        except Exception as exc:
            return False


    ####################################
    # User DTBs
    ####################################

    def getDtbs(self):
        """
        Retrieve DTBs
        """
        """
        List installed devices.
        """
        # Loop on devices stored in piotr local user directory.
        for candidate in listdir(self.__dtbDir):
            candidatePath = join(self.__dtbDir, candidate)
            if isfile(candidatePath):
                # Try to load device config file
                dtbInfo = getDtbInfo(candidate)
                if dtbInfo is not None:
                    dtbInfo['filepath'] = candidatePath
                    yield dtbInfo
                else:
                    debug(
                        'piotr.device:getDtbs',
                        'Bad format for DTB %s' % candidate
                    )

    def hasDtb(self, dtb):
        dtbPath = join(self.__dtbDir, dtb)
        return (exists(dtbPath) and isfile(dtbPath))

    def getDtbPath(self, dtb):
        return join(self.__dtbDir, dtb)


    def getDtb(self, dtb):
        if self.hasDtb(dtb):
            return getDtbInfo(dtb)

    def removeDtb(self, dtb):
        """
        Remove a specific DTB.
        """
        if self.hasDtb(dtb):
            unlink(join(
                self.__dtbDir,
                basename(dtb)
            ))
            return True
        else:
            debug('piotr.user:removeDtb', 'DTB not found')
            error('DTB', 'Specified DTB does not exist and cannot be removed')
            return False


    def addDtb(self, dtbPath):
        """
        Add a specific DTB to our DTBs.

        @param  string  dtbPath     Source DTB path
        @return bool                True on success, False otherwise.
        """
        if self.hasDtb(basename(dtbPath)):
            return False
        else:
            try:
                # Load kernel information
                dtbInfo = getDtbInfo(basename(dtbPath))

                if dtbInfo is not None:
                    # Install kernel into our directory
                    copyfile(dtbPath, join(self.__dtbDir, basename(dtbPath)))
                    return True
                else:
                    return False

            except Exception as exc:
                return False

    def findCompatibleDtb(self, platform, cpu=None):
        """
        Find a compatible DTB based on platform and cpu.

        @param  string  platform    Target platform
        @param  string  cpu         Target CPU
        @return string              Compatible DTB if found, None otherwise
        """
        platform = platform.split('-')[0]
        genericDtb = None
        for dtb in self.getDtbs():
            if dtb['platform'] == platform:
                if cpu is not None:
                    if dtb['cpu'] == cpu:
                        return dtb['name']
                    elif dtb['cpu'] =='generic':
                        genericDtb = dtb['name']
                else:
                    if dtb['cpu'] == 'generic':
                        return dtb['name']
        return genericDtb
