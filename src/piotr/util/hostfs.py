"""
Host filesystem helpers.

Host FS must follow this naming:

name-platform-X.Y.Z-tags.fstype

Supported filesystems:
- ext2, ext3, ext4

"""
import re

def getHostFsInfo(hostfs):
    """
    Extract information from host filesystem image.

    @param  string  hostfs  Path to Host filesystem
    @return object          HostFS information or None on error
    """
    pattern = re.compile('^([^\.]+)\.([^\.]+)\.([^\.]+)-(([0-9]+\.)+([0-9]+))\.([^\.]+)$')
    result = pattern.match(hostfs)
    if result is None:
        return None
    else:
        version = result.group(4)
        platform = result.group(1)
        cpu = result.group(2)
        endian = result.group(3)
        ext = result.group(7)
        return {
            'name': hostfs,
            'file': hostfs,
            'filepath': hostfs,
            'version': version,
            'platform': platform,
            'cpu': cpu,
            'endian': endian,
            'type': ext
        }
