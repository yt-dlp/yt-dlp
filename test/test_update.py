#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from test.helper import FakeYDL, report_warning
from yt_dlp.update import Updater, UpdateInfo

TEST_API_DATA = {
    'yt-dlp/yt-dlp/latest': {
        'tag_name': '2023.12.31',
        'target_commitish': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
        'name': 'yt-dlp 2023.12.31',
        'body': 'BODY',
    },
    'yt-dlp/yt-dlp-nightly-builds/latest': {
        'tag_name': '2023.12.31.123456',
        'target_commitish': 'master',
        'name': 'yt-dlp nightly 2023.12.31.123456',
        'body': 'Generated from: https://github.com/yt-dlp/yt-dlp/commit/cccccccccccccccccccccccccccccccccccccccc',
    },
    'yt-dlp/yt-dlp-master-builds/latest': {
        'tag_name': '2023.12.31.987654',
        'target_commitish': 'master',
        'name': 'yt-dlp master 2023.12.31.987654',
        'body': 'Generated from: https://github.com/yt-dlp/yt-dlp/commit/dddddddddddddddddddddddddddddddddddddddd',
    },
    'yt-dlp/yt-dlp/tags/testing': {
        'tag_name': 'testing',
        'target_commitish': '9999999999999999999999999999999999999999',
        'name': 'testing',
        'body': 'BODY',
    },
    'fork/yt-dlp/latest': {
        'tag_name': '2050.12.31',
        'target_commitish': 'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
        'name': '2050.12.31',
        'body': 'BODY',
    },
    'fork/yt-dlp/tags/pr0000': {
        'tag_name': 'pr0000',
        'target_commitish': 'ffffffffffffffffffffffffffffffffffffffff',
        'name': 'pr1234 2023.11.11.000000',
        'body': 'BODY',
    },
    'fork/yt-dlp/tags/pr1234': {
        'tag_name': 'pr1234',
        'target_commitish': '0000000000000000000000000000000000000000',
        'name': 'pr1234 2023.12.31.555555',
        'body': 'BODY',
    },
    'fork/yt-dlp/tags/pr9999': {
        'tag_name': 'pr9999',
        'target_commitish': '1111111111111111111111111111111111111111',
        'name': 'pr9999',
        'body': 'BODY',
    },
    'fork/yt-dlp-satellite/tags/pr987': {
        'tag_name': 'pr987',
        'target_commitish': 'master',
        'name': 'pr987',
        'body': 'Generated from: https://github.com/yt-dlp/yt-dlp/commit/2222222222222222222222222222222222222222',
    },
}

TEST_LOCKFILE_V1 = '''# This file is used for regulating self-update
lock 2022.08.18.36 .+ Python 3.6
lock 2023.11.13 .+ Python 3.7
'''

TEST_LOCKFILE_V2 = '''# This file is used for regulating self-update
lockV2 yt-dlp/yt-dlp 2022.08.18.36 .+ Python 3.6
lockV2 yt-dlp/yt-dlp 2023.11.13 .+ Python 3.7
'''

TEST_LOCKFILE_V1_V2 = '''# This file is used for regulating self-update
lock 2022.08.18.36 .+ Python 3.6
lock 2023.11.13 .+ Python 3.7
lockV2 yt-dlp/yt-dlp 2022.08.18.36 .+ Python 3.6
lockV2 yt-dlp/yt-dlp 2023.11.13 .+ Python 3.7
lockV2 fork/yt-dlp pr0000 .+ Python 3.6
lockV2 fork/yt-dlp pr1234 .+ Python 3.7
lockV2 fork/yt-dlp pr9999 .+ Python 3.11
'''


class FakeUpdater(Updater):
    current_version = '2022.01.01'
    current_commit = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'

    _channel = 'stable'
    _origin = 'yt-dlp/yt-dlp'

    def _download_update_spec(self, *args, **kwargs):
        return TEST_LOCKFILE_V1_V2

    def _call_api(self, tag):
        tag = f'tags/{tag}' if tag != 'latest' else tag
        return TEST_API_DATA[f'{self.requested_repo}/{tag}']

    def _report_error(self, msg, *args, **kwargs):
        report_warning(msg)


class TestUpdate(unittest.TestCase):
    maxDiff = None

    def test_update_spec(self):
        ydl = FakeYDL()
        updater = FakeUpdater(ydl, 'stable@latest')

        def test(lockfile, identifier, input_tag, expect_tag, exact=False, repo='yt-dlp/yt-dlp'):
            updater._identifier = identifier
            updater._exact = exact
            updater.requested_repo = repo
            result = updater._process_update_spec(lockfile, input_tag)
            self.assertEqual(
                result, expect_tag,
                f'{identifier!r} requesting {repo}@{input_tag} (exact={exact}) '
                f'returned {result!r} instead of {expect_tag!r}')

        test(TEST_LOCKFILE_V1, 'zip Python 3.11.0', '2023.11.13', '2023.11.13')
        test(TEST_LOCKFILE_V1, 'zip stable Python 3.11.0', '2023.11.13', '2023.11.13', exact=True)
        test(TEST_LOCKFILE_V1, 'zip Python 3.6.0', '2023.11.13', '2022.08.18.36')
        test(TEST_LOCKFILE_V1, 'zip stable Python 3.6.0', '2023.11.13', None, exact=True)
        test(TEST_LOCKFILE_V1, 'zip Python 3.7.0', '2023.11.13', '2023.11.13')
        test(TEST_LOCKFILE_V1, 'zip stable Python 3.7.1', '2023.11.13', '2023.11.13')
        test(TEST_LOCKFILE_V1, 'zip Python 3.7.1', '2023.12.31', '2023.11.13')
        test(TEST_LOCKFILE_V1, 'zip stable Python 3.7.1', '2023.12.31', '2023.11.13')

        test(TEST_LOCKFILE_V2, 'zip Python 3.11.1', '2023.11.13', '2023.11.13')
        test(TEST_LOCKFILE_V2, 'zip stable Python 3.11.1', '2023.12.31', '2023.12.31')
        test(TEST_LOCKFILE_V2, 'zip Python 3.6.1', '2023.11.13', '2022.08.18.36')
        test(TEST_LOCKFILE_V2, 'zip stable Python 3.7.2', '2023.11.13', '2023.11.13')
        test(TEST_LOCKFILE_V2, 'zip Python 3.7.2', '2023.12.31', '2023.11.13')

        test(TEST_LOCKFILE_V1_V2, 'zip Python 3.11.2', '2023.11.13', '2023.11.13')
        test(TEST_LOCKFILE_V1_V2, 'zip stable Python 3.11.2', '2023.12.31', '2023.12.31')
        test(TEST_LOCKFILE_V1_V2, 'zip Python 3.6.2', '2023.11.13', '2022.08.18.36')
        test(TEST_LOCKFILE_V1_V2, 'zip stable Python 3.7.3', '2023.11.13', '2023.11.13')
        test(TEST_LOCKFILE_V1_V2, 'zip Python 3.7.3', '2023.12.31', '2023.11.13')
        test(TEST_LOCKFILE_V1_V2, 'zip Python 3.6.3', 'pr0000', None, repo='fork/yt-dlp')
        test(TEST_LOCKFILE_V1_V2, 'zip stable Python 3.7.4', 'pr0000', 'pr0000', repo='fork/yt-dlp')
        test(TEST_LOCKFILE_V1_V2, 'zip Python 3.6.4', 'pr0000', None, repo='fork/yt-dlp')
        test(TEST_LOCKFILE_V1_V2, 'zip Python 3.7.4', 'pr1234', None, repo='fork/yt-dlp')
        test(TEST_LOCKFILE_V1_V2, 'zip stable Python 3.8.1', 'pr1234', 'pr1234', repo='fork/yt-dlp')
        test(TEST_LOCKFILE_V1_V2, 'zip Python 3.7.5', 'pr1234', None, repo='fork/yt-dlp')
        test(TEST_LOCKFILE_V1_V2, 'zip Python 3.11.3', 'pr9999', None, repo='fork/yt-dlp')
        test(TEST_LOCKFILE_V1_V2, 'zip stable Python 3.12.0', 'pr9999', 'pr9999', repo='fork/yt-dlp')
        test(TEST_LOCKFILE_V1_V2, 'zip Python 3.11.4', 'pr9999', None, repo='fork/yt-dlp')

    def test_query_update(self):
        ydl = FakeYDL()

        def test(target, expected, current_version=None, current_commit=None, identifier=None):
            updater = FakeUpdater(ydl, target)
            if current_version:
                updater.current_version = current_version
            if current_commit:
                updater.current_commit = current_commit
            updater._identifier = identifier or 'zip'
            update_info = updater.query_update(_output=True)
            self.assertDictEqual(
                update_info.__dict__ if update_info else {}, expected.__dict__ if expected else {})

        test('yt-dlp/yt-dlp@latest', UpdateInfo(
            '2023.12.31', version='2023.12.31', requested_version='2023.12.31', commit='b' * 40))
        test('yt-dlp/yt-dlp-nightly-builds@latest', UpdateInfo(
            '2023.12.31.123456', version='2023.12.31.123456', requested_version='2023.12.31.123456', commit='c' * 40))
        test('yt-dlp/yt-dlp-master-builds@latest', UpdateInfo(
            '2023.12.31.987654', version='2023.12.31.987654', requested_version='2023.12.31.987654', commit='d' * 40))
        test('fork/yt-dlp@latest', UpdateInfo(
            '2050.12.31', version='2050.12.31', requested_version='2050.12.31', commit='e' * 40))
        test('fork/yt-dlp@pr0000', UpdateInfo(
            'pr0000', version='2023.11.11.000000', requested_version='2023.11.11.000000', commit='f' * 40))
        test('fork/yt-dlp@pr1234', UpdateInfo(
            'pr1234', version='2023.12.31.555555', requested_version='2023.12.31.555555', commit='0' * 40))
        test('fork/yt-dlp@pr9999', UpdateInfo(
            'pr9999', version=None, requested_version=None, commit='1' * 40))
        test('fork/yt-dlp-satellite@pr987', UpdateInfo(
            'pr987', version=None, requested_version=None, commit='2' * 40))
        test('yt-dlp/yt-dlp', None, current_version='2024.01.01')
        test('stable', UpdateInfo(
            '2023.12.31', version='2023.12.31', requested_version='2023.12.31', commit='b' * 40))
        test('nightly', UpdateInfo(
            '2023.12.31.123456', version='2023.12.31.123456', requested_version='2023.12.31.123456', commit='c' * 40))
        test('master', UpdateInfo(
            '2023.12.31.987654', version='2023.12.31.987654', requested_version='2023.12.31.987654', commit='d' * 40))
        test('testing', None, current_commit='9' * 40)
        test('testing', UpdateInfo('testing', commit='9' * 40))


if __name__ == '__main__':
    unittest.main()
