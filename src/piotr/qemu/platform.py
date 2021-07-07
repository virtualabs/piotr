from shutil import copyfile, rmtree, copytree, Error
import subprocess
import sys
import tempfile
from os import environ, mkdir
from os.path import exists, join, dirname, basename
from pathlib import Path

from piotr.qemu import qemu_platform, QemuGuestEnum
from piotr.util.logger import info, warning, debug, error
from piotr.util.namegen import get_random_name

class QemuPlatform:
    """
    Qemu default platform class (based on 'virt' machine)
    """

    def __init__(self, device, name=None):
        self.__name = name
        self.device = device
        self.process = None
        self.__qemu_args = []
        self.nic_index = 0
        self.nics_to_nets = {}

    def generate_name(self):
        """
        Generate an instance name.
        """
        inst_names = QemuGuestEnum.getInstanceNames()
        if self.__name is not None:
            if self.__name in inst_names:
                warning('Instance', 'Instance name already exists, generating a new one')
            else:
                return self.__name

        # Generate a random name
        self.__name = get_random_name()
        while self.__name in inst_names:
            self.__name = get_random_name()

        return self.__name

    def prepare_environment(self):
        """
        Prepare the running environment.

        Duplicate the host filesystem if required (sometimes it is modified
        by the guest system).

        Prepare the SD card image file if required (if sd=true in config.yaml),
        and provide the path to qemu.
        """
        # Create a temporary directory
        self.__tempDir = tempfile.mkdtemp(prefix='piotr-')
        debug('piotr.qemu:prepare_environment', 'Created temporary directory %s' % self.__tempDir)

        # Copy our host filesystem in it
        try:
            debug('piotr.qemu:prepare_environment', 'Copy selected host FS to temporary directory')
            tempHostFs = join(self.__tempDir, basename(self.device.getHostFsPath()))
            copyfile(
                self.device.getHostFsPath(),
                tempHostFs
            )
            self.__hostFsPath = tempHostFs
            debug('piot.qemu:prepare_environment', 'Host fs is now stored at: %s' % self.__hostFsPath)

            # Embed our target file system if required (if guestfs is set to 'embed')
            # This method is designed to work for old versions of kernel, in order to
            # avoid using 9P as it may not be available
            debug('piotr.qemu:prepare_environment', 'Checking if guest FS must be embedded into our duplicate host FS ...')
            if self.device.mustEmbedGuestFS():
                debug('piotr.qemu:prepare_environment', 'Guest FS must be embedded')
                debug('piotr.qemu:prepare_environment', 'Creating mounting point for host FS')

                # First, create a temporary mount point for our filesystem
                tempHostFsMP = join(self.__tempDir, 'host')
                mkdir(tempHostFsMP)

                # Then, we mount our host FS onto this mounting point
                debug('piotr.qemu:prepare_environment', 'Mounting Host FS onto %s' % tempHostFsMP)
                if subprocess.call('mount %s %s' % (
                    tempHostFs,
                    tempHostFsMP
                    ), shell=True) == 0:
                    debug('piotr.qemu:prepare_environment', 'Host FS successfully mounted !')

                    # Copy guest filesystem into our host fs
                    debug('piotr.qemu:prepare_environment', 'Copying guest FS into host FS ...')
                    try:
                        subprocess.call('cp -rf %s %s' % (
                            join(self.device.getPath(), 'rootfs/*'),
                            join(tempHostFsMP, 'target'),
                        ), shell=True)
                        debug('piotr.qemu:prepare_environment', 'Guest FS successfully copied to host FS !')
                    except Error as shutilErr:
                        debug('piotr.qemu:prepare_environment', 'Unable to copy guest FS into host FS')
                        warning('Piotr:QemuGuest', 'Cannot install guest FS into host FS (copy failed)')

                        # Failure
                        subprocess.call('umount %s' % tempHostFsMP)
                        return False

                    # Unmount host FS
                    debug('piotr.qemu:prepare_environment', 'Unmounting host FS ...')
                    if subprocess.call('umount %s' % tempHostFsMP, shell=True) == 0:
                        debug('piotr.qemu:prepare_environment', 'Host FS successfully unmounted.')
                    else:
                        debug('piotr.qemu:prepare_environment', 'Unable to unmount host FS')
                        warning('Piotr:QemuGuest', 'An error occurred while unmounting host FS')

                        # Failure
                        return False
                else:
                    debug('piotr.qemu:prepare_environment', 'Unable to mount host FS onto %s' % tempHostFsMP)
                    warning('Piotr:QemuGuest', 'Cannot mount host FS to %s (required to embed guest FS)' % tempHostFsMP)

            # Prepare our SD card if any
            if self.device.hasSd():

                # Compute sd card image size (fs size + 50M)
                sd_image = join(
                    self.__tempDir,
                    'sdcard.img'
                )
                sd_directory = Path(self.device.getSdImage())
                image_size = sum(f.stat().st_size for f in sd_directory.glob('**/*') if f.is_file()) + (50*(2**20))

                # Allocate sd card image
                image_alloc = subprocess.call(
                    'dd if=/dev/zero of=%s bs=%d count=1' % (
                        sd_image,
                        image_size
                    ),
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                if image_alloc == 0:
                    # create an ext2 filesystem
                    image_fs = subprocess.call(
                        'mkfs.ext2 %s' % sd_image,
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    if image_fs == 0:
                        # Mount filesystem and copy sdcard files
                        sd_mp = join(self.__tempDir, 'sdcard')
                        subprocess.call('mkdir %s' % sd_mp, shell=True)
                        subprocess.call('mount -t ext2 %s %s' % (sd_image, sd_mp), shell=True)
                        subprocess.call('cp -rf %s/* %s' % (sd_directory, sd_mp), shell=True)

                        # unmount filesystem
                        subprocess.call('umount %s' % sd_mp, shell=True)

                        # SD card image is ready to use !
                        self.__sdImagePath = sd_image
                    else:
                        debug('piotr.qemu:prepare_environment', 'cannot format sdcard image to ext2')
                        error('QemuGuest','Cannot format SD card, mkfs.ext2 error occurred.')
                        return False
                else:
                    debug('piotr.qemu:prepare_environment', 'cannot create sdcard image in temporary directory')
                    error('QemuGuest', 'Cannot create SD card image in %s' % self.__tempDir)
                    return False

        except Exception as exc:
            print(exc)
            debug('piotr.qemu:prepare_environment', 'An exception occurred: %s' % str(exc))
            error('QemuGuest', 'An error occurred, unable to prepare the guest environment.')
            return False

        return True

    def clean_environment(self):
        """
        Clean environment.

        Delete the temporary directory and remove all files.
        """
        debug('piotr.qemu:clean_environment', 'Remove temporary environment at %s' % self.__tempDir)
        rmtree(self.__tempDir)
        debug('piotr.qemu:clean_environment', 'Temporary environment removed')

    def append_arg(self, argument):
        """
        Append an argument to qemu arguments list.`argument` may be a string
        or a list of arguments.

        @param  argument    object  Argument to append.
        """
        if isinstance(argument, str):
            self.__qemu_args.append(argument)
        elif isinstance(argument, list):
            self.__qemu_args.extend(argument)
        else:
            raise ValueError()

    def set_platform(self, platform):
        """
        Add qemu platform arguments

        @param  str     platform    Qemu platform to use
        """
        # declare machine
        self.append_arg([
            '-M',
            platform
        ])

    def set_cpu(self, cpu):
        """
        Add qemu platform argument.

        @param  str     cpu     CPU to use.
        """
        self.append_arg([
            '-cpu',
            cpu
        ])


    def set_memory(self, memory):
        """
        Add qemu memory argument.

        @param  str     memory  Memory to use.
        """
        self.append_arg([
            '-m',
            str(memory)
        ])

    def set_kernel(self, kernel):
        """
        Add qemu kernel argument.

        @param  str     kernel  Kernel file to use.
        """
        self.append_arg([
            '-kernel',
            kernel
        ])


    def set_dtb(self, dtb):
        """
        Add qemu DTB file path argument.

        @param  str     dtb     DTB file path.
        """
        self.append_arg([
            '-dtb',
            dtb
        ])

    def set_sd(self, sd_image_path):
        """
        Add qemu SD card arguments.

        @param  str     sd_image_path   SD card image file path.
        """
        self.append_arg([
            '-drive',
            'file=%s,if=none,format=raw,id=hd1,index=1' % sd_image_path,
            '-device',
            'virtio-blk-device,drive=hd1'
        ])

    def set_host_drive(self, hostfs, drive_type):
        """
        Add qemu host drive with corresponding image.

        @param  str     hostfs  Host FS path.
        """
        # Handle 'virtio' special drive.
        if drive_type== 'virtio':
            self.append_arg([
                '-drive',
                'file=%s,if=none,format=raw,id=hd0' % hostfs,
                '-device',
                'virtio-blk-device,drive=hd0'
            ])
        else:
            # Otherwise use the provided drive type.
            self.append_arg([
                '-drive',
                'file=%s,%s' % (
                    hostfs,
                    drive_type
                )
            ])


    def set_bootargs(self, bootargs):
        """
        Add qemu bootargs argument.

        @param  str     bootargs    Bootargs to use.
        """
        self.append_arg([
            '-append',
            '"%s"' % bootargs
        ])

    def set_nic(self, nic, redirects=[]):
        """
        Add qemu nic arguments.

        @param str  nic     Nic parameters to use.
        """
        # If nic is in 'user' mode, then add a simple network device with current
        # nic index.
        if nic['type'] == 'user':
            # Compile port forward rules
            redir_rules = []
            for redir in redirects:
                redir_rules.append(
                    'hostfwd=%s::%d-:%d' % (
                        redir['proto'],
                        redir['local'],
                        redir['dest']
                    )
                )

            # Declare interface
            if len(redir_rules) == 0:
                self.append_arg([
                    '-netdev',
                    'user,id=net%d' % self.nic_index,
                    '-device',
                    'virtio-net-%s,netdev=net%d' % (
                        self.get_virtio_config(),
                        self.nic_index
                    )
                ])
            else:
                self.append_arg([
                    '-netdev',
                    'user,id=net%d,%s' % (
                        self.nic_index,
                        ','.join(redir_rules)
                    ),
                    '-device',
                    'virtio-net-%s,netdev=net%d' % (
                        self.get_virtio_config(),
                        self.nic_index
                    )
                ])
        elif nic['type'] == 'tap':
            self.append_arg([
                '-netdev',
                'type=tap,id=net%d,ifname=%s,script=no,downscript=no' % (
                    self.nic_index,
                    nic['interface']
                ),
                '-device',
                'virtio-net-%s,netdev=net%d' % (
                    self.get_virtio_config(),
                    self.nic_index,
                )
            ])

        # Increment nic index
        self.nic_index += 1

    def set_network_tap(self):
        """
        Add a network tap interface.
        """
        self.append_arg([
            '-netdev',
            'type=tap,id=net%d,ifname=tap0,script=no,downscript=no' % self.nic_index,
            '-device',
            'virtio-net-device,netdev=net%d' % self.nic_index,
        ])
        self.nic_index += 1


    def set_guest_fs(self, rootfs, fstype):
        """
        Add qemu guest FS arguments.

        @param  str rootfs  Guest root filesystem path.
        @param  str fstype  Bus name (must be 'pci' or 'device')
        """
        self.append_arg([
            '-fsdev',
            'local,path=%s,security_model=passthrough,id=host0' % (
                rootfs
                ),
            '-device',
            '%s,fsdev=host0,mount_tag=host0' % fstype,
        ])

    def set_no_screen(self):
        """
        Add qemu nographic option.
        """
        self.append_arg('-nographic')


    def set_agent_vport(self, vport, device):
        """
        Set agent virtual serial port.

        @param  str     vport   Virtual port UNIX socket path
        @param  str     device  Virtual serial port device type
        """
        self.append_arg([
            '-chardev',
            'socket,path=%s,server,nowait,id=piotr' % vport,
            '-device',
            '%s' % device,
            '-device',
            'virtserialport,chardev=piotr,name=piotr'
        ])


    def prepare_args(self):
        """
        Prepare arguments array for qemu-system-arm.
        """

        # Generate command line to start Qemu guest
        self.__qemu_args = []

        # Use mainline qemu-system-arm
        self.append_arg('qemu-system-arm')

        # Add platform arguments
        self.set_platform(self.device.getPlatform())

        # Add cpu arguments
        if self.device.getCpu() is not None:
            self.set_cpu(self.device.getCpu())

        # Add memory arguments
        self.set_memory(self.device.getMemory())

        # Add kernel
        self.set_kernel(self.device.getKernelPath())

        # Add DTB argument if provided
        if self.device.hasDtb():
            self.set_dtb(self.device.getDtbPath())

        # Add sd card arguments if required
        if self.device.hasSd():
            self.set_sd(self.__sdImagePath)

        # Add our host drive
        self.set_host_drive(self.__hostFsPath, self.device.getDriveType())

        # Add bootargs arguments
        self.set_bootargs(self.device.getBootArgs())

        # Check network redirections consistency
        applied_redirects = []
        if self.device.hasRedirects() and self.device.hasNetwork():
            rules = self.device.getRedirects()
            nics = self.device.getNics()
            nic_names = [nic['name'] for nic in nics]
            nics_type = {}
            for nic in nics:
                nics_type[nic['name']] = nic['type']
            for rule in rules:
                if rule['iface'] not in nic_names:
                    warning('piotr.qemu.platform', 'Port redirection `%s` cannot be applied (unknown network interface `%s`)' % (
                        rule['name'],
                        rule['iface']
                    ))
                elif nics_type[rule['iface']] == 'user':
                    applied_redirects.append(rule)
                else:
                    warning('piotr.qemu.platform', 'Port redirection `%s` cannot be applied (wrong NIC type for interface `%s`)' % (
                        rule['name'],
                        rule['iface']
                    ))
        elif not self.device.hasNetwork():
            warning('piotr.qemu.platform', 'Target device has network port redirections but no NIC !')

        # Prepare networking interfaces
        if self.device.hasNetwork():
            nics = self.device.getNics()
            for nic in nics:
                # Setup interface with associated redirections (if any)
                self.set_nic(nic, filter(lambda x: (x['iface'] == nic['name']), applied_redirects))

        # set our virtfs share if required
        if not self.device.mustEmbedGuestFS():
            self.set_guest_fs(
                self.device.getRootfsPath(),
                self.device.getVirtio9pConfig()
            )

        # No screen
        self.set_no_screen()


        # Add a virtual serial port to allow host/guest communication
        virtport = join(self.__tempDir, 'piotr')
        self.set_agent_vport(virtport, self.device.getVirtioSerialConfig())

    def start(self, background=False):
        """
        Start Qemu guest
        """
        # Prepare our environment
        if self.prepare_environment():

            self.prepare_args()

            # Start process with dedicated environment
            try:
                # Save device name and socket in environment variables
                environ['PIOTR_GUEST'] = self.device.getDeviceName()
                environ['PIOTR_SOCK'] = join(self.__tempDir, 'piotr')
                environ['PIOTR_INSTNAME'] = self.generate_name()
                debug('piotr.qemu:cmdline', ' '.join(self.__qemu_args))
                debug('piotr.qemu:start', ' '.join(self.__qemu_args))

                if background:
                    # Launch Qemu-system-arm in background, redirect stdout
                    # and stderr into a pipe
                    self.process = subprocess.Popen(
                        ' '.join(self.__qemu_args),
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                else:
                    # Launch Qemu-system-arm
                    self.process = subprocess.Popen(
                        ' '.join(self.__qemu_args),
                        shell=True
                    )
                info('Qemu', 'Device %s started successfully' % self.device.getName())
                return True
            except OSError as err:
                debug('piotr.qemu.QemuGuest:start', 'An error occurred: %s' % str(err))
                error("Qemu", 'Cannot start device %s' % self.device.getName())
        else:
            debug('piotr.qemu:start', 'An error occurred while prepping env')
            error('Piotr:QemuGuest','Cannot setup the guest environment, aborting ...')
            self.clean_environment()

    def wait(self):
        """
        Wait for child process to complete.
        """
        if self.process is not None:
            self.process.wait()

    def stop(self):
        """
        Clean environment once the guest is stopped
        """
        self.clean_environment()


    def get_virtio_config(self):
        """
        Get the underlying device virtio configuration (device or pci)
        """
        return self.device.getVirtioConfig()

    def requires_privileges(self):
        """
        Check if the target device requires specific privileges.

        Specific privileges are required if a tap network interface is set,
        this method checks if a NIC has been declared and responds accordingly.
        """
        return (self.device.hasNetwork())


    def get_pid(self):
        """
        Retrieve guest PID
        """
        if self.process is not None:
            return self.process.pid

    def get_sock(self):
        return join(self.__tempDir, 'piotr')

    def get_name(self):
        return self.__name
