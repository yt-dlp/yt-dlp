#!/usr/bin/env python3

# Allow direct execution
import os.path
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import unittest.mock
from pathlib import Path

from yt_dlp.options import create_parser, parseOpts
from yt_dlp.utils import Config


def flatten(iterable):
    return list(item for items in iterable for item in items)


class TestCache(unittest.TestCase):
    def setUp(self):
        self.expected_groups = [list(map(Path, items)) for items in [[
            'D:/Documents/GitHub/Grub4K/yt-dlp/yt-dlp.conf',
        ], [
            'yt-dlp.conf',
        ], [
            'C:/Users/grub4k/.config/yt-dlp.conf',
            'C:/Users/grub4k/.config/yt-dlp/config',
            'C:/Users/grub4k/.config/yt-dlp/config.txt',
            'C:/Users/grub4k/AppData/Roaming/yt-dlp.conf',
            'C:/Users/grub4k/AppData/Roaming/yt-dlp/config',
            'C:/Users/grub4k/AppData/Roaming/yt-dlp/config.txt',
            'C:/Users/grub4k/yt-dlp.conf',
            'C:/Users/grub4k/yt-dlp.conf.txt',
            'C:/Users/grub4k/.yt-dlp/config',
            'C:/Users/grub4k/.yt-dlp/config.txt',
        ], [
            '/etc/yt-dlp.conf',
            '/etc/yt-dlp/config',
            '/etc/yt-dlp/config.txt',
        ]]]
        self.expected = flatten(self.expected_groups)
        sys.argv = ['yt-dlp']

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

    def _test_config_group(self, stop_path):
        files = []

        def read_file(filename, default=[]):
            filepath = Path(filename)
            files.append(filepath)
            if filepath == stop_path:
                return ['-o', filename]

        with unittest.mock.patch('yt_dlp.options.Config') as mock:
            mock.return_value = Config(create_parser())
            mock.read_file = read_file

            _, opts, _ = parseOpts()

        return files, opts

    def test_config_grouping(self):
        for group_index, group in enumerate(self.expected_groups):
            for index, path in enumerate(group):
                with self.subTest(f'Config group {group_index}, index {index}'):
                    expected_groups = (
                        self.expected_groups[:group_index]
                        + [self.expected_groups[group_index][:index + 1]]
                        + self.expected_groups[group_index + 1:])

                    expected_result = flatten(expected_groups)
                    result, opts = self._test_config_group(path)
                    self.assertEqual(
                        result, expected_result,
                        'The remaining files in the group were not skipped')
                    self.assertEqual(
                        Path(opts.outtmpl['default']), path,
                        'The parsed result value was incorrect')


if __name__ == '__main__':
    unittest.main()
