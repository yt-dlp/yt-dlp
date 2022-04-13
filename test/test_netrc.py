import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from yt_dlp.extractor import gen_extractor_classes
from yt_dlp.extractor.common import InfoExtractor

NO_LOGIN = InfoExtractor._perform_login


class TestNetRc(unittest.TestCase):
    def test_netrc_present(self):
        for ie in gen_extractor_classes():
            if ie._perform_login is NO_LOGIN:
                continue
            self.assertTrue(
                ie._NETRC_MACHINE,
                'Extractor %s supports login, but is missing a _NETRC_MACHINE property' % ie.IE_NAME)


if __name__ == '__main__':
    unittest.main()
