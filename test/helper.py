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
from yt_dlp.utils import preferredencoding, try_call, write_string, find_available_port

if 'pytest' in sys.modules:
    import pytest
    is_download_test = pytest.mark.download
else:
    def is_download_test(test_class):
        return test_class


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


def report_warning(message, *args, **kwargs):
    """
    Print the message to stderr, it will be prefixed with 'WARNING:'
    If stderr is a tty file the 'WARNING:' will be colored
    """
    if sys.stderr.isatty() and os.name != 'nt':
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

    def to_screen(self, s, *args, **kwargs):
        print(s)

    def trouble(self, s, *args, **kwargs):
        raise Exception(s)

    def download(self, x):
        self.result.append(x)

    def expect_warning(self, regex):
        # Silence an expected warning matching a regex
        old_report_warning = self.report_warning

        def report_warning(self, message, *args, **kwargs):
            if re.match(regex, message):
                return
            old_report_warning(message, *args, **kwargs)
        self.report_warning = types.MethodType(report_warning, self)


def gettestcases(include_onlymatching=False):
    for ie in yt_dlp.extractor.gen_extractors():
        yield from ie.get_testcases(include_onlymatching)


def getwebpagetestcases():
    for ie in yt_dlp.extractor.gen_extractors():
        for tc in ie.get_webpage_testcases():
            tc.setdefault('add_ie', []).append('Generic')
            yield tc


md5 = lambda s: hashlib.md5(s.encode()).hexdigest()


def expect_value(self, got, expected, field):
    if isinstance(expected, str) and expected.startswith('re:'):
        match_str = expected[len('re:'):]
        match_rex = re.compile(match_str)

        self.assertTrue(
            isinstance(got, str),
            f'Expected a {str.__name__} object, but got {type(got).__name__} for field {field}')
        self.assertTrue(
            match_rex.match(got),
            f'field {field} (value: {got!r}) should match {match_str!r}')
    elif isinstance(expected, str) and expected.startswith('startswith:'):
        start_str = expected[len('startswith:'):]
        self.assertTrue(
            isinstance(got, str),
            f'Expected a {str.__name__} object, but got {type(got).__name__} for field {field}')
        self.assertTrue(
            got.startswith(start_str),
            f'field {field} (value: {got!r}) should start with {start_str!r}')
    elif isinstance(expected, str) and expected.startswith('contains:'):
        contains_str = expected[len('contains:'):]
        self.assertTrue(
            isinstance(got, str),
            f'Expected a {str.__name__} object, but got {type(got).__name__} for field {field}')
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
            f'Expect a list of length {len(expected)}, but got a list of length {len(got)} for field {field}')
        for index, (item_got, item_expected) in enumerate(zip(got, expected)):
            type_got = type(item_got)
            type_expected = type(item_expected)
            self.assertEqual(
                type_expected, type_got,
                f'Type mismatch for list item at index {index} for field {field}, '
                f'expected {type_expected!r}, got {type_got!r}')
            expect_value(self, item_got, item_expected, field)
    else:
        if isinstance(expected, str) and expected.startswith('md5:'):
            self.assertTrue(
                isinstance(got, str),
                f'Expected field {field} to be a unicode object, but got value {got!r} of type {type(got)!r}')
            got = 'md5:' + md5(got)
        elif isinstance(expected, str) and re.match(r'^(?:min|max)?count:\d+', expected):
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
        'autonumber', 'playlist', 'format_index', 'video_ext', 'audio_ext', 'duration_string', 'epoch', 'n_entries',
        'fulltitle', 'extractor', 'extractor_key', 'filename', 'filepath', 'infojson_filename', 'original_url',

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
        if value is not None and key not in IGNORED_FIELDS and (
            not any(key.startswith(f'{prefix}_') for prefix in IGNORED_PREFIXES)
            or key == '_old_archive_ids')
    }

    # display_id may be generated from id
    if test_info_dict.get('display_id') == test_info_dict.get('id'):
        test_info_dict.pop('display_id')

    # Remove deprecated fields
    for old in YoutubeDL._deprecated_multivalue_fields:
        test_info_dict.pop(old, None)

    # release_year may be generated from release_date
    if try_call(lambda: test_info_dict['release_year'] == int(test_info_dict['release_date'][:4])):
        test_info_dict.pop('release_year')

    # Check url for flat entries
    if got_dict.get('_type', 'video') != 'video' and got_dict.get('url'):
        test_info_dict['url'] = got_dict['url']

    return test_info_dict


def expect_info_dict(self, got_dict, expected_dict):
    ALLOWED_KEYS_SORT_ORDER = (
        # NB: Keep in sync with the docstring of extractor/common.py
        'id', 'ext', 'direct', 'display_id', 'title', 'alt_title', 'description', 'media_type',
        'uploader', 'uploader_id', 'uploader_url', 'channel', 'channel_id', 'channel_url', 'channel_is_verified',
        'channel_follower_count', 'comment_count', 'view_count', 'concurrent_view_count',
        'like_count', 'dislike_count', 'repost_count', 'average_rating', 'age_limit', 'duration', 'thumbnail', 'heatmap',
        'chapters', 'chapter', 'chapter_number', 'chapter_id', 'start_time', 'end_time', 'section_start', 'section_end',
        'categories', 'tags', 'cast', 'composers', 'artists', 'album_artists', 'creators', 'genres',
        'track', 'track_number', 'track_id', 'album', 'album_type', 'disc_number',
        'series', 'series_id', 'season', 'season_number', 'season_id', 'episode', 'episode_number', 'episode_id',
        'timestamp', 'upload_date', 'release_timestamp', 'release_date', 'release_year', 'modified_timestamp', 'modified_date',
        'playable_in_embed', 'availability', 'live_status', 'location', 'license', '_old_archive_ids',
    )

    expect_dict(self, got_dict, expected_dict)
    # Check for the presence of mandatory fields
    if got_dict.get('_type') not in ('playlist', 'multi_video'):
        mandatory_fields = ['id', 'title']
        if expected_dict.get('ext'):
            mandatory_fields.extend(('url', 'ext'))
        for key in mandatory_fields:
            self.assertTrue(got_dict.get(key), f'Missing mandatory field {key}')
    # Check for mandatory fields that are automatically set by YoutubeDL
    if got_dict.get('_type', 'video') == 'video':
        for key in ['webpage_url', 'extractor', 'extractor_key']:
            self.assertTrue(got_dict.get(key), f'Missing field: {key}')

    test_info_dict = sanitize_got_info_dict(got_dict)

    # Check for invalid/misspelled field names being returned by the extractor
    invalid_keys = sorted(test_info_dict.keys() - ALLOWED_KEYS_SORT_ORDER)
    self.assertFalse(invalid_keys, f'Invalid fields returned by the extractor: {", ".join(invalid_keys)}')

    missing_keys = sorted(
        test_info_dict.keys() - expected_dict.keys(),
        key=lambda x: ALLOWED_KEYS_SORT_ORDER.index(x))
    if missing_keys:
        def _repr(v):
            if isinstance(v, str):
                return "'{}'".format(v.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n'))
            elif isinstance(v, type):
                return v.__name__
            else:
                return repr(v)
        info_dict_str = ''.join(
            f'    {_repr(k)}: {_repr(v)},\n'
            for k, v in test_info_dict.items() if k not in missing_keys)
        if info_dict_str:
            info_dict_str += '\n'
        info_dict_str += ''.join(
            f'    {_repr(k)}: {_repr(test_info_dict[k])},\n'
            for k in missing_keys)
        info_dict_str = '\n\'info_dict\': {\n' + info_dict_str + '},\n'
        write_string(info_dict_str.replace('\n', '\n        '), out=sys.stderr)
        self.assertFalse(
            missing_keys,
            'Missing keys in test definition: {}'.format(', '.join(sorted(missing_keys))))


def assertRegexpMatches(self, text, regexp, msg=None):
    if hasattr(self, 'assertRegexp'):
        return self.assertRegexp(text, regexp, msg)
    else:
        m = re.match(regexp, text)
        if not m:
            note = f'Regexp didn\'t match: {regexp!r} not found'
            if len(text) < 1000:
                note += f' in {text!r}'
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
    if got != expected:
        if msg is None:
            msg = f'{got!r} not equal to {expected!r}'
        self.assertTrue(got == expected, msg)


def expect_warnings(ydl, warnings_re):
    real_warning = ydl.report_warning

    def _report_warning(w, *args, **kwargs):
        if not any(re.search(w_re, w) for w_re in warnings_re):
            real_warning(w, *args, **kwargs)

    ydl.report_warning = _report_warning


def http_server_port(httpd):
    if os.name == 'java' and isinstance(httpd.socket, ssl.SSLSocket):
        # In Jython SSLSocket is not a subclass of socket.socket
        sock = httpd.socket.sock
    else:
        sock = httpd.socket
    return sock.getsockname()[1]


def verify_address_availability(address):
    if find_available_port(address) is None:
        pytest.skip(f'Unable to bind to source address {address} (address may not exist)')


def validate_and_send(rh, req):
    rh.validate(req)
    return rh.send(req)
