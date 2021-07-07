"""
Piotr Device management module.
"""

import re
import yaml
from os.path import isdir, exists, join, isfile
from piotr.util.logger import error, warning, info, debug
from piotr.exceptions import DeviceConfigError, DeviceNotFound, DeviceConfigMissing


class DeviceConfig(object):

    """
    Piotr Device class

    This class stores all the information regarding a Piotr IoT device:
    - device name
    - kernel and hostfs versions
    - machine characteristics (cpu, model, ram)
    - external devices (sd card, network interfaces)
    """

    def __init__(self, devicePath):
        self.__path = devicePath

        # Default parameters
        self.name = None
        self.platform = 'virt'
        self.cpu = None
        self.endian = 'little'
        self.kernel = None
        self.hostfs = None
        self.memory = None
        self.netifs = []
        self.dtb = None
        self.sd = None
        self.bootargs = None
        self.nics = []
        self.redirs = []
        self.virtio = 'device'
        self.guestfs = 'virtfs'

        # Load device from config file
        self.__load()

    def __load(self):
        """
        Load device configuration file.

        Parses YAML configuration file, and performs some sanity checks.
        """
        # First, check if devicePath exists and is a directory.
        if exists(self.__path) and isdir(self.__path):
            configPath = join(self.__path, 'config.yaml')
            if exists(configPath) and isfile(configPath):
                # Load configuration file (yaml)
                with open(configPath) as config:
                    try:
                        self.__deviceConfig = yaml.safe_load(config)

                        # Load device properties
                        self.__loadDeviceParams()
                    except yaml.YAMLError as exc:
                        debug('util.device:__load', 'Error while parsing YAML configuration file')
                        error('Util:Device','Error while parsing YAML configuration')
                        raise DeviceConfigMissing()
            else:
                debug('util.device:__load', 'config.yaml is missing')
                error('Util:Device', 'File config.yaml missing for device')
                raise DeviceConfigMissing()
        else:
            debug('util.device:__load', 'Device path does not exist')
            raise DeviceNotFound()


    def __loadDeviceParams(self):
        """
        Load device parameters based on configuration.
        """
        # Check config file version
        if self.__deviceConfig['version'] == "1.0":
            if 'device' in self.__deviceConfig:
                device = self.__deviceConfig['device']
                # Load machine specifics if any
                if 'machine' in device:
                    for i in device['machine'].keys():
                        if i == 'platform':
                            self.platform = device['machine']['platform']
                        elif i == 'cpu':
                            self.cpu = device['machine']['cpu']
                        elif i == 'endian':
                            self.endian = device['machine']['endian']
                        elif i == 'memory':
                            self.memory = device['machine']['memory']
                        elif i == 'dtb':
                            self.dtb = device['machine']['dtb']

                # Name
                if 'name' in device:
                    self.name = device['name']

                # load kernel if specified
                if 'kernel' in device:
                    self.kernel = device['kernel']

                # load hostfs if specified
                if 'hostfs' in device:
                    self.hostfs = device['hostfs']
                else:
                    self.hostfs = None

                # load hostfs interface
                if 'drive_type' in device:
                    self.drivetype = device['drive_type'].lower()
                    if self.drivetype not in ['pci', 'virtio', 'scsi']:
                        warning('piotr.util.device', 'Unknown drive type value in config.yaml')
                        raise DeviceConfigError('incorrect drive_type value "%s", must be one of the following: virtio, pci, scsi' % device['drive_type'])
                else:
                    self.drivetype = 'scsi'

                # virtio bus
                if 'virtio' in device:
                    if device['virtio'].lower() in ['pci', 'device']:
                        self.virtio = device['virtio']
                    else:
                        warning('piotr.util.device', 'Unknown virtio value in config.yaml')
                        raise DeviceConfigError('incorrect virtio value "%s", must be one of the following: pci, device' % device['virtio'])

                if 'guestfs' in device:
                    if device['guestfs'].lower() in ['virtfs', 'embed']:
                        self.guestfs = device['guestfs']
                    else:
                        warning(
                            'piotr.util.device',
                            'Unknown "guestfs" option value (%s)' % device['guestfs']
                        )
                        raise DeviceConfigError('unknown guestfs value "%s", must be one of the following: virtfs, embed' % device['guestfs'])

                if 'sd' in device:
                    self.sd = device['sd']

                if 'bootargs' in device:
                    self.bootargs = device['bootargs']

                # Parse network definitions
                if 'network' in device:
                    # Loop over interfaces
                    for interface in device['network']:
                        netname = interface
                        netdef = device['network'][interface]
                        if ',' in netdef:
                            nettype,netif=netdef.split(',')[:2]
                            nettype = nettype.lower().lstrip().rstrip()
                            netif = netif.lstrip().rstrip()
                            if nettype == 'user':
                                debug('piotr.util.device', 'network interface should not have a name, discarding name.')
                                netif = None
                            elif nettype != 'tap':
                                debug('piotr.util.device', 'unknown network interface mode')
                                raise DeviceConfigError('Unknown network interface type `%s` for network interface `%s`' % (
                                    nettype,
                                    netname
                                ))
                        else:
                            nettype,netif=netdef,None
                            nettype = nettype.lower().lstrip().rstrip()
                            if nettype not in ['user']:
                                debug('piotr.util.device', 'unknown network interface mode')
                                raise DeviceConfigError('Unknown network interface type `%s` for network interface `%s`' % (
                                    nettype,
                                    netname
                                ))

                        self.nics.append({
                            'name': netname,
                            'type': nettype,
                            'interface': netif
                        })

                # Parse network redirects
                if 'redirect' in device:
                    # Loop on redirection rules
                    for iface in device['redirect']:
                        rules = device['redirect'][iface]
                        if isinstance(rules, dict):
                            for rule in rules:
                                rule_name = rule
                                rule_desc = device['redirect'][iface][rule]
                                result = re.match('^(tcp|udp)\s*,\s*([0-9]+)\s*,\s*([0-9]+)\s*$', rule_desc)
                                if result is not None:
                                    rule_proto = result.group(1)
                                    rule_local_port = int(result.group(2))
                                    rule_dest_port = int(result.group(3))
                                    self.redirs.append({
                                        'iface': iface,
                                        'name': rule_name,
                                        'local': rule_local_port,
                                        'dest': rule_dest_port,
                                        'proto': rule_proto
                                    })
                                else:
                                    raise DeviceConfigError('Wrong format in redirection rule `%s` for interface `%s`'%(
                                        rule_name,
                                        iface
                                    ))
                        else:
                            raise DeviceConfigError('Bad format for network redirection rules, expecting per-interface rules.')

                # Make sure we need everything
                if self.bootargs is None:
                    error('util.device:__loadDeviceParams', 'bootargs is missing')
                    raise DeviceConfigError('Critical parameter missing from device configuration file')

                # By default, cpu will be handled by qemu and will default to cortex-a15 if not
                # specified. Endianness is little by default. Only platform is needed !
                if self.platform is None:
                    error('util.device:__loadDeviceParams', 'platform is not specified')
                    raise DeviceConfigError('Critical parameter missing from device configuration file')

            else:
                debug('util.device:__loadDeviceParams', '"device" entry missing in configuration')
                error('Util:Device', 'Device entry is missing from configuration file')
                raise DeviceConfigError('No device entry in configuration file')
        else:
            error('Util:Device', 'Unsupported version of device configuration file')
            raise


    def getPath(self):
        """
        Return device path
        """
        return self.__path
