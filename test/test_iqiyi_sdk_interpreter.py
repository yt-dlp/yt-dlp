#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from test.helper import FakeYDL, is_download_test
from yt_dlp.extractor import IqiyiIE


class WarningLogger:
    def __init__(self):
        self.messages = []

    def warning(self, msg):
        self.messages.append(msg)

    def debug(self, msg):
        pass

    def error(self, msg):
        pass


@is_download_test
class TestIqiyiSDKInterpreter(unittest.TestCase):
    def test_iqiyi_sdk_interpreter(self):
        """
        Test the functionality of IqiyiSDKInterpreter by trying to log in

        If `sign` is incorrect, /validate call throws an HTTP 556 error
        """
        logger = WarningLogger()
        ie = IqiyiIE(FakeYDL({'logger': logger}))
        ie._perform_login('foo', 'bar')
        self.assertTrue('unable to log in:' in logger.messages[0])


if __name__ == '__main__':
    unittest.main()
