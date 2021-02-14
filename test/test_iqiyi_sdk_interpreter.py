#!/usr/bin/env python

from __future__ import unicode_literals

# Allow direct execution
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test.helper import FakeYDL
from yt_dlp.extractor import IqiyiIE


class IqiyiIEWithCredentials(IqiyiIE):
    def _get_login_info(self):
        return 'foo', 'bar'


class WarningLogger(object):
    def __init__(self):
        self.messages = []

    def warning(self, msg):
        self.messages.append(msg)

    def debug(self, msg):
        pass

    def error(self, msg):
        pass


class TestIqiyiSDKInterpreter(unittest.TestCase):
    def test_iqiyi_sdk_interpreter(self):
        '''
        Test the functionality of IqiyiSDKInterpreter by trying to log in

        If `sign` is incorrect, /validate call throws an HTTP 556 error
        '''
        logger = WarningLogger()
        ie = IqiyiIEWithCredentials(FakeYDL({'logger': logger}))
        ie._login()
        self.assertTrue('unable to log in:' in logger.messages[0])


if __name__ == '__main__':
    unittest.main()
