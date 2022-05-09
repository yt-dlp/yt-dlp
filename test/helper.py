import errno
import hashlib
import json
import os.path
import re
import ssl
import sys
import types

import yt_dlp.extractor
from yt_dlp import YoutubeDL
from yt_dlp.compat import compat_os_name, compat_str
from yt_dlp.utils import preferredencoding, write_string

if 'pytest' in sys.modules:
    import pytest
    is_download_test = pytest.mark.download
else:
    def is_download_test(testClass):
        return testClass


def get_params(override=None):
    PARAMETERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'parameters.json')
    LOCAL_PARAMETERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         'local_parameters.json')
    with open(PARAMETERS_FILE, encoding='utf-8') as pf:
        parameters = json.load(pf)
    if os.path.exists(LOCAL_PARAMETERS_FILE):
        with open(LOCAL_PARAMETERS_FILE, encoding='utf-8') as pf:
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
    output = f'{_msg_header} {message}\n'
    if 'b' in getattr(sys.stderr, 'mode', ''):
        output = output.encode(preferredencoding())
    sys.stderr.write(output)


class FakeYDL(YoutubeDL):
    def __init__(self, override=None):
        # Different instances of the downloader can't share the same dictionary
        # some test set the "sublang" parameter, which would break the md5 checks.
        params = get_params(override=override)
        super().__init__(params, auto_init=False)
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
        yield from ie.get_testcases(include_onlymatching)


md5 = lambda s: hashlib.md5(s.encode()).hexdigest()


def expect_value(self, got, expected, field):
    if isinstance(expected, compat_str) and expected.startswith('re:'):
        match_str = expected[len('re:'):]
        match_rex = re.compile(match_str)

        self.assertTrue(
            isinstance(got, compat_str),
            f'Expected a {compat_str.__name__} object, but got {type(got).__name__} for field {field}')
        self.assertTrue(
            match_rex.match(got),
            f'field {field} (value: {got!r}) should match {match_str!r}')
    elif isinstance(expected, compat_str) and expected.startswith('startswith:'):
        start_str = expected[len('startswith:'):]
        self.assertTrue(
            isinstance(got, compat_str),
            f'Expected a {compat_str.__name__} object, but got {type(got).__name__} for field {field}')
        self.assertTrue(
            got.startswith(start_str),
            f'field {field} (value: {got!r}) should start with {start_str!r}')
    elif isinstance(expected, compat_str) and expected.startswith('contains:'):
        contains_str = expected[len('contains:'):]
        self.assertTrue(
            isinstance(got, compat_str),
            f'Expected a {compat_str.__name__} object, but got {type(got).__name__} for field {field}')
        self.assertTrue(
            contains_str in got,
            f'field {field} (value: {got!r}) should contain {contains_str!r}')
    elif isinstance(expected, type):
        self.assertTrue(
            isinstance(got, expected),
            f'Expected type {expected!r} for field {field}, but got value {got!r} of type {type(got)!r}')
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
                f'Expected field {field} to be a unicode object, but got value {got!r} of type {type(got)!r}')
            got = 'md5:' + md5(got)
        elif isinstance(expected, compat_str) and re.match(r'^(?:min|max)?count:\d+', expected):
            self.assertTrue(
                isinstance(got, (list, dict)),
                f'Expected field {field} to be a list or a dict, but it is of type {type(got).__name__}')
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
            f'Invalid value for field {field}, expected {expected!r}, got {got!r}')


def expect_dict(self, got_dict, expected_dict):
    for info_field, expected in expected_dict.items():
        got = got_dict.get(info_field)
        expect_value(self, got, expected, info_field)


def sanitize_got_info_dict(got_dict):
    IGNORED_FIELDS = (
        *YoutubeDL._format_fields,

        # Lists
        'formats', 'thumbnails', 'subtitles', 'automatic_captions', 'comments', 'entries',

        # Auto-generated
        'autonumber', 'playlist', 'format_index', 'video_ext', 'audio_ext', 'duration_string', 'epoch',
        'fulltitle', 'extractor', 'extractor_key', 'filepath', 'infojson_filename', 'original_url', 'n_entries',

        # Only live_status needs to be checked
        'is_live', 'was_live',
    )

    IGNORED_PREFIXES = ('', 'playlist', 'requested', 'webpage')

    def sanitize(key, value):
        if isinstance(value, str) and len(value) > 100 and key != 'thumbnail':
            return f'md5:{md5(value)}'
        elif isinstance(value, list) and len(value) > 10:
            return f'count:{len(value)}'
        elif key.endswith('_count') and isinstance(value, int):
            return int
        return value

    test_info_dict = {
        key: sanitize(key, value) for key, value in got_dict.items()
        if value is not None and key not in IGNORED_FIELDS and not any(
            key.startswith(f'{prefix}_') for prefix in IGNORED_PREFIXES)
    }

    # display_id may be generated from id
    if test_info_dict.get('display_id') == test_info_dict.get('id'):
        test_info_dict.pop('display_id')

    return test_info_dict


def expect_info_dict(self, got_dict, expected_dict):
    expect_dict(self, got_dict, expected_dict)
    # Check for the presence of mandatory fields
    if got_dict.get('_type') not in ('playlist', 'multi_video'):
        mandatory_fields = ['id', 'title']
        if expected_dict.get('ext'):
            mandatory_fields.extend(('url', 'ext'))
        for key in mandatory_fields:
            self.assertTrue(got_dict.get(key), 'Missing mandatory field %s' % key)
    # Check for mandatory fields that are automatically set by YoutubeDL
    for key in ['webpage_url', 'extractor', 'extractor_key']:
        self.assertTrue(got_dict.get(key), 'Missing field: %s' % key)

    test_info_dict = sanitize_got_info_dict(got_dict)

    missing_keys = set(test_info_dict.keys()) - set(expected_dict.keys())
    if missing_keys:
        def _repr(v):
            if isinstance(v, compat_str):
                return "'%s'" % v.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
            elif isinstance(v, type):
                return v.__name__
            else:
                return repr(v)
        info_dict_str = ''
        if len(missing_keys) != len(expected_dict):
            info_dict_str += ''.join(
                f'    {_repr(k)}: {_repr(v)},\n'
                for k, v in test_info_dict.items() if k not in missing_keys)

            if info_dict_str:
                info_dict_str += '\n'
        info_dict_str += ''.join(
            f'    {_repr(k)}: {_repr(test_info_dict[k])},\n'
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
            msg = f'{got!r} not greater than or equal to {expected!r}'
        self.assertTrue(got >= expected, msg)


def assertLessEqual(self, got, expected, msg=None):
    if not (got <= expected):
        if msg is None:
            msg = f'{got!r} not less than or equal to {expected!r}'
        self.assertTrue(got <= expected, msg)


def assertEqual(self, got, expected, msg=None):
    if not (got == expected):
        if msg is None:
            msg = f'{got!r} not equal to {expected!r}'
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
