#!/usr/bin/env python3

# Allow direct execution
import os
import os.path
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import unittest.mock
from pathlib import Path

from yt_dlp.compat import compat_expanduser
from yt_dlp.options import create_parser, parseOpts
from yt_dlp.utils import Config, get_executable_path


def flatten(iterable):
    return list(item for items in iterable for item in items)


class TestCache(unittest.TestCase):
    def setUp(self):
        xdg_config_home = os.getenv('XDG_CONFIG_HOME') or compat_expanduser('~/.config')
        appdata_dir = os.getenv('appdata')
        home_dir = compat_expanduser('~')
        self.expected_groups = {
            "Portable": [
                Path(get_executable_path(), 'yt-dlp.conf'),
            ],
            "Home": [
                Path('yt-dlp.conf'),
            ],
            "User": [
                Path(xdg_config_home, 'yt-dlp.conf'),
                Path(xdg_config_home, 'yt-dlp', 'config'),
                Path(xdg_config_home, 'yt-dlp', 'config.txt'),
                *([
                    Path(appdata_dir, 'yt-dlp.conf'),
                    Path(appdata_dir, 'yt-dlp', 'config'),
                    Path(appdata_dir, 'yt-dlp', 'config.txt'),
                ] if appdata_dir else []),
                Path(home_dir, 'yt-dlp.conf'),
                Path(home_dir, 'yt-dlp.conf.txt'),
                Path(home_dir, '.yt-dlp', 'config'),
                Path(home_dir, '.yt-dlp', 'config.txt'),
            ],
            "System": [
                Path('/etc/yt-dlp.conf'),
                Path('/etc/yt-dlp/config'),
                Path('/etc/yt-dlp/config.txt'),
            ]
        }
        self.expected = flatten(self.expected_groups.values())
        sys.argv = ['yt-dlp']
        self.maxDiff = None

    def test_config_locations(self):
        files = []

        def read_file(filename, default=[]):
            files.append(Path(filename))

        with unittest.mock.patch('yt_dlp.options.Config') as mock:
            mock.return_value = Config(create_parser())
            mock.read_file = read_file

            parseOpts()
            self.assertEqual(files, self.expected,
                             'Not all expected locations have been checked')

    def _test_config_group(self, stop_index):
        files = []
        index = 0

        def read_file(filename, default=[]):
            nonlocal index
            index += 1

            filepath = Path(filename)
            files.append(filepath)
            if index == stop_index:
                return ['-o', filename]

        with unittest.mock.patch('yt_dlp.options.Config') as mock:
            mock.return_value = Config(create_parser())
            mock.read_file = read_file

            _, opts, _ = parseOpts()

        return files, opts

    def test_config_grouping(self):
        total_index = 0
        for name, group in self.expected_groups.items():
            for index, path in enumerate(group):
                total_index += 1
                with self.subTest(f'Config group {name}, index {index}'):
                    result, opts = self._test_config_group(total_index)
                    expected_groups = self.expected_groups.copy()
                    expected_groups[name] = expected_groups[name][:index + 1]

                    self.assertEqual(
                        result, flatten(expected_groups.values()),
                        'The remaining files in the group were not skipped')
                    self.assertEqual(
                        Path(opts.outtmpl['default']), path,
                        'The parsed result value was incorrect')


if __name__ == '__main__':
    unittest.main()
