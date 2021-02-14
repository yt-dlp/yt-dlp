# coding: utf-8

from __future__ import unicode_literals

# Allow direct execution
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yt_dlp.options import _hide_login_info


class TestOptions(unittest.TestCase):
    def test_hide_login_info(self):
        self.assertEqual(_hide_login_info(['-u', 'foo', '-p', 'bar']),
                         ['-u', 'PRIVATE', '-p', 'PRIVATE'])
        self.assertEqual(_hide_login_info(['-u']), ['-u'])
        self.assertEqual(_hide_login_info(['-u', 'foo', '-u', 'bar']),
                         ['-u', 'PRIVATE', '-u', 'PRIVATE'])
        self.assertEqual(_hide_login_info(['--username=foo']),
                         ['--username=PRIVATE'])


if __name__ == '__main__':
    unittest.main()
