"""
Kernel utility functions.

This module provide utility functions for linux zImage kernels.

@raise KernelNotFound
@raise KernelFormatError
"""

import re
import zlib
from os.path import basename
from piotr.exceptions import KernelNotFound, KernelFormatError
from piotr.util.logger import warning, error, debug, info

ZIMAGE_KERNEL_HEADER = b'\x1F\x8B\x08\x00'

def _parseRawVersion(versionStr):
    """
    Parse version string and extract valuable information.

    @param  string  versionStr  Kernel version string
    @return dict    Kernel metadata
    """
    pattern = re.compile(b'^Linux version (((\d+\.)+)(\d+))(-\S+)?\s*([^#]+)#\d+(\s+SMP)?(.*)$')
    result = pattern.match(versionStr)
    if result is not None:
        return {
            'version': result.group(1),
            'tags': result.group(5).split(b'-')[1:] if result.group(5) is not None else [],
            'build_config': result.group(6),
            'build_date': result.group(8)
        }
    else:
        return None

def _extractKernelVersion(kernel):
    """
    Extract version string from raw kernel binary.

    @param  bytes   kernel  Raw kernel binary.
    @return string  Version string if found.
    """
    try:
        versionOffset = kernel.index(b'Linux version')
        for i in range(versionOffset, versionOffset+1024):
            if kernel[i]==0x00:
                return kernel[versionOffset:i]
        return None
    except IndexError as exc:
        return None

def _findKernel(kernel):
    """
    Find the start of a kernel compressed image from a raw zImage.

    @param  bytes   kernel
    @return int     offset to compressed kernel
    """
    try:
        return kernel.index(ZIMAGE_KERNEL_HEADER)
    except ValueError as exc:
        return None

def getKernVerFromImage(kernelPath):
    """
    Extract kernel version from kernel zImage.

    @param  string  Kernel zImage file path
    @return string  Kernel version string as extracted from kernel.
    """
    try:
        kernel = open(kernelPath,'rb').read()
        kernelOffset = _findKernel(kernel)
        if kernelOffset is not None:
            try:
                # Uncompress kernel from zImage
                uncompressedKernel = zlib.decompress(kernel[kernelOffset:], 16+zlib.MAX_WBITS)

                # Find kernel version
                rawVersion = _extractKernelVersion(uncompressedKernel)
                if rawVersion is not None:
                    # Parse raw version
                    return _parseRawVersion(rawVersion)
                else:
                    return None
            except zlib.error as zlibExc:
                raise KernelFormatError("Error while decompressing data (zlib)")
        else:
            raise KernelFormatError("Cannot find compressed kernel in image")
    except IOError as exc:
        raise KernelNotFound()


def getKernInfoFromImageName(kernelPath):
    """
    Extract kernel information from image name.

    We are expecting each kernel name to follow this naming:

    [version]-[platform].[cpu].[endianness]

    @param  string  kernel file path
    @return dict    Kernel information.
    """
    naming = re.compile('^([^\.]+)\.([^\.]+)\.([^\.]+)-(([0-9]+\.)+([0-9]+))$')
    result = naming.match(basename(kernelPath))
    if result is not None:
        version = result.group(4)
        platform = result.group(1)
        cpu = result.group(2)
        endian = result.group(3)

        return {
            'version': version,
            'platform': platform,
            'cpu': cpu,
            'endian': endian
        }
    else:
        return None


def getKernInfo(kernelPath):
    """
    Get kernel info from image name and raw image.

    @param  string   kernelPath  Path to kernel file.
    @return dict    Dictionnary with at least version number, platform and tags
    """
    # Try to extract info from image name
    debug('util.kernel:getKernInfo', 'Loading kernel info from image name ...')
    kernelInfo = getKernInfoFromImageName(kernelPath)
    if kernelInfo is not None:
        debug('util.kernel:getKernInfo', 'Loaded. Adding info from zImage parsing ...')
        kernelInfo['filepath'] = kernelPath
        kernelInfo['name'] = basename(kernelPath)
        kernelInfo['raw_info'] = getKernVerFromImage(kernelPath)
        debug('util.kernel:getKernInfo', 'Info extracted from zImage')
    else:
        error('util.kernel:getKernInfo', 'Cannot load kernel info from name')
        debug('util.kernel:getKernInfo', 'Loading kernel info from zImage ...')
        kernelInfo = getKernVerFromImage(kernelPath)
        if kernelInfo is not None:
            debug('util.kernel:getKernInfo', 'Info from zImage loaded')
            kernelInfo['filepath'] = kernelPath
            kernelInfo['name'] = basename(kernelPath)
        else:
            error('util.kernel:getKernInfo', 'Cannot load info from zImage')
            kernelInfo = None
    return kernelInfo
