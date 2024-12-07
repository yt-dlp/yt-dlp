#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import contextlib
import copy
import json

from test.helper import FakeYDL, assertRegexpMatches, try_rm
from yt_dlp import YoutubeDL
from yt_dlp.extractor import YoutubeIE
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.postprocessor.common import PostProcessor
from yt_dlp.utils import (
    ExtractorError,
    LazyList,
    OnDemandPagedList,
    int_or_none,
    match_filter_func,
)
from yt_dlp.utils.traversal import traverse_obj

TEST_URL = 'http://localhost/sample.mp4'


class YDL(FakeYDL):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.downloaded_info_dicts = []
        self.msgs = []

    def process_info(self, info_dict):
        self.downloaded_info_dicts.append(info_dict.copy())

    def to_screen(self, msg, *args, **kwargs):
        self.msgs.append(msg)

    def dl(self, *args, **kwargs):
        assert False, 'Downloader must not be invoked for test_YoutubeDL'


def _make_result(formats, **kwargs):
    res = {
        'formats': formats,
        'id': 'testid',
        'title': 'testttitle',
        'extractor': 'testex',
        'extractor_key': 'TestEx',
        'webpage_url': 'http://example.com/watch?v=shenanigans',
    }
    res.update(**kwargs)
    return res


class TestFormatSelection(unittest.TestCase):
    def test_prefer_free_formats(self):
        # Same resolution => download webm
        ydl = YDL()
        ydl.params['prefer_free_formats'] = True
        formats = [
            {'ext': 'webm', 'height': 460, 'url': TEST_URL},
            {'ext': 'mp4', 'height': 460, 'url': TEST_URL},
        ]
        info_dict = _make_result(formats)
        ydl.sort_formats(info_dict)
        ydl.process_ie_result(info_dict)
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['ext'], 'webm')

        # Different resolution => download best quality (mp4)
        ydl = YDL()
        ydl.params['prefer_free_formats'] = True
        formats = [
            {'ext': 'webm', 'height': 720, 'url': TEST_URL},
            {'ext': 'mp4', 'height': 1080, 'url': TEST_URL},
        ]
        info_dict['formats'] = formats
        ydl.sort_formats(info_dict)
        ydl.process_ie_result(info_dict)
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['ext'], 'mp4')

        # No prefer_free_formats => prefer mp4 and webm
        ydl = YDL()
        ydl.params['prefer_free_formats'] = False
        formats = [
            {'ext': 'webm', 'height': 720, 'url': TEST_URL},
            {'ext': 'mp4', 'height': 720, 'url': TEST_URL},
            {'ext': 'flv', 'height': 720, 'url': TEST_URL},
        ]
        info_dict['formats'] = formats
        ydl.sort_formats(info_dict)
        ydl.process_ie_result(info_dict)
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['ext'], 'mp4')

        ydl = YDL()
        ydl.params['prefer_free_formats'] = False
        formats = [
            {'ext': 'flv', 'height': 720, 'url': TEST_URL},
            {'ext': 'webm', 'height': 720, 'url': TEST_URL},
        ]
        info_dict['formats'] = formats
        ydl.sort_formats(info_dict)
        ydl.process_ie_result(info_dict)
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['ext'], 'webm')

    def test_format_selection(self):
        formats = [
            {'format_id': '35', 'ext': 'mp4', 'preference': 0, 'url': TEST_URL},
            {'format_id': 'example-with-dashes', 'ext': 'webm', 'preference': 1, 'url': TEST_URL},
            {'format_id': '45', 'ext': 'webm', 'preference': 2, 'url': TEST_URL},
            {'format_id': '47', 'ext': 'webm', 'preference': 3, 'url': TEST_URL},
            {'format_id': '2', 'ext': 'flv', 'preference': 4, 'url': TEST_URL},
        ]
        info_dict = _make_result(formats)

        def test(inp, *expected, multi=False):
            ydl = YDL({
                'format': inp,
                'allow_multiple_video_streams': multi,
                'allow_multiple_audio_streams': multi,
            })
            ydl.process_ie_result(info_dict.copy())
            downloaded = [x['format_id'] for x in ydl.downloaded_info_dicts]
            self.assertEqual(downloaded, list(expected))

        test('20/47', '47')
        test('20/71/worst', '35')
        test(None, '2')
        test('webm/mp4', '47')
        test('3gp/40/mp4', '35')
        test('example-with-dashes', 'example-with-dashes')
        test('all', '2', '47', '45', 'example-with-dashes', '35')
        test('mergeall', '2+47+45+example-with-dashes+35', multi=True)
        # See: https://github.com/yt-dlp/yt-dlp/pulls/8797
        test('7_a/worst', '35')

    def test_format_selection_audio(self):
        formats = [
            {'format_id': 'audio-low', 'ext': 'webm', 'preference': 1, 'vcodec': 'none', 'url': TEST_URL},
            {'format_id': 'audio-mid', 'ext': 'webm', 'preference': 2, 'vcodec': 'none', 'url': TEST_URL},
            {'format_id': 'audio-high', 'ext': 'flv', 'preference': 3, 'vcodec': 'none', 'url': TEST_URL},
            {'format_id': 'vid', 'ext': 'mp4', 'preference': 4, 'url': TEST_URL},
        ]
        info_dict = _make_result(formats)

        ydl = YDL({'format': 'bestaudio'})
        ydl.process_ie_result(info_dict.copy())
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'audio-high')

        ydl = YDL({'format': 'worstaudio'})
        ydl.process_ie_result(info_dict.copy())
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'audio-low')

        formats = [
            {'format_id': 'vid-low', 'ext': 'mp4', 'preference': 1, 'url': TEST_URL},
            {'format_id': 'vid-high', 'ext': 'mp4', 'preference': 2, 'url': TEST_URL},
        ]
        info_dict = _make_result(formats)

        ydl = YDL({'format': 'bestaudio/worstaudio/best'})
        ydl.process_ie_result(info_dict.copy())
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'vid-high')

    def test_format_selection_audio_exts(self):
        formats = [
            {'format_id': 'mp3-64', 'ext': 'mp3', 'abr': 64, 'url': 'http://_', 'vcodec': 'none'},
            {'format_id': 'ogg-64', 'ext': 'ogg', 'abr': 64, 'url': 'http://_', 'vcodec': 'none'},
            {'format_id': 'aac-64', 'ext': 'aac', 'abr': 64, 'url': 'http://_', 'vcodec': 'none'},
            {'format_id': 'mp3-32', 'ext': 'mp3', 'abr': 32, 'url': 'http://_', 'vcodec': 'none'},
            {'format_id': 'aac-32', 'ext': 'aac', 'abr': 32, 'url': 'http://_', 'vcodec': 'none'},
        ]

        info_dict = _make_result(formats)
        ydl = YDL({'format': 'best', 'format_sort': ['abr', 'ext']})
        ydl.sort_formats(info_dict)
        ydl.process_ie_result(copy.deepcopy(info_dict))
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'aac-64')

        ydl = YDL({'format': 'mp3'})
        ydl.sort_formats(info_dict)
        ydl.process_ie_result(copy.deepcopy(info_dict))
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'mp3-64')

        ydl = YDL({'prefer_free_formats': True, 'format_sort': ['abr', 'ext']})
        ydl.sort_formats(info_dict)
        ydl.process_ie_result(copy.deepcopy(info_dict))
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'ogg-64')

    def test_format_selection_video(self):
        formats = [
            {'format_id': 'dash-video-low', 'ext': 'mp4', 'preference': 1, 'acodec': 'none', 'url': TEST_URL},
            {'format_id': 'dash-video-high', 'ext': 'mp4', 'preference': 2, 'acodec': 'none', 'url': TEST_URL},
            {'format_id': 'vid', 'ext': 'mp4', 'preference': 3, 'url': TEST_URL},
        ]
        info_dict = _make_result(formats)

        ydl = YDL({'format': 'bestvideo'})
        ydl.process_ie_result(info_dict.copy())
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'dash-video-high')

        ydl = YDL({'format': 'worstvideo'})
        ydl.process_ie_result(info_dict.copy())
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'dash-video-low')

        ydl = YDL({'format': 'bestvideo[format_id^=dash][format_id$=low]'})
        ydl.process_ie_result(info_dict.copy())
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'dash-video-low')

        formats = [
            {'format_id': 'vid-vcodec-dot', 'ext': 'mp4', 'preference': 1, 'vcodec': 'avc1.123456', 'acodec': 'none', 'url': TEST_URL},
        ]
        info_dict = _make_result(formats)

        ydl = YDL({'format': 'bestvideo[vcodec=avc1.123456]'})
        ydl.process_ie_result(info_dict.copy())
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'vid-vcodec-dot')

    def test_format_selection_by_vcodec_sort(self):
        formats = [
            {'format_id': 'av1-format', 'ext': 'mp4', 'vcodec': 'av1', 'acodec': 'none', 'url': TEST_URL},
            {'format_id': 'vp9-hdr-format', 'ext': 'mp4', 'vcodec': 'vp09.02.50.10.01.09.18.09.00', 'acodec': 'none', 'url': TEST_URL},
            {'format_id': 'vp9-sdr-format', 'ext': 'mp4', 'vcodec': 'vp09.00.50.08', 'acodec': 'none', 'url': TEST_URL},
            {'format_id': 'h265-format', 'ext': 'mp4', 'vcodec': 'h265', 'acodec': 'none', 'url': TEST_URL},
        ]
        info_dict = _make_result(formats)

        ydl = YDL({'format': 'bestvideo', 'format_sort': ['vcodec:vp9.2']})
        ydl.process_ie_result(info_dict.copy())
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'vp9-hdr-format')

        ydl = YDL({'format': 'bestvideo', 'format_sort': ['vcodec:vp9']})
        ydl.process_ie_result(info_dict.copy())
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'vp9-sdr-format')

        ydl = YDL({'format': 'bestvideo', 'format_sort': ['+vcodec:vp9.2']})
        ydl.process_ie_result(info_dict.copy())
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'vp9-hdr-format')

        ydl = YDL({'format': 'bestvideo', 'format_sort': ['+vcodec:vp9']})
        ydl.process_ie_result(info_dict.copy())
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'vp9-sdr-format')

    def test_format_selection_string_ops(self):
        formats = [
            {'format_id': 'abc-cba', 'ext': 'mp4', 'url': TEST_URL},
            {'format_id': 'zxc-cxz', 'ext': 'webm', 'url': TEST_URL},
        ]
        info_dict = _make_result(formats)

        # equals (=)
        ydl = YDL({'format': '[format_id=abc-cba]'})
        ydl.process_ie_result(info_dict.copy())
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'abc-cba')

        # does not equal (!=)
        ydl = YDL({'format': '[format_id!=abc-cba]'})
        ydl.process_ie_result(info_dict.copy())
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'zxc-cxz')

        ydl = YDL({'format': '[format_id!=abc-cba][format_id!=zxc-cxz]'})
        self.assertRaises(ExtractorError, ydl.process_ie_result, info_dict.copy())

        # starts with (^=)
        ydl = YDL({'format': '[format_id^=abc]'})
        ydl.process_ie_result(info_dict.copy())
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'abc-cba')

        # does not start with (!^=)
        ydl = YDL({'format': '[format_id!^=abc]'})
        ydl.process_ie_result(info_dict.copy())
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'zxc-cxz')

        ydl = YDL({'format': '[format_id!^=abc][format_id!^=zxc]'})
        self.assertRaises(ExtractorError, ydl.process_ie_result, info_dict.copy())

        # ends with ($=)
        ydl = YDL({'format': '[format_id$=cba]'})
        ydl.process_ie_result(info_dict.copy())
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'abc-cba')

        # does not end with (!$=)
        ydl = YDL({'format': '[format_id!$=cba]'})
        ydl.process_ie_result(info_dict.copy())
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'zxc-cxz')

        ydl = YDL({'format': '[format_id!$=cba][format_id!$=cxz]'})
        self.assertRaises(ExtractorError, ydl.process_ie_result, info_dict.copy())

        # contains (*=)
        ydl = YDL({'format': '[format_id*=bc-cb]'})
        ydl.process_ie_result(info_dict.copy())
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'abc-cba')

        # does not contain (!*=)
        ydl = YDL({'format': '[format_id!*=bc-cb]'})
        ydl.process_ie_result(info_dict.copy())
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'zxc-cxz')

        ydl = YDL({'format': '[format_id!*=abc][format_id!*=zxc]'})
        self.assertRaises(ExtractorError, ydl.process_ie_result, info_dict.copy())

        ydl = YDL({'format': '[format_id!*=-]'})
        self.assertRaises(ExtractorError, ydl.process_ie_result, info_dict.copy())

    def test_youtube_format_selection(self):
        # FIXME: Rewrite in accordance with the new format sorting options
        return

        order = [
            '38', '37', '46', '22', '45', '35', '44', '18', '34', '43', '6', '5', '17', '36', '13',
            # Apple HTTP Live Streaming
            '96', '95', '94', '93', '92', '132', '151',
            # 3D
            '85', '84', '102', '83', '101', '82', '100',
            # Dash video
            '137', '248', '136', '247', '135', '246',
            '245', '244', '134', '243', '133', '242', '160',
            # Dash audio
            '141', '172', '140', '171', '139',
        ]

        def format_info(f_id):
            info = YoutubeIE._formats[f_id].copy()

            # XXX: In real cases InfoExtractor._parse_mpd_formats() fills up 'acodec'
            # and 'vcodec', while in tests such information is incomplete since
            # commit a6c2c24479e5f4827ceb06f64d855329c0a6f593
            # test_YoutubeDL.test_youtube_format_selection is broken without
            # this fix
            if 'acodec' in info and 'vcodec' not in info:
                info['vcodec'] = 'none'
            elif 'vcodec' in info and 'acodec' not in info:
                info['acodec'] = 'none'

            info['format_id'] = f_id
            info['url'] = 'url:' + f_id
            return info
        formats_order = [format_info(f_id) for f_id in order]

        info_dict = _make_result(list(formats_order), extractor='youtube')
        ydl = YDL({'format': 'bestvideo+bestaudio'})
        ydl.sort_formats(info_dict)
        ydl.process_ie_result(info_dict)
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], '248+172')
        self.assertEqual(downloaded['ext'], 'mp4')

        info_dict = _make_result(list(formats_order), extractor='youtube')
        ydl = YDL({'format': 'bestvideo[height>=999999]+bestaudio/best'})
        ydl.sort_formats(info_dict)
        ydl.process_ie_result(info_dict)
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], '38')

        info_dict = _make_result(list(formats_order), extractor='youtube')
        ydl = YDL({'format': 'bestvideo/best,bestaudio'})
        ydl.sort_formats(info_dict)
        ydl.process_ie_result(info_dict)
        downloaded_ids = [info['format_id'] for info in ydl.downloaded_info_dicts]
        self.assertEqual(downloaded_ids, ['137', '141'])

        info_dict = _make_result(list(formats_order), extractor='youtube')
        ydl = YDL({'format': '(bestvideo[ext=mp4],bestvideo[ext=webm])+bestaudio'})
        ydl.sort_formats(info_dict)
        ydl.process_ie_result(info_dict)
        downloaded_ids = [info['format_id'] for info in ydl.downloaded_info_dicts]
        self.assertEqual(downloaded_ids, ['137+141', '248+141'])

        info_dict = _make_result(list(formats_order), extractor='youtube')
        ydl = YDL({'format': '(bestvideo[ext=mp4],bestvideo[ext=webm])[height<=720]+bestaudio'})
        ydl.sort_formats(info_dict)
        ydl.process_ie_result(info_dict)
        downloaded_ids = [info['format_id'] for info in ydl.downloaded_info_dicts]
        self.assertEqual(downloaded_ids, ['136+141', '247+141'])

        info_dict = _make_result(list(formats_order), extractor='youtube')
        ydl = YDL({'format': '(bestvideo[ext=none]/bestvideo[ext=webm])+bestaudio'})
        ydl.sort_formats(info_dict)
        ydl.process_ie_result(info_dict)
        downloaded_ids = [info['format_id'] for info in ydl.downloaded_info_dicts]
        self.assertEqual(downloaded_ids, ['248+141'])

        for f1, f2 in zip(formats_order, formats_order[1:]):
            info_dict = _make_result([f1, f2], extractor='youtube')
            ydl = YDL({'format': 'best/bestvideo'})
            ydl.sort_formats(info_dict)
            ydl.process_ie_result(info_dict)
            downloaded = ydl.downloaded_info_dicts[0]
            self.assertEqual(downloaded['format_id'], f1['format_id'])

            info_dict = _make_result([f2, f1], extractor='youtube')
            ydl = YDL({'format': 'best/bestvideo'})
            ydl.sort_formats(info_dict)
            ydl.process_ie_result(info_dict)
            downloaded = ydl.downloaded_info_dicts[0]
            self.assertEqual(downloaded['format_id'], f1['format_id'])

    def test_audio_only_extractor_format_selection(self):
        # For extractors with incomplete formats (all formats are audio-only or
        # video-only) best and worst should fallback to corresponding best/worst
        # video-only or audio-only formats (as per
        # https://github.com/ytdl-org/youtube-dl/pull/5556)
        formats = [
            {'format_id': 'low', 'ext': 'mp3', 'preference': 1, 'vcodec': 'none', 'url': TEST_URL},
            {'format_id': 'high', 'ext': 'mp3', 'preference': 2, 'vcodec': 'none', 'url': TEST_URL},
        ]
        info_dict = _make_result(formats)

        ydl = YDL({'format': 'best'})
        ydl.process_ie_result(info_dict.copy())
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'high')

        ydl = YDL({'format': 'worst'})
        ydl.process_ie_result(info_dict.copy())
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'low')

    def test_format_not_available(self):
        formats = [
            {'format_id': 'regular', 'ext': 'mp4', 'height': 360, 'url': TEST_URL},
            {'format_id': 'video', 'ext': 'mp4', 'height': 720, 'acodec': 'none', 'url': TEST_URL},
        ]
        info_dict = _make_result(formats)

        # This must fail since complete video-audio format does not match filter
        # and extractor does not provide incomplete only formats (i.e. only
        # video-only or audio-only).
        ydl = YDL({'format': 'best[height>360]'})
        self.assertRaises(ExtractorError, ydl.process_ie_result, info_dict.copy())

    def test_format_selection_issue_10083(self):
        # See https://github.com/ytdl-org/youtube-dl/issues/10083
        formats = [
            {'format_id': 'regular', 'height': 360, 'url': TEST_URL},
            {'format_id': 'video', 'height': 720, 'acodec': 'none', 'url': TEST_URL},
            {'format_id': 'audio', 'vcodec': 'none', 'url': TEST_URL},
        ]
        info_dict = _make_result(formats)

        ydl = YDL({'format': 'best[height>360]/bestvideo[height>360]+bestaudio'})
        ydl.process_ie_result(info_dict.copy())
        self.assertEqual(ydl.downloaded_info_dicts[0]['format_id'], 'video+audio')

    def test_invalid_format_specs(self):
        def assert_syntax_error(format_spec):
            self.assertRaises(SyntaxError, YDL, {'format': format_spec})

        assert_syntax_error('bestvideo,,best')
        assert_syntax_error('+bestaudio')
        assert_syntax_error('bestvideo+')
        assert_syntax_error('/')
        assert_syntax_error('[720<height]')

    def test_format_filtering(self):
        formats = [
            {'format_id': 'A', 'filesize': 500, 'width': 1000},
            {'format_id': 'B', 'filesize': 1000, 'width': 500},
            {'format_id': 'C', 'filesize': 1000, 'width': 400},
            {'format_id': 'D', 'filesize': 2000, 'width': 600},
            {'format_id': 'E', 'filesize': 3000},
            {'format_id': 'F'},
            {'format_id': 'G', 'filesize': 1000000},
        ]
        for f in formats:
            f['url'] = 'http://_/'
            f['ext'] = 'unknown'
        info_dict = _make_result(formats, _format_sort_fields=('id', ))

        ydl = YDL({'format': 'best[filesize<3000]'})
        ydl.process_ie_result(info_dict)
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'D')

        ydl = YDL({'format': 'best[filesize<=3000]'})
        ydl.process_ie_result(info_dict)
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'E')

        ydl = YDL({'format': 'best[filesize <= ? 3000]'})
        ydl.process_ie_result(info_dict)
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'F')

        ydl = YDL({'format': 'best [filesize = 1000] [width>450]'})
        ydl.process_ie_result(info_dict)
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'B')

        ydl = YDL({'format': 'best [filesize = 1000] [width!=450]'})
        ydl.process_ie_result(info_dict)
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'C')

        ydl = YDL({'format': '[filesize>?1]'})
        ydl.process_ie_result(info_dict)
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'G')

        ydl = YDL({'format': '[filesize<1M]'})
        ydl.process_ie_result(info_dict)
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'E')

        ydl = YDL({'format': '[filesize<1MiB]'})
        ydl.process_ie_result(info_dict)
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'G')

        ydl = YDL({'format': 'all[width>=400][width<=600]'})
        ydl.process_ie_result(info_dict)
        downloaded_ids = [info['format_id'] for info in ydl.downloaded_info_dicts]
        self.assertEqual(downloaded_ids, ['D', 'C', 'B'])

        ydl = YDL({'format': 'best[height<40]'})
        with contextlib.suppress(ExtractorError):
            ydl.process_ie_result(info_dict)
        self.assertEqual(ydl.downloaded_info_dicts, [])

    @patch('yt_dlp.postprocessor.ffmpeg.FFmpegMergerPP.available', False)
    def test_default_format_spec_without_ffmpeg(self):
        ydl = YDL({})
        self.assertEqual(ydl._default_format_spec({}), 'best/bestvideo+bestaudio')

        ydl = YDL({'simulate': True})
        self.assertEqual(ydl._default_format_spec({}), 'best/bestvideo+bestaudio')

        ydl = YDL({})
        self.assertEqual(ydl._default_format_spec({'is_live': True}), 'best/bestvideo+bestaudio')

        ydl = YDL({'simulate': True})
        self.assertEqual(ydl._default_format_spec({'is_live': True}), 'best/bestvideo+bestaudio')

        ydl = YDL({'outtmpl': '-'})
        self.assertEqual(ydl._default_format_spec({}), 'best/bestvideo+bestaudio')

        ydl = YDL({})
        self.assertEqual(ydl._default_format_spec({}), 'best/bestvideo+bestaudio')
        self.assertEqual(ydl._default_format_spec({'is_live': True}), 'best/bestvideo+bestaudio')

    @patch('yt_dlp.postprocessor.ffmpeg.FFmpegMergerPP.available', True)
    @patch('yt_dlp.postprocessor.ffmpeg.FFmpegMergerPP.can_merge', lambda _: True)
    def test_default_format_spec_with_ffmpeg(self):
        ydl = YDL({})
        self.assertEqual(ydl._default_format_spec({}), 'bestvideo*+bestaudio/best')

        ydl = YDL({'simulate': True})
        self.assertEqual(ydl._default_format_spec({}), 'bestvideo*+bestaudio/best')

        ydl = YDL({})
        self.assertEqual(ydl._default_format_spec({'is_live': True}), 'best/bestvideo+bestaudio')

        ydl = YDL({'simulate': True})
        self.assertEqual(ydl._default_format_spec({'is_live': True}), 'best/bestvideo+bestaudio')

        ydl = YDL({'outtmpl': '-'})
        self.assertEqual(ydl._default_format_spec({}), 'best/bestvideo+bestaudio')

        ydl = YDL({})
        self.assertEqual(ydl._default_format_spec({}), 'bestvideo*+bestaudio/best')
        self.assertEqual(ydl._default_format_spec({'is_live': True}), 'best/bestvideo+bestaudio')


class TestYoutubeDL(unittest.TestCase):
    def test_subtitles(self):
        def s_formats(lang, autocaption=False):
            return [{
                'ext': ext,
                'url': f'http://localhost/video.{lang}.{ext}',
                '_auto': autocaption,
            } for ext in ['vtt', 'srt', 'ass']]
        subtitles = {l: s_formats(l) for l in ['en', 'fr', 'es']}
        auto_captions = {l: s_formats(l, True) for l in ['it', 'pt', 'es']}
        info_dict = {
            'id': 'test',
            'title': 'Test',
            'url': 'http://localhost/video.mp4',
            'subtitles': subtitles,
            'automatic_captions': auto_captions,
            'extractor': 'TEST',
            'webpage_url': 'http://example.com/watch?v=shenanigans',
        }

        def get_info(params={}):
            params.setdefault('simulate', True)
            ydl = YDL(params)
            ydl.report_warning = lambda *args, **kargs: None
            return ydl.process_video_result(info_dict, download=False)

        result = get_info()
        self.assertFalse(result.get('requested_subtitles'))
        self.assertEqual(result['subtitles'], subtitles)
        self.assertEqual(result['automatic_captions'], auto_captions)

        result = get_info({'writesubtitles': True})
        subs = result['requested_subtitles']
        self.assertTrue(subs)
        self.assertEqual(set(subs.keys()), {'en'})
        self.assertTrue(subs['en'].get('data') is None)
        self.assertEqual(subs['en']['ext'], 'ass')

        result = get_info({'writesubtitles': True, 'subtitlesformat': 'foo/srt'})
        subs = result['requested_subtitles']
        self.assertEqual(subs['en']['ext'], 'srt')

        result = get_info({'writesubtitles': True, 'subtitleslangs': ['es', 'fr', 'it']})
        subs = result['requested_subtitles']
        self.assertTrue(subs)
        self.assertEqual(set(subs.keys()), {'es', 'fr'})

        result = get_info({'writesubtitles': True, 'subtitleslangs': ['all', '-en']})
        subs = result['requested_subtitles']
        self.assertTrue(subs)
        self.assertEqual(set(subs.keys()), {'es', 'fr'})

        result = get_info({'writesubtitles': True, 'subtitleslangs': ['en', 'fr', '-en']})
        subs = result['requested_subtitles']
        self.assertTrue(subs)
        self.assertEqual(set(subs.keys()), {'fr'})

        result = get_info({'writesubtitles': True, 'subtitleslangs': ['-en', 'en']})
        subs = result['requested_subtitles']
        self.assertTrue(subs)
        self.assertEqual(set(subs.keys()), {'en'})

        result = get_info({'writesubtitles': True, 'subtitleslangs': ['e.+']})
        subs = result['requested_subtitles']
        self.assertTrue(subs)
        self.assertEqual(set(subs.keys()), {'es', 'en'})

        result = get_info({'writesubtitles': True, 'writeautomaticsub': True, 'subtitleslangs': ['es', 'pt']})
        subs = result['requested_subtitles']
        self.assertTrue(subs)
        self.assertEqual(set(subs.keys()), {'es', 'pt'})
        self.assertFalse(subs['es']['_auto'])
        self.assertTrue(subs['pt']['_auto'])

        result = get_info({'writeautomaticsub': True, 'subtitleslangs': ['es', 'pt']})
        subs = result['requested_subtitles']
        self.assertTrue(subs)
        self.assertEqual(set(subs.keys()), {'es', 'pt'})
        self.assertTrue(subs['es']['_auto'])
        self.assertTrue(subs['pt']['_auto'])

    def test_add_extra_info(self):
        test_dict = {
            'extractor': 'Foo',
        }
        extra_info = {
            'extractor': 'Bar',
            'playlist': 'funny videos',
        }
        YDL.add_extra_info(test_dict, extra_info)
        self.assertEqual(test_dict['extractor'], 'Foo')
        self.assertEqual(test_dict['playlist'], 'funny videos')

    outtmpl_info = {
        'id': '1234',
        'ext': 'mp4',
        'width': None,
        'height': 1080,
        'filesize': 1024,
        'title1': '$PATH',
        'title2': '%PATH%',
        'title3': 'foo/bar\\test',
        'title4': 'foo "bar" test',
        'title5': 'áéí 𝐀',
        'timestamp': 1618488000,
        'duration': 100000,
        'playlist_index': 1,
        'playlist_autonumber': 2,
        '__last_playlist_index': 100,
        'n_entries': 10,
        'formats': [
            {'id': 'id 1', 'height': 1080, 'width': 1920},
            {'id': 'id 2', 'height': 720},
            {'id': 'id 3'},
        ],
    }

    def test_prepare_outtmpl_and_filename(self):
        def test(tmpl, expected, *, info=None, **params):
            params['outtmpl'] = tmpl
            ydl = FakeYDL(params)
            ydl._num_downloads = 1
            self.assertEqual(ydl.validate_outtmpl(tmpl), None)

            out = ydl.evaluate_outtmpl(tmpl, info or self.outtmpl_info)
            fname = ydl.prepare_filename(info or self.outtmpl_info)

            if not isinstance(expected, (list, tuple)):
                expected = (expected, expected)
            for (name, got), expect in zip((('outtmpl', out), ('filename', fname)), expected):
                if callable(expect):
                    self.assertTrue(expect(got), f'Wrong {name} from {tmpl}')
                elif expect is not None:
                    self.assertEqual(got, expect, f'Wrong {name} from {tmpl}')

        # Side-effects
        original_infodict = dict(self.outtmpl_info)
        test('foo.bar', 'foo.bar')
        original_infodict['epoch'] = self.outtmpl_info.get('epoch')
        self.assertTrue(isinstance(original_infodict['epoch'], int))
        test('%(epoch)d', int_or_none)
        self.assertEqual(original_infodict, self.outtmpl_info)

        # Auto-generated fields
        test('%(id)s.%(ext)s', '1234.mp4')
        test('%(duration_string)s', ('27:46:40', '27-46-40'))
        test('%(resolution)s', '1080p')
        test('%(playlist_index|)s', '001')
        test('%(playlist_index&{}!)s', '1!')
        test('%(playlist_autonumber)s', '02')
        test('%(autonumber)s', '00001')
        test('%(autonumber+2)03d', '005', autonumber_start=3)
        test('%(autonumber)s', '001', autonumber_size=3)

        # Escaping %
        test('%', '%')
        test('%%', '%')
        test('%%%%', '%%')
        test('%s', '%s')
        test('%%%s', '%%s')
        test('%d', '%d')
        test('%abc%', '%abc%')
        test('%%(width)06d.%(ext)s', '%(width)06d.mp4')
        test('%%%(height)s', '%1080')
        test('%(width)06d.%(ext)s', 'NA.mp4')
        test('%(width)06d.%%(ext)s', 'NA.%(ext)s')
        test('%%(width)06d.%(ext)s', '%(width)06d.mp4')

        # ID sanitization
        test('%(id)s', '_abcd', info={'id': '_abcd'})
        test('%(some_id)s', '_abcd', info={'some_id': '_abcd'})
        test('%(formats.0.id)s', '_abcd', info={'formats': [{'id': '_abcd'}]})
        test('%(id)s', '-abcd', info={'id': '-abcd'})
        test('%(id)s', '.abcd', info={'id': '.abcd'})
        test('%(id)s', 'ab__cd', info={'id': 'ab__cd'})
        test('%(id)s', ('ab:cd', 'ab：cd'), info={'id': 'ab:cd'})
        test('%(id.0)s', '-', info={'id': '--'})

        # Invalid templates
        self.assertTrue(isinstance(YoutubeDL.validate_outtmpl('%(title)'), ValueError))
        test('%(invalid@tmpl|def)s', 'none', outtmpl_na_placeholder='none')
        test('%(..)s', 'NA')
        test('%(formats.{id)s', 'NA')

        # Entire info_dict
        def expect_same_infodict(out):
            got_dict = json.loads(out)
            for info_field, expected in self.outtmpl_info.items():
                self.assertEqual(got_dict.get(info_field), expected, info_field)
            return True

        test('%()j', (expect_same_infodict, None))

        # NA placeholder
        NA_TEST_OUTTMPL = '%(uploader_date)s-%(width)d-%(x|def)s-%(id)s.%(ext)s'
        test(NA_TEST_OUTTMPL, 'NA-NA-def-1234.mp4')
        test(NA_TEST_OUTTMPL, 'none-none-def-1234.mp4', outtmpl_na_placeholder='none')
        test(NA_TEST_OUTTMPL, '--def-1234.mp4', outtmpl_na_placeholder='')
        test('%(non_existent.0)s', 'NA')

        # String formatting
        FMT_TEST_OUTTMPL = '%%(height)%s.%%(ext)s'
        test(FMT_TEST_OUTTMPL % 's', '1080.mp4')
        test(FMT_TEST_OUTTMPL % 'd', '1080.mp4')
        test(FMT_TEST_OUTTMPL % '6d', '  1080.mp4')
        test(FMT_TEST_OUTTMPL % '-6d', '1080  .mp4')
        test(FMT_TEST_OUTTMPL % '06d', '001080.mp4')
        test(FMT_TEST_OUTTMPL % ' 06d', ' 01080.mp4')
        test(FMT_TEST_OUTTMPL % '   06d', ' 01080.mp4')
        test(FMT_TEST_OUTTMPL % '0 6d', ' 01080.mp4')
        test(FMT_TEST_OUTTMPL % '0   6d', ' 01080.mp4')
        test(FMT_TEST_OUTTMPL % '   0   6d', ' 01080.mp4')

        # Type casting
        test('%(id)d', '1234')
        test('%(height)c', '1')
        test('%(ext)c', 'm')
        test('%(id)d %(id)r', "1234 '1234'")
        test('%(id)r %(height)r', "'1234' 1080")
        test('%(title5)a %(height)a', (R"'\xe1\xe9\xed \U0001d400' 1080", None))
        test('%(ext)s-%(ext|def)d', 'mp4-def')
        test('%(width|0)04d', '0')
        test('a%(width|b)d', 'ab', outtmpl_na_placeholder='none')

        FORMATS = self.outtmpl_info['formats']

        # Custom type casting
        test('%(formats.:.id)l', 'id 1, id 2, id 3')
        test('%(formats.:.id)#l', ('id 1\nid 2\nid 3', 'id 1 id 2 id 3'))
        test('%(ext)l', 'mp4')
        test('%(formats.:.id) 18l', '  id 1, id 2, id 3')
        test('%(formats)j', (json.dumps(FORMATS), None))
        test('%(formats)#j', (
            json.dumps(FORMATS, indent=4),
            json.dumps(FORMATS, indent=4).replace(':', '：').replace('"', '＂').replace('\n', ' '),
        ))
        test('%(title5).3B', 'á')
        test('%(title5)U', 'áéí 𝐀')
        test('%(title5)#U', 'a\u0301e\u0301i\u0301 𝐀')
        test('%(title5)+U', 'áéí A')
        test('%(title5)+#U', 'a\u0301e\u0301i\u0301 A')
        test('%(height)D', '1k')
        test('%(filesize)#D', '1Ki')
        test('%(height)5.2D', ' 1.08k')
        test('%(title4)#S', 'foo_bar_test')
        test('%(title4).10S', ('foo ＂bar＂ ', 'foo ＂bar＂' + ('#' if os.name == 'nt' else ' ')))
        if os.name == 'nt':
            test('%(title4)q', ('"foo ""bar"" test"', None))
            test('%(formats.:.id)#q', ('"id 1" "id 2" "id 3"', None))
            test('%(formats.0.id)#q', ('"id 1"', None))
        else:
            test('%(title4)q', ('\'foo "bar" test\'', '\'foo ＂bar＂ test\''))
            test('%(formats.:.id)#q', "'id 1' 'id 2' 'id 3'")
            test('%(formats.0.id)#q', "'id 1'")

        # Internal formatting
        test('%(timestamp-1000>%H-%M-%S)s', '11-43-20')
        test('%(title|%)s %(title|%%)s', '% %%')
        test('%(id+1-height+3)05d', '00158')
        test('%(width+100)05d', 'NA')
        test('%(filesize*8)d', '8192')
        test('%(formats.0) 15s', ('% 15s' % FORMATS[0], None))
        test('%(formats.0)r', (repr(FORMATS[0]), None))
        test('%(height.0)03d', '001')
        test('%(-height.0)04d', '-001')
        test('%(formats.-1.id)s', FORMATS[-1]['id'])
        test('%(formats.0.id.-1)d', FORMATS[0]['id'][-1])
        test('%(formats.3)s', 'NA')
        test('%(formats.:2:-1)r', repr(FORMATS[:2:-1]))
        test('%(formats.0.id.-1+id)f', '1235.000000')
        test('%(formats.0.id.-1+formats.1.id.-1)d', '3')
        out = json.dumps([{'id': f['id'], 'height.:2': str(f['height'])[:2]}
                          if 'height' in f else {'id': f['id']}
                          for f in FORMATS])
        test('%(formats.:.{id,height.:2})j', (out, None))
        test('%(formats.:.{id,height}.id)l', ', '.join(f['id'] for f in FORMATS))
        test('%(.{id,title})j', ('{"id": "1234"}', '{＂id＂： ＂1234＂}'))

        # Alternates
        test('%(title,id)s', '1234')
        test('%(width-100,height+20|def)d', '1100')
        test('%(width-100,height+width|def)s', 'def')
        test('%(timestamp-x>%H\\,%M\\,%S,timestamp>%H\\,%M\\,%S)s', '12,00,00')

        # Replacement
        test('%(id&foo)s.bar', 'foo.bar')
        test('%(title&foo)s.bar', 'NA.bar')
        test('%(title&foo|baz)s.bar', 'baz.bar')
        test('%(x,id&foo|baz)s.bar', 'foo.bar')
        test('%(x,title&foo|baz)s.bar', 'baz.bar')
        test('%(id&a\nb|)s', ('a\nb', 'a b'))
        test('%(id&hi {:>10} {}|)s', 'hi       1234 1234')
        test(R'%(id&{0} {}|)s', 'NA')
        test(R'%(id&{0.1}|)s', 'NA')
        test('%(height&{:,d})S', '1,080')

        # Laziness
        def gen():
            yield from range(5)
            raise self.assertTrue(False, 'LazyList should not be evaluated till here')
        test('%(key.4)s', '4', info={'key': LazyList(gen())})

        # Empty filename
        test('%(foo|)s-%(bar|)s.%(ext)s', '-.mp4')
        # test('%(foo|)s.%(ext)s', ('.mp4', '_.mp4'))  # FIXME: ?
        # test('%(foo|)s', ('', '_'))  # FIXME: ?

        # Environment variable expansion for prepare_filename
        os.environ['__yt_dlp_var'] = 'expanded'
        envvar = '%__yt_dlp_var%' if os.name == 'nt' else '$__yt_dlp_var'
        test(envvar, (envvar, 'expanded'))
        if os.name == 'nt':
            test('%s%', ('%s%', '%s%'))
            os.environ['s'] = 'expanded'
            test('%s%', ('%s%', 'expanded'))  # %s% should be expanded before escaping %s
            os.environ['(test)s'] = 'expanded'
            test('%(test)s%', ('NA%', 'expanded'))  # Environment should take priority over template

        # Path expansion and escaping
        test('Hello %(title1)s', 'Hello $PATH')
        test('Hello %(title2)s', 'Hello %PATH%')
        test('%(title3)s', ('foo/bar\\test', 'foo⧸bar⧹test'))
        test('folder/%(title3)s', ('folder/foo/bar\\test', f'folder{os.path.sep}foo⧸bar⧹test'))

    def test_format_note(self):
        ydl = YoutubeDL()
        self.assertEqual(ydl._format_note({}), '')
        assertRegexpMatches(self, ydl._format_note({
            'vbr': 10,
        }), r'^\s*10k$')
        assertRegexpMatches(self, ydl._format_note({
            'fps': 30,
        }), r'^30fps$')

    def test_postprocessors(self):
        filename = 'post-processor-testfile.mp4'
        audiofile = filename + '.mp3'

        class SimplePP(PostProcessor):
            def run(self, info):
                with open(audiofile, 'w') as f:
                    f.write('EXAMPLE')
                return [info['filepath']], info

        def run_pp(params, pp):
            with open(filename, 'w') as f:
                f.write('EXAMPLE')
            ydl = YoutubeDL(params)
            ydl.add_post_processor(pp())
            ydl.post_process(filename, {'filepath': filename})

        run_pp({'keepvideo': True}, SimplePP)
        self.assertTrue(os.path.exists(filename), f'{filename} doesn\'t exist')
        self.assertTrue(os.path.exists(audiofile), f'{audiofile} doesn\'t exist')
        os.unlink(filename)
        os.unlink(audiofile)

        run_pp({'keepvideo': False}, SimplePP)
        self.assertFalse(os.path.exists(filename), f'{filename} exists')
        self.assertTrue(os.path.exists(audiofile), f'{audiofile} doesn\'t exist')
        os.unlink(audiofile)

        class ModifierPP(PostProcessor):
            def run(self, info):
                with open(info['filepath'], 'w') as f:
                    f.write('MODIFIED')
                return [], info

        run_pp({'keepvideo': False}, ModifierPP)
        self.assertTrue(os.path.exists(filename), f'{filename} doesn\'t exist')
        os.unlink(filename)

    def test_match_filter(self):
        first = {
            'id': '1',
            'url': TEST_URL,
            'title': 'one',
            'extractor': 'TEST',
            'duration': 30,
            'filesize': 10 * 1024,
            'playlist_id': '42',
            'uploader': '變態妍字幕版 太妍 тест',
            'creator': "тест ' 123 ' тест--",
            'webpage_url': 'http://example.com/watch?v=shenanigans',
        }
        second = {
            'id': '2',
            'url': TEST_URL,
            'title': 'two',
            'extractor': 'TEST',
            'duration': 10,
            'description': 'foo',
            'filesize': 5 * 1024,
            'playlist_id': '43',
            'uploader': 'тест 123',
            'webpage_url': 'http://example.com/watch?v=SHENANIGANS',
        }
        videos = [first, second]

        def get_videos(filter_=None):
            ydl = YDL({'match_filter': filter_, 'simulate': True})
            for v in videos:
                ydl.process_ie_result(v.copy(), download=True)
            return [v['id'] for v in ydl.downloaded_info_dicts]

        res = get_videos()
        self.assertEqual(res, ['1', '2'])

        def f(v, incomplete):
            if v['id'] == '1':
                return None
            else:
                return 'Video id is not 1'
        res = get_videos(f)
        self.assertEqual(res, ['1'])

        f = match_filter_func('duration < 30')
        res = get_videos(f)
        self.assertEqual(res, ['2'])

        f = match_filter_func('description = foo')
        res = get_videos(f)
        self.assertEqual(res, ['2'])

        f = match_filter_func('description =? foo')
        res = get_videos(f)
        self.assertEqual(res, ['1', '2'])

        f = match_filter_func('filesize > 5KiB')
        res = get_videos(f)
        self.assertEqual(res, ['1'])

        f = match_filter_func('playlist_id = 42')
        res = get_videos(f)
        self.assertEqual(res, ['1'])

        f = match_filter_func('uploader = "變態妍字幕版 太妍 тест"')
        res = get_videos(f)
        self.assertEqual(res, ['1'])

        f = match_filter_func('uploader != "變態妍字幕版 太妍 тест"')
        res = get_videos(f)
        self.assertEqual(res, ['2'])

        f = match_filter_func('creator = "тест \' 123 \' тест--"')
        res = get_videos(f)
        self.assertEqual(res, ['1'])

        f = match_filter_func("creator = 'тест \\' 123 \\' тест--'")
        res = get_videos(f)
        self.assertEqual(res, ['1'])

        f = match_filter_func(r"creator = 'тест \' 123 \' тест--' & duration > 30")
        res = get_videos(f)
        self.assertEqual(res, [])

    def test_playlist_items_selection(self):
        INDICES, PAGE_SIZE = list(range(1, 11)), 3

        def entry(i, evaluated):
            evaluated.append(i)
            return {
                'id': str(i),
                'title': str(i),
                'url': TEST_URL,
            }

        def pagedlist_entries(evaluated):
            def page_func(n):
                start = PAGE_SIZE * n
                for i in INDICES[start: start + PAGE_SIZE]:
                    yield entry(i, evaluated)
            return OnDemandPagedList(page_func, PAGE_SIZE)

        def page_num(i):
            return (i + PAGE_SIZE - 1) // PAGE_SIZE

        def generator_entries(evaluated):
            for i in INDICES:
                yield entry(i, evaluated)

        def list_entries(evaluated):
            return list(generator_entries(evaluated))

        def lazylist_entries(evaluated):
            return LazyList(generator_entries(evaluated))

        def get_downloaded_info_dicts(params, entries):
            ydl = YDL(params)
            ydl.process_ie_result({
                '_type': 'playlist',
                'id': 'test',
                'extractor': 'test:playlist',
                'extractor_key': 'test:playlist',
                'webpage_url': 'http://example.com',
                'entries': entries,
            })
            return ydl.downloaded_info_dicts

        def test_selection(params, expected_ids, evaluate_all=False):
            expected_ids = list(expected_ids)
            if evaluate_all:
                generator_eval = pagedlist_eval = INDICES
            elif not expected_ids:
                generator_eval = pagedlist_eval = []
            else:
                generator_eval = INDICES[0: max(expected_ids)]
                pagedlist_eval = INDICES[PAGE_SIZE * page_num(min(expected_ids)) - PAGE_SIZE:
                                         PAGE_SIZE * page_num(max(expected_ids))]

            for name, func, expected_eval in (
                ('list', list_entries, INDICES),
                ('Generator', generator_entries, generator_eval),
                # ('LazyList', lazylist_entries, generator_eval),  # Generator and LazyList follow the exact same code path
                ('PagedList', pagedlist_entries, pagedlist_eval),
            ):
                evaluated = []
                entries = func(evaluated)
                results = [(v['playlist_autonumber'] - 1, (int(v['id']), v['playlist_index']))
                           for v in get_downloaded_info_dicts(params, entries)]
                self.assertEqual(results, list(enumerate(zip(expected_ids, expected_ids))), f'Entries of {name} for {params}')
                self.assertEqual(sorted(evaluated), expected_eval, f'Evaluation of {name} for {params}')

        test_selection({}, INDICES)
        test_selection({'playlistend': 20}, INDICES, True)
        test_selection({'playlistend': 2}, INDICES[:2])
        test_selection({'playliststart': 11}, [], True)
        test_selection({'playliststart': 2}, INDICES[1:])
        test_selection({'playlist_items': '2-4'}, INDICES[1:4])
        test_selection({'playlist_items': '2,4'}, [2, 4])
        test_selection({'playlist_items': '20'}, [], True)
        test_selection({'playlist_items': '0'}, [])

        # Tests for https://github.com/ytdl-org/youtube-dl/issues/10591
        test_selection({'playlist_items': '2-4,3-4,3'}, [2, 3, 4])
        test_selection({'playlist_items': '4,2'}, [4, 2])

        # Tests for https://github.com/yt-dlp/yt-dlp/issues/720
        # https://github.com/yt-dlp/yt-dlp/issues/302
        test_selection({'playlistreverse': True}, INDICES[::-1])
        test_selection({'playliststart': 2, 'playlistreverse': True}, INDICES[:0:-1])
        test_selection({'playlist_items': '2,4', 'playlistreverse': True}, [4, 2])
        test_selection({'playlist_items': '4,2'}, [4, 2])

        # Tests for --playlist-items start:end:step
        test_selection({'playlist_items': ':'}, INDICES, True)
        test_selection({'playlist_items': '::1'}, INDICES, True)
        test_selection({'playlist_items': '::-1'}, INDICES[::-1], True)
        test_selection({'playlist_items': ':6'}, INDICES[:6])
        test_selection({'playlist_items': ':-6'}, INDICES[:-5], True)
        test_selection({'playlist_items': '-1:6:-2'}, INDICES[:4:-2], True)
        test_selection({'playlist_items': '9:-6:-2'}, INDICES[8:3:-2], True)

        test_selection({'playlist_items': '1:inf:2'}, INDICES[::2], True)
        test_selection({'playlist_items': '-2:inf'}, INDICES[-2:], True)
        test_selection({'playlist_items': ':inf:-1'}, [], True)
        test_selection({'playlist_items': '0-2:2'}, [2])
        test_selection({'playlist_items': '1-:2'}, INDICES[::2], True)
        test_selection({'playlist_items': '0--2:2'}, INDICES[1:-1:2], True)

        test_selection({'playlist_items': '10::3'}, [10], True)
        test_selection({'playlist_items': '-1::3'}, [10], True)
        test_selection({'playlist_items': '11::3'}, [], True)
        test_selection({'playlist_items': '-15::2'}, INDICES[1::2], True)
        test_selection({'playlist_items': '-15::15'}, [], True)

    def test_do_not_override_ie_key_in_url_transparent(self):
        ydl = YDL()

        class Foo1IE(InfoExtractor):
            _VALID_URL = r'foo1:'

            def _real_extract(self, url):
                return {
                    '_type': 'url_transparent',
                    'url': 'foo2:',
                    'ie_key': 'Foo2',
                    'title': 'foo1 title',
                    'id': 'foo1_id',
                }

        class Foo2IE(InfoExtractor):
            _VALID_URL = r'foo2:'

            def _real_extract(self, url):
                return {
                    '_type': 'url',
                    'url': 'foo3:',
                    'ie_key': 'Foo3',
                }

        class Foo3IE(InfoExtractor):
            _VALID_URL = r'foo3:'

            def _real_extract(self, url):
                return _make_result([{'url': TEST_URL}], title='foo3 title')

        ydl.add_info_extractor(Foo1IE(ydl))
        ydl.add_info_extractor(Foo2IE(ydl))
        ydl.add_info_extractor(Foo3IE(ydl))
        ydl.extract_info('foo1:')
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['url'], TEST_URL)
        self.assertEqual(downloaded['title'], 'foo1 title')
        self.assertEqual(downloaded['id'], 'testid')
        self.assertEqual(downloaded['extractor'], 'testex')
        self.assertEqual(downloaded['extractor_key'], 'TestEx')

    # Test case for https://github.com/ytdl-org/youtube-dl/issues/27064
    def test_ignoreerrors_for_playlist_with_url_transparent_iterable_entries(self):

        class _YDL(YDL):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            def trouble(self, s, tb=None):
                pass

        ydl = _YDL({
            'format': 'extra',
            'ignoreerrors': True,
        })

        class VideoIE(InfoExtractor):
            _VALID_URL = r'video:(?P<id>\d+)'

            def _real_extract(self, url):
                video_id = self._match_id(url)
                formats = [{
                    'format_id': 'default',
                    'url': 'url:',
                }]
                if video_id == '0':
                    raise ExtractorError('foo')
                if video_id == '2':
                    formats.append({
                        'format_id': 'extra',
                        'url': TEST_URL,
                    })
                return {
                    'id': video_id,
                    'title': f'Video {video_id}',
                    'formats': formats,
                }

        class PlaylistIE(InfoExtractor):
            _VALID_URL = r'playlist:'

            def _entries(self):
                for n in range(3):
                    video_id = str(n)
                    yield {
                        '_type': 'url_transparent',
                        'ie_key': VideoIE.ie_key(),
                        'id': video_id,
                        'url': f'video:{video_id}',
                        'title': f'Video Transparent {video_id}',
                    }

            def _real_extract(self, url):
                return self.playlist_result(self._entries())

        ydl.add_info_extractor(VideoIE(ydl))
        ydl.add_info_extractor(PlaylistIE(ydl))
        info = ydl.extract_info('playlist:')
        entries = info['entries']
        self.assertEqual(len(entries), 3)
        self.assertTrue(entries[0] is None)
        self.assertTrue(entries[1] is None)
        self.assertEqual(len(ydl.downloaded_info_dicts), 1)
        downloaded = ydl.downloaded_info_dicts[0]
        entries[2].pop('requested_downloads', None)
        self.assertEqual(entries[2], downloaded)
        self.assertEqual(downloaded['url'], TEST_URL)
        self.assertEqual(downloaded['title'], 'Video Transparent 2')
        self.assertEqual(downloaded['id'], '2')
        self.assertEqual(downloaded['extractor'], 'Video')
        self.assertEqual(downloaded['extractor_key'], 'Video')

    def test_header_cookies(self):
        from http.cookiejar import Cookie

        ydl = FakeYDL()
        ydl.report_warning = lambda *_, **__: None

        def cookie(name, value, version=None, domain='', path='', secure=False, expires=None):
            return Cookie(
                version or 0, name, value, None, False,
                domain, bool(domain), bool(domain), path, bool(path),
                secure, expires, False, None, None, rest={})

        _test_url = 'https://yt.dlp/test'

        def test(encoded_cookies, cookies, *, headers=False, round_trip=None, error_re=None):
            def _test():
                ydl.cookiejar.clear()
                ydl._load_cookies(encoded_cookies, autoscope=headers)
                if headers:
                    ydl._apply_header_cookies(_test_url)
                data = {'url': _test_url}
                ydl._calc_headers(data)
                self.assertCountEqual(
                    map(vars, ydl.cookiejar), map(vars, cookies),
                    'Extracted cookiejar.Cookie is not the same')
                if not headers:
                    self.assertEqual(
                        data.get('cookies'), round_trip or encoded_cookies,
                        'Cookie is not the same as round trip')
                ydl.__dict__['_YoutubeDL__header_cookies'] = []

            with self.subTest(msg=encoded_cookies):
                if not error_re:
                    _test()
                    return
                with self.assertRaisesRegex(Exception, error_re):
                    _test()

        test('test=value; Domain=.yt.dlp', [cookie('test', 'value', domain='.yt.dlp')])
        test('test=value', [cookie('test', 'value')], error_re=r'Unscoped cookies are not allowed')
        test('cookie1=value1; Domain=.yt.dlp; Path=/test; cookie2=value2; Domain=.yt.dlp; Path=/', [
            cookie('cookie1', 'value1', domain='.yt.dlp', path='/test'),
            cookie('cookie2', 'value2', domain='.yt.dlp', path='/')])
        test('test=value; Domain=.yt.dlp; Path=/test; Secure; Expires=9999999999', [
            cookie('test', 'value', domain='.yt.dlp', path='/test', secure=True, expires=9999999999)])
        test('test="value; "; path=/test; domain=.yt.dlp', [
            cookie('test', 'value; ', domain='.yt.dlp', path='/test')],
            round_trip='test="value\\073 "; Domain=.yt.dlp; Path=/test')
        test('name=; Domain=.yt.dlp', [cookie('name', '', domain='.yt.dlp')],
             round_trip='name=""; Domain=.yt.dlp')

        test('test=value', [cookie('test', 'value', domain='.yt.dlp')], headers=True)
        test('cookie1=value; Domain=.yt.dlp; cookie2=value', [], headers=True, error_re=r'Invalid syntax')
        ydl.deprecated_feature = ydl.report_error
        test('test=value', [], headers=True, error_re=r'Passing cookies as a header is a potential security risk')

    def test_infojson_cookies(self):
        TEST_FILE = 'test_infojson_cookies.info.json'
        TEST_URL = 'https://example.com/example.mp4'
        COOKIES = 'a=b; Domain=.example.com; c=d; Domain=.example.com'
        COOKIE_HEADER = {'Cookie': 'a=b; c=d'}

        ydl = FakeYDL()
        ydl.process_info = lambda x: ydl._write_info_json('test', x, TEST_FILE)

        def make_info(info_header_cookies=False, fmts_header_cookies=False, cookies_field=False):
            fmt = {'url': TEST_URL}
            if fmts_header_cookies:
                fmt['http_headers'] = COOKIE_HEADER
            if cookies_field:
                fmt['cookies'] = COOKIES
            return _make_result([fmt], http_headers=COOKIE_HEADER if info_header_cookies else None)

        def test(initial_info, note):
            result = {}
            result['processed'] = ydl.process_ie_result(initial_info)
            self.assertTrue(ydl.cookiejar.get_cookies_for_url(TEST_URL),
                            msg=f'No cookies set in cookiejar after initial process when {note}')
            ydl.cookiejar.clear()
            with open(TEST_FILE) as infojson:
                result['loaded'] = ydl.sanitize_info(json.load(infojson), True)
            result['final'] = ydl.process_ie_result(result['loaded'].copy(), download=False)
            self.assertTrue(ydl.cookiejar.get_cookies_for_url(TEST_URL),
                            msg=f'No cookies set in cookiejar after final process when {note}')
            ydl.cookiejar.clear()
            for key in ('processed', 'loaded', 'final'):
                info = result[key]
                self.assertIsNone(
                    traverse_obj(info, ((None, ('formats', 0)), 'http_headers', 'Cookie'), casesense=False, get_all=False),
                    msg=f'Cookie header not removed in {key} result when {note}')
                self.assertEqual(
                    traverse_obj(info, ((None, ('formats', 0)), 'cookies'), get_all=False), COOKIES,
                    msg=f'No cookies field found in {key} result when {note}')

        test({'url': TEST_URL, 'http_headers': COOKIE_HEADER, 'id': '1', 'title': 'x'}, 'no formats field')
        test(make_info(info_header_cookies=True), 'info_dict header cokies')
        test(make_info(fmts_header_cookies=True), 'format header cookies')
        test(make_info(info_header_cookies=True, fmts_header_cookies=True), 'info_dict and format header cookies')
        test(make_info(info_header_cookies=True, fmts_header_cookies=True, cookies_field=True), 'all cookies fields')
        test(make_info(cookies_field=True), 'cookies format field')
        test({'url': TEST_URL, 'cookies': COOKIES, 'id': '1', 'title': 'x'}, 'info_dict cookies field only')

        try_rm(TEST_FILE)

    def test_add_headers_cookie(self):
        def check_for_cookie_header(result):
            return traverse_obj(result, ((None, ('formats', 0)), 'http_headers', 'Cookie'), casesense=False, get_all=False)

        ydl = FakeYDL({'http_headers': {'Cookie': 'a=b'}})
        ydl._apply_header_cookies(_make_result([])['webpage_url'])  # Scope to input webpage URL: .example.com

        fmt = {'url': 'https://example.com/video.mp4'}
        result = ydl.process_ie_result(_make_result([fmt]), download=False)
        self.assertIsNone(check_for_cookie_header(result), msg='http_headers cookies in result info_dict')
        self.assertEqual(result.get('cookies'), 'a=b; Domain=.example.com', msg='No cookies were set in cookies field')
        self.assertIn('a=b', ydl.cookiejar.get_cookie_header(fmt['url']), msg='No cookies were set in cookiejar')

        fmt = {'url': 'https://wrong.com/video.mp4'}
        result = ydl.process_ie_result(_make_result([fmt]), download=False)
        self.assertIsNone(check_for_cookie_header(result), msg='http_headers cookies for wrong domain')
        self.assertFalse(result.get('cookies'), msg='Cookies set in cookies field for wrong domain')
        self.assertFalse(ydl.cookiejar.get_cookie_header(fmt['url']), msg='Cookies set in cookiejar for wrong domain')


if __name__ == '__main__':
    unittest.main()
