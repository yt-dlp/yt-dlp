#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from test.helper import (
    FakeYDL,
)
from yt_dlp.jsinterp.common import ExternalJSI
from yt_dlp.jsinterp._deno import DenoJSI, DenoJITlessJSI, DenoJSDomJSI
from yt_dlp.jsinterp._phantomjs import PhantomJSJSI


class Base:
    class TestExternalJSI(unittest.TestCase):
        _JSI_CLASS: type[ExternalJSI] = None

        def setUp(self):
            self.ydl = FakeYDL()
            self.jsi = self._JSI_CLASS(self.ydl, 19, {})
            if not self.jsi_available():
                self.skipTest('Not available')

        def jsi_available(self):
            return self._JSI_CLASS and self._JSI_CLASS.exe_version

        def test_execute(self):
            self.assertEqual(self.jsi.execute('console.log("Hello, world!");'), 'Hello, world!')


class TestDeno(Base.TestExternalJSI):
    _JSI_CLASS = DenoJSI


class TestDenoJITless(Base.TestExternalJSI):
    _JSI_CLASS = DenoJITlessJSI


class TestDenoDom(Base.TestExternalJSI):
    _JSI_CLASS = DenoJSDomJSI


class TestPhantomJS(Base.TestExternalJSI):
    _JSI_CLASS = PhantomJSJSI


if __name__ == '__main__':
    unittest.main()
