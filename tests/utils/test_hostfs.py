import unittest
from piotr.util.hostfs import getHostFsInfo

class HostFsParsingTests(unittest.TestCase):
    """
    HostFs parsing tests.
    """

    def test_good_name(self):
        '''Test valid HostFS name'''
        name = 'virt.cortex-a7.little-1.2.3.ext2'
        result = getHostFsInfo(name)
        self.assertEqual(result['platform'], 'virt')
        self.assertEqual(result['cpu'], 'cortex-a7')
        self.assertEqual(result['endian'], 'little')
        self.assertEqual(result['version'], '1.2.3')
        self.assertEqual(result['type'], 'ext2')

    def test_bad_name(self):
        '''Test invalid HostFS name'''
        name = 'virt_cortex-a7_test.ext2'
        result = getHostFsInfo(name)
        self.assertEqual(result, None)
