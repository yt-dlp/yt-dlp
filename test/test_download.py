#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import collections
import hashlib
import json

from test.helper import (
    assertGreaterEqual,
    expect_info_dict,
    expect_warnings,
    get_params,
    gettestcases,
    getwebpagetestcases,
    is_download_test,
    report_warning,
    try_rm,
)

import yt_dlp.YoutubeDL  # isort: split
from yt_dlp.extractor import get_info_extractor
from yt_dlp.networking.exceptions import HTTPError, TransportError
from yt_dlp.utils import (
    DownloadError,
    ExtractorError,
    UnavailableVideoError,
    YoutubeDLError,
    format_bytes,
    join_nonempty,
)

RETRIES = 3


class YoutubeDL(yt_dlp.YoutubeDL):
    def __init__(self, *args, **kwargs):
        self.to_stderr = self.to_screen
        self.processed_info_dicts = []
        super().__init__(*args, **kwargs)

    def report_warning(self, message, *args, **kwargs):
        # Don't accept warnings during tests
        raise ExtractorError(message)

    def process_info(self, info_dict):
        self.processed_info_dicts.append(info_dict.copy())
        return super().process_info(info_dict)


def _file_md5(fn):
    with open(fn, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


normal_test_cases = gettestcases()
webpage_test_cases = getwebpagetestcases()
tests_counter = collections.defaultdict(collections.Counter)


@is_download_test
class TestDownload(unittest.TestCase):
    # Parallel testing in nosetests. See
    # http://nose.readthedocs.org/en/latest/doc_tests/test_multiprocess/multiprocess.html
    _multiprocess_shared_ = True

    maxDiff = None

    COMPLETED_TESTS = {}

    def __str__(self):
        """Identify each test with the `add_ie` attribute, if available."""
        cls, add_ie = type(self), getattr(self, self._testMethodName).add_ie
        return f'{self._testMethodName} ({cls.__module__}.{cls.__name__}){f" [{add_ie}]" if add_ie else ""}:'


# Dynamically generate tests

def generator(test_case, tname):
    def test_template(self):
        if self.COMPLETED_TESTS.get(tname):
            return
        self.COMPLETED_TESTS[tname] = True
        ie = yt_dlp.extractor.get_info_extractor(test_case['name'])()
        other_ies = [get_info_extractor(ie_key)() for ie_key in test_case.get('add_ie', [])]
        is_playlist = any(k.startswith('playlist') for k in test_case)
        test_cases = test_case.get(
            'playlist', [] if is_playlist else [test_case])

        def print_skipping(reason):
            print('Skipping {}: {}'.format(test_case['name'], reason))
            self.skipTest(reason)

        if not ie.working():
            print_skipping('IE marked as not _WORKING')

        for tc in test_cases:
            if tc.get('expected_exception'):
                continue
            info_dict = tc.get('info_dict', {})
            params = tc.get('params', {})
            if not info_dict.get('id'):
                raise Exception(f'Test {tname} definition incorrect - "id" key is not present')
            elif not info_dict.get('ext') and info_dict.get('_type', 'video') == 'video':
                if params.get('skip_download') and params.get('ignore_no_formats_error'):
                    continue
                raise Exception(f'Test {tname} definition incorrect - "ext" key must be present to define the output file')

        if 'skip' in test_case:
            print_skipping(test_case['skip'])

        for other_ie in other_ies:
            if not other_ie.working():
                print_skipping(f'test depends on {other_ie.ie_key()}IE, marked as not WORKING')

        params = get_params(test_case.get('params', {}))
        params['outtmpl'] = tname + '_' + params['outtmpl']
        if is_playlist and 'playlist' not in test_case:
            params.setdefault('extract_flat', 'in_playlist')
            params.setdefault('playlistend', test_case.get(
                'playlist_mincount', test_case.get('playlist_count', -2) + 1))
            params.setdefault('skip_download', True)

        ydl = YoutubeDL(params, auto_init=False)
        ydl.add_default_info_extractors()
        finished_hook_called = set()

        def _hook(status):
            if status['status'] == 'finished':
                finished_hook_called.add(status['filename'])
        ydl.add_progress_hook(_hook)
        expect_warnings(ydl, test_case.get('expected_warnings', []))

        def get_tc_filename(tc):
            return ydl.prepare_filename(dict(tc.get('info_dict', {})))

        res_dict = None

        def match_exception(err):
            expected_exception = test_case.get('expected_exception')
            if not expected_exception:
                return False
            if err.__class__.__name__ == expected_exception:
                return True
            return any(exc.__class__.__name__ == expected_exception for exc in err.exc_info)

        def try_rm_tcs_files(tcs=None):
            if tcs is None:
                tcs = test_cases
            for tc in tcs:
                tc_filename = get_tc_filename(tc)
                try_rm(tc_filename)
                try_rm(tc_filename + '.part')
                try_rm(os.path.splitext(tc_filename)[0] + '.info.json')
        try_rm_tcs_files()
        try:
            try_num = 1
            while True:
                try:
                    # We're not using .download here since that is just a shim
                    # for outside error handling, and returns the exit code
                    # instead of the result dict.
                    res_dict = ydl.extract_info(
                        test_case['url'],
                        force_generic_extractor=params.get('force_generic_extractor', False))
                except (DownloadError, ExtractorError) as err:
                    # Check if the exception is not a network related one
                    if not isinstance(err.exc_info[1], (TransportError, UnavailableVideoError)) or (isinstance(err.exc_info[1], HTTPError) and err.exc_info[1].status == 503):
                        if match_exception(err):
                            return
                        err.msg = f'{getattr(err, "msg", err)} ({tname})'
                        raise

                    if try_num == RETRIES:
                        report_warning(f'{tname} failed due to network errors, skipping...')
                        return

                    print(f'Retrying: {try_num} failed tries\n\n##########\n\n')

                    try_num += 1
                except YoutubeDLError as err:
                    if match_exception(err):
                        return
                    raise
                else:
                    break

            if is_playlist:
                self.assertTrue(res_dict['_type'] in ['playlist', 'multi_video'])
                self.assertTrue('entries' in res_dict)
                expect_info_dict(self, res_dict, test_case.get('info_dict', {}))

            if 'playlist_mincount' in test_case:
                assertGreaterEqual(
                    self,
                    len(res_dict['entries']),
                    test_case['playlist_mincount'],
                    'Expected at least %d in playlist %s, but got only %d' % (
                        test_case['playlist_mincount'], test_case['url'],
                        len(res_dict['entries'])))
            if 'playlist_count' in test_case:
                self.assertEqual(
                    len(res_dict['entries']),
                    test_case['playlist_count'],
                    'Expected %d entries in playlist %s, but got %d.' % (
                        test_case['playlist_count'],
                        test_case['url'],
                        len(res_dict['entries']),
                    ))
            if 'playlist_duration_sum' in test_case:
                got_duration = sum(e['duration'] for e in res_dict['entries'])
                self.assertEqual(
                    test_case['playlist_duration_sum'], got_duration)

            # Generalize both playlists and single videos to unified format for
            # simplicity
            if 'entries' not in res_dict:
                res_dict['entries'] = [res_dict]

            for tc_num, tc in enumerate(test_cases):
                tc_res_dict = res_dict['entries'][tc_num]
                # First, check test cases' data against extracted data alone
                expect_info_dict(self, tc_res_dict, tc.get('info_dict', {}))
                if tc_res_dict.get('_type', 'video') != 'video':
                    continue
                # Now, check downloaded file consistency
                tc_filename = get_tc_filename(tc)
                if not test_case.get('params', {}).get('skip_download', False):
                    self.assertTrue(os.path.exists(tc_filename), msg='Missing file ' + tc_filename)
                    self.assertTrue(tc_filename in finished_hook_called)
                    expected_minsize = tc.get('file_minsize', 10000)
                    if expected_minsize is not None:
                        if params.get('test'):
                            expected_minsize = max(expected_minsize, 10000)
                        got_fsize = os.path.getsize(tc_filename)
                        assertGreaterEqual(
                            self, got_fsize, expected_minsize,
                            f'Expected {tc_filename} to be at least {format_bytes(expected_minsize)}, '
                            f'but it\'s only {format_bytes(got_fsize)} ')
                    if 'md5' in tc:
                        md5_for_file = _file_md5(tc_filename)
                        self.assertEqual(tc['md5'], md5_for_file)
                # Finally, check test cases' data again but this time against
                # extracted data from info JSON file written during processing
                info_json_fn = os.path.splitext(tc_filename)[0] + '.info.json'
                self.assertTrue(
                    os.path.exists(info_json_fn),
                    f'Missing info file {info_json_fn}')
                with open(info_json_fn, encoding='utf-8') as infof:
                    info_dict = json.load(infof)
                expect_info_dict(self, info_dict, tc.get('info_dict', {}))
        finally:
            try_rm_tcs_files()
            if is_playlist and res_dict is not None and res_dict.get('entries'):
                # Remove all other files that may have been extracted if the
                # extractor returns full results even with extract_flat
                res_tcs = [{'info_dict': e} for e in res_dict['entries']]
                try_rm_tcs_files(res_tcs)
            ydl.close()
    return test_template


# And add them to TestDownload
def inject_tests(test_cases, label=''):
    for test_case in test_cases:
        name = test_case['name']
        tname = join_nonempty('test', name, label, tests_counter[name][label], delim='_')
        tests_counter[name][label] += 1

        test_method = generator(test_case, tname)
        test_method.__name__ = tname
        test_method.add_ie = ','.join(test_case.get('add_ie', []))
        setattr(TestDownload, test_method.__name__, test_method)


inject_tests(normal_test_cases)

# TODO: disable redirection to the IE to ensure we are actually testing the webpage extraction
inject_tests(webpage_test_cases, 'webpage')


def batch_generator(name):
    def test_template(self):
        for label, num_tests in tests_counter[name].items():
            for i in range(num_tests):
                test_name = join_nonempty('test', name, label, i, delim='_')
                try:
                    getattr(self, test_name)()
                except unittest.SkipTest:
                    print(f'Skipped {test_name}')

    return test_template


for name in tests_counter:
    test_method = batch_generator(name)
    test_method.__name__ = f'test_{name}_all'
    test_method.add_ie = ''
    setattr(TestDownload, test_method.__name__, test_method)
del test_method


if __name__ == '__main__':
    unittest.main()
