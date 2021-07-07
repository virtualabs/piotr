import unittest
import zlib
import tempfile
import os
from piotr.exceptions import KernelFormatError
from piotr.exceptions import KernelNotFound
from piotr.util.kernel import getKernInfoFromImageName, getKernVerFromImage

class KernelParsingTests(unittest.TestCase):
    """
    Kernel parsing tests.
    """

    def test_good_name(self):
        """
        Try parsing a well formatted name.
        """
        name = 'virt.cortex-a7.little-1.2.3'
        result = getKernInfoFromImageName(name)
        self.assertEqual(result['version'], '1.2.3')
        self.assertEqual(result['platform'], 'virt')
        self.assertEqual(result['cpu'], 'cortex-a7')

    def test_bad_name(self):
        """
        Parse a bad name
        """
        name = 'virt.cortex-a7.little.toto-1.3'
        self.assertIsNone(getKernInfoFromImageName(name))
