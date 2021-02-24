from __future__ import unicode_literals

import errno
import io
import hashlib
import json
import os.path
import re
import types
import ssl
import sys

import yt_dlp.extractor
from yt_dlp import YoutubeDL
from yt_dlp.compat import (
    compat_os_name,
    compat_str,
)
from yt_dlp.utils import (
    preferredencoding,
    write_string,
)


def get_params(override=None):
    PARAMETERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "parameters.json")
    LOCAL_PARAMETERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "local_parameters.json")
    with io.open(PARAMETERS_FILE, encoding='utf-8') as pf:
        parameters = json.load(pf)
    if os.path.exists(LOCAL_PARAMETERS_FILE):
        with io.open(LOCAL_PARAMETERS_FILE, encoding='utf-8') as pf:
            parameters.update(json.load(pf))
    if override:
        parameters.update(override)
    return parameters


def try_rm(filename):
    """ Remove a file if it exists """
    try:
        os.remove(filename)
    except OSError as ose:
        if ose.errno != errno.ENOENT:
            raise


def report_warning(message):
    '''
    Print the message to stderr, it will be prefixed with 'WARNING:'
    If stderr is a tty file the 'WARNING:' will be colored
    '''
    if sys.stderr.isatty() and compat_os_name != 'nt':
        _msg_header = '\033[0;33mWARNING:\033[0m'
    else:
        _msg_header = 'WARNING:'
    output = '%s %s\n' % (_msg_header, message)
    if 'b' in getattr(sys.stderr, 'mode', '') or sys.version_info[0] < 3:
        output = output.encode(preferredencoding())
    sys.stderr.write(output)


class FakeYDL(YoutubeDL):
    def __init__(self, override=None):
        # Different instances of the downloader can't share the same dictionary
        # some test set the "sublang" parameter, which would break the md5 checks.
        params = get_params(override=override)
        super(FakeYDL, self).__init__(params, auto_init=False)
        self.result = []

    def to_screen(self, s, skip_eol=None):
        print(s)

    def trouble(self, s, tb=None):
        raise Exception(s)

    def download(self, x):
        self.result.append(x)

    def expect_warning(self, regex):
        # Silence an expected warning matching a regex
        old_report_warning = self.report_warning

        def report_warning(self, message):
            if re.match(regex, message):
                return
            old_report_warning(message)
        self.report_warning = types.MethodType(report_warning, self)


def gettestcases(include_onlymatching=False):
    for ie in yt_dlp.extractor.gen_extractors():
        for tc in ie.get_testcases(include_onlymatching):
            yield tc


md5 = lambda s: hashlib.md5(s.encode('utf-8')).hexdigest()


def expect_value(self, got, expected, field):
    if isinstance(expected, compat_str) and expected.startswith('re:'):
        match_str = expected[len('re:'):]
        match_rex = re.compile(match_str)

        self.assertTrue(
            isinstance(got, compat_str),
            'Expected a %s object, but got %s for field %s' % (
                compat_str.__name__, type(got).__name__, field))
        self.assertTrue(
            match_rex.match(got),
            'field %s (value: %r) should match %r' % (field, got, match_str))
    elif isinstance(expected, compat_str) and expected.startswith('startswith:'):
        start_str = expected[len('startswith:'):]
        self.assertTrue(
            isinstance(got, compat_str),
            'Expected a %s object, but got %s for field %s' % (
                compat_str.__name__, type(got).__name__, field))
        self.assertTrue(
            got.startswith(start_str),
            'field %s (value: %r) should start with %r' % (field, got, start_str))
    elif isinstance(expected, compat_str) and expected.startswith('contains:'):
        contains_str = expected[len('contains:'):]
        self.assertTrue(
            isinstance(got, compat_str),
            'Expected a %s object, but got %s for field %s' % (
                compat_str.__name__, type(got).__name__, field))
        self.assertTrue(
            contains_str in got,
            'field %s (value: %r) should contain %r' % (field, got, contains_str))
    elif isinstance(expected, type):
        self.assertTrue(
            isinstance(got, expected),
            'Expected type %r for field %s, but got value %r of type %r' % (expected, field, got, type(got)))
    elif isinstance(expected, dict) and isinstance(got, dict):
        expect_dict(self, got, expected)
    elif isinstance(expected, list) and isinstance(got, list):
        self.assertEqual(
            len(expected), len(got),
            'Expect a list of length %d, but got a list of length %d for field %s' % (
                len(expected), len(got), field))
        for index, (item_got, item_expected) in enumerate(zip(got, expected)):
            type_got = type(item_got)
            type_expected = type(item_expected)
            self.assertEqual(
                type_expected, type_got,
                'Type mismatch for list item at index %d for field %s, expected %r, got %r' % (
                    index, field, type_expected, type_got))
            expect_value(self, item_got, item_expected, field)
    else:
        if isinstance(expected, compat_str) and expected.startswith('md5:'):
            self.assertTrue(
                isinstance(got, compat_str),
                'Expected field %s to be a unicode object, but got value %r of type %r' % (field, got, type(got)))
            got = 'md5:' + md5(got)
        elif isinstance(expected, compat_str) and re.match(r'^(?:min|max)?count:\d+', expected):
            self.assertTrue(
                isinstance(got, (list, dict)),
                'Expected field %s to be a list or a dict, but it is of type %s' % (
                    field, type(got).__name__))
            op, _, expected_num = expected.partition(':')
            expected_num = int(expected_num)
            if op == 'mincount':
                assert_func = assertGreaterEqual
                msg_tmpl = 'Expected %d items in field %s, but only got %d'
            elif op == 'maxcount':
                assert_func = assertLessEqual
                msg_tmpl = 'Expected maximum %d items in field %s, but got %d'
            elif op == 'count':
                assert_func = assertEqual
                msg_tmpl = 'Expected exactly %d items in field %s, but got %d'
            else:
                assert False
            assert_func(
                self, len(got), expected_num,
                msg_tmpl % (expected_num, field, len(got)))
            return
        self.assertEqual(
            expected, got,
            'Invalid value for field %s, expected %r, got %r' % (field, expected, got))


def expect_dict(self, got_dict, expected_dict):
    for info_field, expected in expected_dict.items():
        got = got_dict.get(info_field)
        expect_value(self, got, expected, info_field)


def expect_info_dict(self, got_dict, expected_dict):
    expect_dict(self, got_dict, expected_dict)
    # Check for the presence of mandatory fields
    if got_dict.get('_type') not in ('playlist', 'multi_video'):
        for key in ('id', 'url', 'title', 'ext'):
            self.assertTrue(got_dict.get(key), 'Missing mandatory field %s' % key)
    # Check for mandatory fields that are automatically set by YoutubeDL
    for key in ['webpage_url', 'extractor', 'extractor_key']:
        self.assertTrue(got_dict.get(key), 'Missing field: %s' % key)

    # Are checkable fields missing from the test case definition?
    test_info_dict = dict((key, value if not isinstance(value, compat_str) or len(value) < 250 else 'md5:' + md5(value))
                          for key, value in got_dict.items()
                          if value and key in ('id', 'title', 'description', 'uploader', 'upload_date', 'timestamp', 'uploader_id', 'location', 'age_limit'))
    missing_keys = set(test_info_dict.keys()) - set(expected_dict.keys())
    if missing_keys:
        def _repr(v):
            if isinstance(v, compat_str):
                return "'%s'" % v.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
            else:
                return repr(v)
        info_dict_str = ''
        if len(missing_keys) != len(expected_dict):
            info_dict_str += ''.join(
                '    %s: %s,\n' % (_repr(k), _repr(v))
                for k, v in test_info_dict.items() if k not in missing_keys)

            if info_dict_str:
                info_dict_str += '\n'
        info_dict_str += ''.join(
            '    %s: %s,\n' % (_repr(k), _repr(test_info_dict[k]))
            for k in missing_keys)
        write_string(
            '\n\'info_dict\': {\n' + info_dict_str + '},\n', out=sys.stderr)
        self.assertFalse(
            missing_keys,
            'Missing keys in test definition: %s' % (
                ', '.join(sorted(missing_keys))))


def assertRegexpMatches(self, text, regexp, msg=None):
    if hasattr(self, 'assertRegexp'):
        return self.assertRegexp(text, regexp, msg)
    else:
        m = re.match(regexp, text)
        if not m:
            note = 'Regexp didn\'t match: %r not found' % (regexp)
            if len(text) < 1000:
                note += ' in %r' % text
            if msg is None:
                msg = note
            else:
                msg = note + ', ' + msg
            self.assertTrue(m, msg)


def assertGreaterEqual(self, got, expected, msg=None):
    if not (got >= expected):
        if msg is None:
            msg = '%r not greater than or equal to %r' % (got, expected)
        self.assertTrue(got >= expected, msg)


def assertLessEqual(self, got, expected, msg=None):
    if not (got <= expected):
        if msg is None:
            msg = '%r not less than or equal to %r' % (got, expected)
        self.assertTrue(got <= expected, msg)


def assertEqual(self, got, expected, msg=None):
    if not (got == expected):
        if msg is None:
            msg = '%r not equal to %r' % (got, expected)
        self.assertTrue(got == expected, msg)


def expect_warnings(ydl, warnings_re):
    real_warning = ydl.report_warning

    def _report_warning(w):
        if not any(re.search(w_re, w) for w_re in warnings_re):
            real_warning(w)

    ydl.report_warning = _report_warning


def http_server_port(httpd):
    if os.name == 'java' and isinstance(httpd.socket, ssl.SSLSocket):
        # In Jython SSLSocket is not a subclass of socket.socket
        sock = httpd.socket.sock
    else:
        sock = httpd.socket
    return sock.getsockname()[1]
