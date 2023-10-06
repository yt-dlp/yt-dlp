#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import contextlib
import subprocess

from yt_dlp.utils import Popen

rootDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAZY_EXTRACTORS = 'yt_dlp/extractor/lazy_extractors.py'


class TestExecution(unittest.TestCase):
    def run_yt_dlp(self, exe=(sys.executable, 'yt_dlp/__main__.py'), opts=('--version', )):
        stdout, stderr, returncode = Popen.run(
            [*exe, '--ignore-config', *opts], cwd=rootDir, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(stderr, file=sys.stderr)
        self.assertEqual(returncode, 0)
        return stdout.strip(), stderr.strip()

    def test_main_exec(self):
        self.run_yt_dlp()

    def test_import(self):
        self.run_yt_dlp(exe=(sys.executable, '-c', 'import yt_dlp'))

    def test_module_exec(self):
        self.run_yt_dlp(exe=(sys.executable, '-m', 'yt_dlp'))

    def test_cmdline_umlauts(self):
        _, stderr = self.run_yt_dlp(opts=('ä', '--version'))
        self.assertFalse(stderr)

    def test_lazy_extractors(self):
        try:
            subprocess.check_call([sys.executable, 'devscripts/make_lazy_extractors.py', LAZY_EXTRACTORS],
                                  cwd=rootDir, stdout=subprocess.DEVNULL)
            self.assertTrue(os.path.exists(LAZY_EXTRACTORS))

            _, stderr = self.run_yt_dlp(opts=('-s', 'test:'))
            # `MIN_RECOMMENDED` emits a deprecated feature warning for deprecated python versions
            if stderr and stderr.startswith('Deprecated Feature: Support for Python'):
                stderr = ''
            self.assertFalse(stderr)

            subprocess.check_call([sys.executable, 'test/test_all_urls.py'], cwd=rootDir, stdout=subprocess.DEVNULL)
        finally:
            with contextlib.suppress(OSError):
                os.remove(LAZY_EXTRACTORS)


if __name__ == '__main__':
    unittest.main()
