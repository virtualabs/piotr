"""
DTBs
"""

import re

def getDtbInfo(dtbPath):
    """
    Extract information from DTB
    """
    pattern = re.compile('^([^-]+)-([^\.]+)\.dtb$')
    result = pattern.match(dtbPath)
    if result is not None:
        return {
            'name': dtbPath,
            'platform': result.group(1),
            'cpu': result.group(2)
        }
    else:
        return None
