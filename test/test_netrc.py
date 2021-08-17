# coding: utf-8
from __future__ import unicode_literals

import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from yt_dlp.extractor import (
    gen_extractors,
)


class TestNetRc(unittest.TestCase):
    def test_netrc_present(self):
        for ie in gen_extractors():
            if not hasattr(ie, '_login'):
                continue
            self.assertTrue(
                hasattr(ie, '_NETRC_MACHINE'),
                'Extractor %s supports login, but is missing a _NETRC_MACHINE property' % ie.IE_NAME)


if __name__ == '__main__':
    unittest.main()
