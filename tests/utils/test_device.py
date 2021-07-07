import os
import unittest
from tempfile import TemporaryDirectory
from piotr.exceptions import DeviceConfigError
from piotr.util.device import DeviceConfig

# Default machine, no network, default hostfs and kernel.
CONFIG_FILE_0='''
version: "1.0"
device:
        name: Test device #1

        # Host configuration
        drive_type: virtio

        # Machine specifications
        machine:
                platform: virt
                memory: 1024
                cpu: cortex-a7
        bootargs: "root=/dev/vda rw console=ttyAMA0,115200"
'''

# Missing bootargs (mandatory)
CONFIG_FILE_1='''
version: "1.0"
device:
        name: Test device #1

        # Host configuration
        drive_type: virtio

        # Machine specifications
        machine:
                platform: virt
                memory: 1024
                cpu: cortex-a7
'''

# Missing CPU
CONFIG_FILE_2='''
version: "1.0"
device:
        name: Test device #1

        # Host configuration
        drive_type: virtio

        bootargs: "root=/dev/vda rw console=ttyAMA0,115200"

        # Machine specifications
        machine:
                platform: virt
                memory: 1024
'''

class DeviceConfigParsingTests(unittest.TestCase):
    '''Device configuration file tests.'''

    def setUp(self):
        '''
        Create some temporary configuration files.
        '''
        self.config0 = TemporaryDirectory()
        with open(os.path.join(self.config0.name, 'config.yaml'), 'w') as f:
            f.write(CONFIG_FILE_0)
            f.close()

        self.config1 = TemporaryDirectory()
        with open(os.path.join(self.config1.name, 'config.yaml'), 'w') as f:
            f.write(CONFIG_FILE_1)
            f.close()
        
        self.config2 = TemporaryDirectory()
        with open(os.path.join(self.config2.name, 'config.yaml'), 'w') as f:
            f.write(CONFIG_FILE_2)
            f.close()

    def setDown(self):
        self.config0.cleanup()
        self.config1.cleanup()
        self.config2.cleanup()
        
        
    def test_valid_config(self):
        '''Test valid config.yaml'''
        device = DeviceConfig(self.config0.name)
        self.assertTrue(device is not None)
    
    def test_invalid_bootargs(self):
        '''Test invalid config.yaml (bootargs missing)'''
        with self.assertRaises(DeviceConfigError):
            device = DeviceConfig(self.config1.name)
            self.assertTrue(device is not None)



