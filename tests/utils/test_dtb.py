import unittest
from piotr.util.dtb import getDtbInfo

class DtbParsingTests(unittest.TestCase):
    """
    Dtb parsing tests.
    """

    def test_good_name(self):
        '''Test valid DTB name'''
        name = 'platform-cpu.dtb'
        result = getDtbInfo(name)
        self.assertEqual(result['platform'], 'platform')
        self.assertEqual(result['cpu'], 'cpu')

    def test_good_name_with_weird_cpu(self):
        '''Test valid DTB name with weird CPU'''
        name = 'platform-cpu-mark_strange_characters!.dtb'
        result = getDtbInfo(name)
        self.assertEqual(result['platform'], 'platform')
        self.assertEqual(result['cpu'], 'cpu-mark_strange_characters!')

    def test_bad_name(self):
        '''Test invalid DTB name'''
        name = 'platform_cpu.dtb'
        result = getDtbInfo(name)
        self.assertIsNone(result)
