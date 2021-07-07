"""
Piotr Device.

Provides the Device class required to load and manage devices from user special
directory (~/.piotr/).
"""
import os
import piotr
import shutil
from inspect import getfile
from os.path import exists, join, isfile, isdir, dirname
from piotr.util.device import DeviceConfig
from piotr.user import UserDirectory
from piotr.util.logger import warning, error, debug
from piotr.exceptions import KernelNotFound, HostFsError, DeviceNotFound, \
    DtbError

def create_device(devname):
    """
    Create a device skeleton.

    @param  str     devname     Device alias
    """
    # Filter device name
    # We don't want devname to contain '/'
    devname = devname.replace('/','_')

    # get module path
    module_path = dirname(getfile(piotr))
    skel_config = join(module_path, 'data/config.skeleton.yaml')

    # Create our device skeleton
    base_dir = UserDirectory.get().getPath()
    device_dir = join(base_dir, 'devices')
    if exists(device_dir):
        if isdir(device_dir):
            dev_dir = join(device_dir, devname)
            rootfs_dir = join(dev_dir, 'rootfs')
            config_file = join(dev_dir, 'config.yaml')

            try:
                # Create device directory
                os.mkdir(dev_dir)

                # Create device rootfs
                os.mkdir(rootfs_dir)

                # Copy config.yaml skeleton
                shutil.copyfile(skel_config, config_file)
            except OSError as err:
                error('piotr.util.device:create_device', 'An error occured while creating device directory: %s' % str(err))

        else:
            error('piotr.util.device:create_device', 'devices directory is not a directory')
    else:
        error('piotr.util.device:create_device', 'devices directory does not exist')


class Device(object):
    """
    Piotr emulated device container.

    This class is in charge of loading a device directory:
    - it loads the config.yaml configuration file located at the root of this directory
    - it checks every parameter and builds an internal view of the device

    This class is then used by a QemuPlatform-compatible class in order to
    run the guest corresponding to this device.
    """

    def __init__(self, deviceName):
        """
        Constructor
        """
        # dependencies
        self.__devName = deviceName
        self.kernel = None
        self.hostfs = None
        self.dtb = None

        # First, we load our device configuration
        self.__userDir = UserDirectory.get()
        if self.__userDir.hasDevice(deviceName):
            self.__config = DeviceConfig(self.__userDir.getDevicePath(deviceName))
            self.__load()
        else:
            raise DeviceNotFound()


    def __checkKernel(self):
        """
        Check if a compatible kernel is available.

        @return     bool    True if a compatible kernel was found, False otherwise
        """
        # Is kernel a path to an existing kernel ?
        if self.__config.kernel is not None and exists(join(self.__config.getPath(), self.__config.kernel)):
            return True
        else:
            # Look for a compatible kernel
            debug('piotr.device:__checkKernelFs', 'Look for compatible kernel ...')
            compKernel = self.__userDir.findCompatibleKernel(
                self.__config.kernel,
                self.__config.platform,
                self.__config.cpu,
                self.__config.endian
            )
            if compKernel is not None:
                debug('piotr.device:__checkKernel', 'Kernel %s found' % (
                    self.__config.kernel
                ))
                return True
            else:
                debug(
                    'piotr.device:__checkKernelFs',
                    'No compatible kernel for version %s and platform %s' % (
                        self.__config.kernel,
                        self.__config.platform
                ))
                error(
                    'Device',
                    'Cannot find a compatible kernel for device %s' % (
                        self.__devName
                ))
                return False


    def __checkHostFs(self):
        """
        Check Host filesystem.
        """
        debug('piotr.device:__checkHostFs', 'Look for compatible Host FS ...')
        compHostFs = self.__userDir.findCompatibleHostFs(
            self.__config.hostfs,
            self.__config.platform,
            self.__config.cpu,
            self.__config.endian
        )
        if compHostFs is not None:
            debug('piotr.device:__checkHostFs', 'Host FS %s found' % (
                self.__config.hostfs
            ))
            return True
        else:
            error('Device', 'Cannot find a compatible Host FS with %s' % self.__config.hostfs)
            return False


    def __findDtb(self):
        """
        Check DTB file.

        DTB value can be one of the following:
            - auto: we automatically pick the DTB from stock DTBs, and avoid it
                    if none is found
            - embedded: dtb is embedded with kernel, so no need to specify it
            - *.dtb: dtb file is provided aside the kernel, in the device directory
        """
        if self.__config.dtb is not None:
            if self.__config.dtb.lower() == 'auto':
                dtbName = self.__userDir.findCompatibleDtb(
                    self.__config.platform,
                    self.__config.cpu
                )
                if dtbName is not None:
                    return self.__userDir.getDtbPath(dtbName)
                else:
                    return None
            elif self.__config.dtb.lower() == 'embedded':
                return None
            elif self.__config.dtb.endswith('.dtb'):
                dtbPath = join(self.__config.getPath(), self.__config.dtb)
                if exists(dtbPath) and isfile(dtbPath):
                    return dtbPath
                else:
                    warning('Device', 'Provided DTB file is missing or incorrect')
                    return None
            else:
                return None

    def __load(self):
        """
        Load device components.
        """
        # Check kernel and host fs
        debug('piotr.device:__load', 'Checking required parameters ...')
        if not self.__checkKernel():
            debug('piotr.device:__load', 'No compatible kernel found')
            raise KernelNotFound()
        elif not self.__checkHostFs():
            debug('piotr.device:__load', 'No compatible Host FS found')
            raise HostFsError()


        # Resolve DTB path
        self.__dtbPath = self.__findDtb()

        # Kernel and Host FS are ok
        if self.__config.kernel is not None  and exists(join(self.__config.getPath(), self.__config.kernel)):
            self.__kernelPath = join(self.__config.getPath(), self.__config.kernel)
        else:
            if self.__config.kernel is not None:
                debug('piotr.device:__load', 'provided kernel option "%s" does not correspond to an existing kernel (full path: %s)' %(
                    self.__config.kernel,
                    join(self.__config.getPath(), self.__config.kernel)
                ))
            self.__kernelPath = self.__userDir.getKernelPath(
                self.__userDir.findCompatibleKernel(
                    self.__config.kernel,
                    self.__config.platform,
                    self.__config.cpu,
                    self.__config.endian
                )
            )

        self.__hostfsPath = self.__userDir.getHostFsPath(
            self.__userDir.findCompatibleHostFs(
                    self.__config.hostfs,
                    self.__config.platform,
                    self.__config.cpu,
                    self.__config.endian
            )
        )

    def getPath(self):
        """
        Get the device absolute path.

        @return     str     Device absolute path
        """
        return self.__config.getPath()

    def getDeviceName(self):
        """
        Get device alias from directory name.

        @return     str     Device alias name
        """
        return self.__devName


    def getName(self):
        """
        Get device name from config file.

        @return     str     Device name
        """
        if self.__config.name is not None:
            return self.__config.name
        else:
            return 'piotr_guest'


    def hasStockKernel(self):
        """
        Check if device uses a stock kernel.
        """
        if self.__config.kernel is not None and exists(join(self.__config.getPath(), self.__config.kernel)):
            return False
        else:
            # Look for a compatible kernel
            compKernel = self.__userDir.findCompatibleKernel(
                self.__config.kernel,
                self.__config.platform,
                self.__config.cpu,
                self.__config.endian
            )
            return (compKernel is not None)

    def hasStockDtb(self):
        """
        Check if device uses a stock DTB
        """
        if self.hasDtb():
            if self.__config.dtb.lower() == 'auto':
                return True
        return False


    def hasStockHostFs(self):
        """
        Check if device uses a stock Host FS
        """
        if self.__config.hostfs is not None and exists(join(self.__config.getPath(), self.__config.hostfs)):
            return False
        else:
            # Look for a compatible host FS
            compFs = self.__userDir.findCompatibleHostFs(
                self.__config.hostfs,
                self.__config.platform,
                self.__config.cpu,
                self.__config.endian
            )
            return (compFs is not None)

    def getKernelPath(self):
        """
        Retrieve device kernel path.

        @return     string  Selected kernel path
        """
        return self.__kernelPath


    def getHostFsPath(self):
        """
        Retrieve device host fs path

        @return     string  Selected host FS path
        """
        return self.__hostfsPath


    def hasDtb(self):
        """
        Detect if device's DTB is set.
        """
        return (self.__dtbPath is not None)


    def getDtbPath(self):
        """
        Retrieve device's DTB path.
        """
        return self.__dtbPath


    def getDriveType(self):
        """
        Return Qemu drive interface based on device configuration.

        'scsi' and 'sd' are default supported types, any other values
        will be directly passed to Qemu.

        @return     string  Qemu drive interface argument
        """
        if self.__config.drivetype == 'scsi':
            return 'if=scsi,format=raw'
        elif self.__config.drivetype == 'sd':
            return 'if=sd,format=raw,index=0'
        elif self.__config.drivetype == 'virtio':
            return self.__config.drivetype


    def hasRedirects(self):
        """
        Detect if the device requires ports to be redirected to a specific
        NIC and target ports.

        @return     bool    True if device redirects ports, False otherwise.
        """
        return (len(self.__config.redirs) > 0)


    def getRedirects(self):
        """
        Get network redirection rules.

        @return     list    List of network redirections to apply.
        """
        return self.__config.redirs


    def hasNetwork(self):
        """
        Detect if the device requires a NIC to be created.

        @return     bool    True if a NIC must be created, False otherwise.
        """
        return (len(self.__config.nics) > 0)


    def getNics(self):
        """
        Retrieve NICs parameters.

        @return     str     Device's NIC parameters (qemu-style)
        """
        if self.hasNetwork():
            return self.__config.nics
        else:
            return None


    def hasSd(self):
        """
        Detect if the device requires a SD card to be created.

        @return     bool    True if a SD card is required, False otherwise.
        """
        return (self.__config.sd is not None)


    def getRootfsPath(self):
        """
        Return the device's absolute root filesystem path.

        @return     str     Device's absolute root FS path
        """
        return join(self.__config.getPath(), 'rootfs')


    def getSdImage(self):
        """
        Return the SD card root directory path.

        @return     str     SD card root FS path
        """
        return join(
            self.__config.getPath(),
            self.__config.sd
        )


    def getPlatform(self):
        """
        Retrieve the target platform, such as `virt` or `versatilepb`.

        @return     str     Target emulation platform
        """
        if self.__config.platform is not None:
            return self.__config.platform
        else:
            return 'virt'

    def getCpu(self):
        """
        Retrieve the device's CPU.

        @return     str     Cpu name if specified, None otherwise.
        """
        return self.__config.cpu


    def getMemory(self):
        """
        Retrieve device's RAM size.

        @return     str     Device RAM size, '128M' if not specified
        """
        if self.__config.memory is not None:
            return self.__config.memory
        else:
            return '128M'


    def getBootArgs(self):
        """
        Retrieve device's boot args.

        @return     str     Device bootargs
        """
        return self.__config.bootargs


    def getVirtioConfig(self):
        """
        Get virtio default config to use for virtio devices (either device or
        pci).

        @return     str     Virtio device configuration
        """
        return self.__config.virtio

    def getVirtio9pConfig(self):
        """
        Get virtio 9P device type.

        @return     str     Virtio 9P device type.
        """
        return 'virtio-9p-%s' % self.__config.virtio


    def getVirtioSerialConfig(self):
        """
        Get virtio serial port type.

        @return     str     Device's virtio serial port type.
        """
        return 'virtio-serial-%s' % self.__config.virtio


    def mustEmbedGuestFS(self):
        """
        Detect if guest fs must be embedded into root fs. This may be required
        if the selected kernel does not support 9P file sharing (<=3.10)
        """
        return (self.__config.guestfs == 'embed')
