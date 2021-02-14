#!/usr/bin/env python
from __future__ import unicode_literals

# Allow direct execution
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import errno
import io
import json
import re
import subprocess

from yt_dlp.swfinterp import SWFInterpreter


TEST_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'swftests')


class TestSWFInterpreter(unittest.TestCase):
    pass


def _make_testfunc(testfile):
    m = re.match(r'^(.*)\.(as)$', testfile)
    if not m:
        return
    test_id = m.group(1)

    def test_func(self):
        as_file = os.path.join(TEST_DIR, testfile)
        swf_file = os.path.join(TEST_DIR, test_id + '.swf')
        if ((not os.path.exists(swf_file))
                or os.path.getmtime(swf_file) < os.path.getmtime(as_file)):
            # Recompile
            try:
                subprocess.check_call([
                    'mxmlc', '-output', swf_file,
                    '-static-link-runtime-shared-libraries', as_file])
            except OSError as ose:
                if ose.errno == errno.ENOENT:
                    print('mxmlc not found! Skipping test.')
                    return
                raise

        with open(swf_file, 'rb') as swf_f:
            swf_content = swf_f.read()
        swfi = SWFInterpreter(swf_content)

        with io.open(as_file, 'r', encoding='utf-8') as as_f:
            as_content = as_f.read()

        def _find_spec(key):
            m = re.search(
                r'(?m)^//\s*%s:\s*(.*?)\n' % re.escape(key), as_content)
            if not m:
                raise ValueError('Cannot find %s in %s' % (key, testfile))
            return json.loads(m.group(1))

        input_args = _find_spec('input')
        output = _find_spec('output')

        swf_class = swfi.extract_class(test_id)
        func = swfi.extract_function(swf_class, 'main')
        res = func(input_args)
        self.assertEqual(res, output)

    test_func.__name__ = str('test_swf_' + test_id)
    setattr(TestSWFInterpreter, test_func.__name__, test_func)


for testfile in os.listdir(TEST_DIR):
    _make_testfunc(testfile)

if __name__ == '__main__':
    unittest.main()
