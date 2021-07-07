"""
Device packaging

This module provides export and import features for Piotr devices.

When exporting a device, Piotr will check if the device uses a custom or a
stock kernel (from the actual user configuration), and will export it as well.
Stock kernels will then be imported into the registered kernels by default when
a device is imported, but this behavior can be altered depending on the kernel
used (which may conflict with existing kernels).

Device packages are TGZ archive with a custom extension (.piotr).
"""
import os
from os.path import join, exists, isfile, isdir, basename, splitext
import pathlib
from piotr.user import UserDirectory as ud
from piotr.util.device import DeviceConfig, DeviceConfigError, DeviceConfigMissing
from piotr.util.dtb import getDtbInfo
from piotr.util.kernel import getKernInfo
from piotr.util.hostfs import getHostFsInfo
from piotr.util.logger import debug, warning, error
import tarfile
import tempfile
import subprocess

class BadPackageError(Exception):
    pass

def __remove_dir(d):
    subprocess.call('rm -rf %s' % d, shell=True)

def package_create(device, package_path):
    """
    Create a package from device.

    @param      Device          device  Device to export into a package
    @param      package_path    str     Target package file path
    @return     bool                    True on success, False on error
    """

    # First, we create a temporary directory
    temp_dir = tempfile.mkdtemp(prefix='piotr-')

    # We copy the entire device directory, recursively
    subprocess.call(
        'cp -rf %s/* %s' % (
            device.getPath(),
            temp_dir
        ),
        shell=True
    )

    # We add the kernel if it is a stock one
    if device.hasStockKernel():
        # Ensure 'deps/kernel/' directory exists in temporary directory
        kern_dir = join(temp_dir, 'deps/kernel/')
        if not exists(kern_dir):
            os.makedirs(kern_dir)

        # Copy kernel to kernel directory
        subprocess.call(
            'cp %s %s' % (
                device.getKernelPath(),
                kern_dir
            ),
            shell=True
        )

    # We add the dtb if it is a stock one
    if device.hasStockDtb():
        # Ensure 'deps/hostfs/' directory exists in temporary directory
        dtb_dir = join(temp_dir, 'deps/dtb/')
        if not exists(fs_dir):
            os.makedirs(fs_dir)

        # Copy kernel to kernel directory
        subprocess.call(
            'cp %s %s' % (
                device.getDtbPath(),
                dtb_dir
            ),
            shell=True
        )

    # We add the host FS if it is a stock one
    if device.hasStockHostFs():
        # Ensure 'deps/hostfs/' directory exists in temporary directory
        fs_dir = join(temp_dir, 'deps/hostfs/')
        if not exists(fs_dir):
            os.makedirs(fs_dir)

        # Copy kernel to kernel directory
        subprocess.call(
            'cp %s %s' % (
                device.getHostFsPath(),
                fs_dir
            ),
            shell=True
        )

    # We compress everything and save it to package_path
    with tarfile.open(package_path, mode='w:gz') as pack:
        pack.add(temp_dir, '', recursive=True)

    # remove temporary directory
    subprocess.call(
        'rm -rf %s' % temp_dir,
        shell=True
    )


def package_import(package_path):
    """
    Import a device from a package.

    @param      str     package_path    Package path
    @return     bool                    True on success, False on error
    """
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp(prefix='piotr-')

    # Check package and decompress if ok
    with tarfile.open(package_path, mode='r:gz') as pack:
        for member in pack.getmembers():
            if member.name.startswith('/') or member.name.startswith('..'):
                __remove_dir(temp_dir)
                raise BadPackageError()
        # Decompress
        pack.extractall(temp_dir)

    # Then proceed with decompressed package.
    # First, we load the config.yaml file
    try:
        config = DeviceConfig(temp_dir)

        # Then, we determine if the kernel is a custom one
        if config.kernel is not None  and exists(join(temp_dir, config.kernel)):
            # This is a custom kernel, do not import !
            debug('piotr.package:package_import', 'Device kernel is a custom one, do not import.')
        else:
            # Look for a kernel in the deps/kernel/ directory. If many, pick the first one.
            debug('piotr.package:package_import', 'Look for importable compatible kernel ...')
            kernel_dir = join(
                temp_dir,
                'deps/kernel/'
            )
            if exists(kernel_dir):
                # Iterate over the kernels
                kernel_path = None
                for kernel in os.listdir(kernel_dir):
                    kernInfo = getKernInfo(join(
                        kernel_dir,
                        kernel
                    ))
                    if kernInfo is not None:
                        kernel_path = kernel
                        break

                # Do we have the same kernel already installed ?
                if kernel_path is not None:
                    if ud.get().hasKernel(kernel_path):
                        debug('piotr.package:package_import', 'Kernel is already installed, do not overwrite.')
                    else:
                        debug('piotr.package:package_import', 'Kernel is a new one, import.')
                        ud.get().addKernel(join(
                            kernel_dir,
                            kernel
                        ))
            else:
                error('piotr.package:package_import', 'Directory deps/kernel/ is missing.')
                __remove_dir(temp_dir)
                raise BadPackageError()

        # Then, we determine if the hostfs is a custom one
        if config.hostfs is not None and exists(join(temp_dir, config.hostfs)):
            # This is a custom kernel, do not import !
            debug('piotr.package:package_import', 'Device host FS is a custom one, do not import.')
        else:
            # Look for a hostfs in the deps/hostfs/ directory. If many, pick the first one.
            debug('piotr.package:package_import', 'Look for importable compatible host FS ...')
            hostfs_dir = join(
                temp_dir,
                'deps/hostfs/'
            )
            if exists(hostfs_dir):
                # Iterate over the filesystems
                hostfs_path = None
                for hostfs in os.listdir(hostfs_dir):
                    fsInfo = getHostFsInfo(hostfs)
                    if fsInfo is not None:
                        hostfs_path = hostfs
                        break

                # Do we have the same filesystem already installed ?
                if hostfs_path is not None:
                    if ud.get().hasHostFs(hostfs_path):
                        debug('piotr.package:package_import', 'Host filesystem is already installed, do not overwrite.')
                    else:
                        debug('piotr.package:package_import', 'Host filesystem is a new one, import.')
                        ud.get().addHostFs(join(
                            hostfs_dir,
                            hostfs
                        ))
                else:
                    error('piotr.package:package_import', 'Unable to parse host filesystem file')
            else:
                error('piotr.package:package_import', 'Directory deps/hostfs/ is missing.')
                __remove_dir(temp_dir)
                raise BadPackageError()


        # Look for DTB
        if config.dtb is not None:
            if exists(join(temp_dir, config.dtb)):
                # This is a custom dtb, do not import !
                debug('piotr.package:package_import', 'DTB is custom, do not import.')
            else:
                # Look for a dtb in the deps/dtb/ directory. If many, pick the first one.
                debug('piotr.package:package_import', 'Look for importable compatible dtb ...')
                dtb_dir = join(
                    temp_dir,
                    'deps/dtb/'
                )
                if exists(dtb_dir):
                    # Iterate over the kernels
                    dtb_path = None
                    for dtb in os.listdir(dtb_dir):
                        dtbInfo = getDtbInfo(join(
                            dtb_dir,
                            dtb
                        ))
                        if dtbInfo is not None:
                            dtb_path = dtb
                            break

                    # Do we have the same dtb already installed ?
                    if dtb_path is not None:
                        if ud.get().hasDtb(dtb_path):
                            debug('piotr.package:package_import', 'Dtb is already installed, do not overwrite.')
                        else:
                            debug('piotr.package:package_import', 'Dtb is a new one, import.')
                            ud.get().addDtb(join(
                                dtb_dir,
                                dtb
                            ))

                else:
                    error('piotr.package:package_import', 'Directory deps/kernel/ is missing.')
                    __remove_dir(temp_dir)
                    raise BadPackageError()

        # Check if a device with the same name does not exist
        devname, ext = splitext(basename(package_path))
        if ud.get().hasDevice(devname):
            error('Device %s already exists in your device directory !' % devname)
            __remove_dir(temp_dir)
            return False
        else:
            # Everything is okay, copy complete folder into ./piotr/devices/
            device_path = join(ud.get().getPath(), 'devices', devname)
            if not exists(device_path):
                os.mkdir(device_path)

            subprocess.call(
                'cp -rf %s/* %s' % (
                    temp_dir,
                    device_path
                ),
                shell=True
            )

            # Remove the deps directory
            subprocess.call(
                'rm -rf %s' % join(ud.get().getPath(), 'devices', devname, 'deps'),
                shell=True
            )

            # Success !
            return True


    except DeviceConfigMissing as missingConfig:
        debug('Package', 'Configuration file `config.yaml` is missing.')
        error('PackageManager', 'Malformed package %s' % basename(package_path))
        __remove_dir(temp_dir)
        raise BadPackageError()
    except DeviceConfigError as errorConfig:
        debug('Package', 'Cannot parse `config.yaml`')
        error('PackageManager', 'Malformed package %s' % basename(package_path))
        __remove_dir(temp_dir)
        raise BadPackageError()
