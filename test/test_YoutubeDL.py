#!/usr/bin/env python3
# Allow direct execution
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import copy
import json
from test.helper import FakeYDL, assertRegexpMatches

from yt_dlp import YoutubeDL
from yt_dlp.compat import (
    compat_os_name,
    compat_setenv,
    compat_str,
    compat_urllib_error,
)
from yt_dlp.extractor import YoutubeIE
from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.postprocessor.common import PostProcessor
from yt_dlp.utils import (
    ExtractorError,
    LazyList,
    int_or_none,
    match_filter_func,
)

TEST_URL = 'http://localhost/sample.mp4'


class YDL(FakeYDL):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.downloaded_info_dicts = []
        self.msgs = []

    def process_info(self, info_dict):
        self.downloaded_info_dicts.append(info_dict.copy())

    def to_screen(self, msg):
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
        yie = YoutubeIE(ydl)
        yie._sort_formats(info_dict['formats'])
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
        yie = YoutubeIE(ydl)
        yie._sort_formats(info_dict['formats'])
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
        yie = YoutubeIE(ydl)
        yie._sort_formats(info_dict['formats'])
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
        yie = YoutubeIE(ydl)
        yie._sort_formats(info_dict['formats'])
        ydl.process_ie_result(info_dict)
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['ext'], 'webm')

    def test_format_selection(self):
        formats = [
            {'format_id': '35', 'ext': 'mp4', 'preference': 1, 'url': TEST_URL},
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
            downloaded = map(lambda x: x['format_id'], ydl.downloaded_info_dicts)
            self.assertEqual(list(downloaded), list(expected))

        test('20/47', '47')
        test('20/71/worst', '35')
        test(None, '2')
        test('webm/mp4', '47')
        test('3gp/40/mp4', '35')
        test('example-with-dashes', 'example-with-dashes')
        test('all', '2', '47', '45', 'example-with-dashes', '35')
        test('mergeall', '2+47+45+example-with-dashes+35', multi=True)

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
        ydl = YDL({'format': 'best'})
        ie = YoutubeIE(ydl)
        ie._sort_formats(info_dict['formats'])
        ydl.process_ie_result(copy.deepcopy(info_dict))
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'aac-64')

        ydl = YDL({'format': 'mp3'})
        ie = YoutubeIE(ydl)
        ie._sort_formats(info_dict['formats'])
        ydl.process_ie_result(copy.deepcopy(info_dict))
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], 'mp3-64')

        ydl = YDL({'prefer_free_formats': True})
        ie = YoutubeIE(ydl)
        ie._sort_formats(info_dict['formats'])
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
        yie = YoutubeIE(ydl)
        yie._sort_formats(info_dict['formats'])
        ydl.process_ie_result(info_dict)
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], '248+172')
        self.assertEqual(downloaded['ext'], 'mp4')

        info_dict = _make_result(list(formats_order), extractor='youtube')
        ydl = YDL({'format': 'bestvideo[height>=999999]+bestaudio/best'})
        yie = YoutubeIE(ydl)
        yie._sort_formats(info_dict['formats'])
        ydl.process_ie_result(info_dict)
        downloaded = ydl.downloaded_info_dicts[0]
        self.assertEqual(downloaded['format_id'], '38')

        info_dict = _make_result(list(formats_order), extractor='youtube')
        ydl = YDL({'format': 'bestvideo/best,bestaudio'})
        yie = YoutubeIE(ydl)
        yie._sort_formats(info_dict['formats'])
        ydl.process_ie_result(info_dict)
        downloaded_ids = [info['format_id'] for info in ydl.downloaded_info_dicts]
        self.assertEqual(downloaded_ids, ['137', '141'])

        info_dict = _make_result(list(formats_order), extractor='youtube')
        ydl = YDL({'format': '(bestvideo[ext=mp4],bestvideo[ext=webm])+bestaudio'})
        yie = YoutubeIE(ydl)
        yie._sort_formats(info_dict['formats'])
        ydl.process_ie_result(info_dict)
        downloaded_ids = [info['format_id'] for info in ydl.downloaded_info_dicts]
        self.assertEqual(downloaded_ids, ['137+141', '248+141'])

        info_dict = _make_result(list(formats_order), extractor='youtube')
        ydl = YDL({'format': '(bestvideo[ext=mp4],bestvideo[ext=webm])[height<=720]+bestaudio'})
        yie = YoutubeIE(ydl)
        yie._sort_formats(info_dict['formats'])
        ydl.process_ie_result(info_dict)
        downloaded_ids = [info['format_id'] for info in ydl.downloaded_info_dicts]
        self.assertEqual(downloaded_ids, ['136+141', '247+141'])

        info_dict = _make_result(list(formats_order), extractor='youtube')
        ydl = YDL({'format': '(bestvideo[ext=none]/bestvideo[ext=webm])+bestaudio'})
        yie = YoutubeIE(ydl)
        yie._sort_formats(info_dict['formats'])
        ydl.process_ie_result(info_dict)
        downloaded_ids = [info['format_id'] for info in ydl.downloaded_info_dicts]
        self.assertEqual(downloaded_ids, ['248+141'])

        for f1, f2 in zip(formats_order, formats_order[1:]):
            info_dict = _make_result([f1, f2], extractor='youtube')
            ydl = YDL({'format': 'best/bestvideo'})
            yie = YoutubeIE(ydl)
            yie._sort_formats(info_dict['formats'])
            ydl.process_ie_result(info_dict)
            downloaded = ydl.downloaded_info_dicts[0]
            self.assertEqual(downloaded['format_id'], f1['format_id'])

            info_dict = _make_result([f2, f1], extractor='youtube')
            ydl = YDL({'format': 'best/bestvideo'})
            yie = YoutubeIE(ydl)
            yie._sort_formats(info_dict['formats'])
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
        info_dict = _make_result(formats)

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
        try:
            ydl.process_ie_result(info_dict)
        except ExtractorError:
            pass
        self.assertEqual(ydl.downloaded_info_dicts, [])

    def test_default_format_spec(self):
        ydl = YDL({'simulate': True})
        self.assertEqual(ydl._default_format_spec({}), 'bestvideo*+bestaudio/best')

        ydl = YDL({})
        self.assertEqual(ydl._default_format_spec({'is_live': True}), 'best/bestvideo+bestaudio')

        ydl = YDL({'simulate': True})
        self.assertEqual(ydl._default_format_spec({'is_live': True}), 'bestvideo*+bestaudio/best')

        ydl = YDL({'outtmpl': '-'})
        self.assertEqual(ydl._default_format_spec({}), 'best/bestvideo+bestaudio')

        ydl = YDL({})
        self.assertEqual(ydl._default_format_spec({}, download=False), 'bestvideo*+bestaudio/best')
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
        'formats': [{'id': 'id 1'}, {'id': 'id 2'}, {'id': 'id 3'}]
    }

    def test_prepare_outtmpl_and_filename(self):
        def test(tmpl, expected, *, info=None, **params):
            params['outtmpl'] = tmpl
            ydl = YoutubeDL(params)
            ydl._num_downloads = 1
            self.assertEqual(ydl.validate_outtmpl(tmpl), None)

            out = ydl.evaluate_outtmpl(tmpl, info or self.outtmpl_info)
            fname = ydl.prepare_filename(info or self.outtmpl_info)

            if not isinstance(expected, (list, tuple)):
                expected = (expected, expected)
            for (name, got), expect in zip((('outtmpl', out), ('filename', fname)), expected):
                if callable(expect):
                    self.assertTrue(expect(got), f'Wrong {name} from {tmpl}')
                else:
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
        test('%(playlist_index)s', '001')
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
        test('%(id)s', ('ab:cd', 'ab -cd'), info={'id': 'ab:cd'})
        test('%(id.0)s', '-', info={'id': '--'})

        # Invalid templates
        self.assertTrue(isinstance(YoutubeDL.validate_outtmpl('%(title)'), ValueError))
        test('%(invalid@tmpl|def)s', 'none', outtmpl_na_placeholder='none')
        test('%(..)s', 'NA')

        # Entire info_dict
        def expect_same_infodict(out):
            got_dict = json.loads(out)
            for info_field, expected in self.outtmpl_info.items():
                self.assertEqual(got_dict.get(info_field), expected, info_field)
            return True

        test('%()j', (expect_same_infodict, str))

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
        test('%(ext)s-%(ext|def)d', 'mp4-def')
        test('%(width|0)04d', '0000')
        test('a%(width|)d', 'a', outtmpl_na_placeholder='none')

        FORMATS = self.outtmpl_info['formats']
        sanitize = lambda x: x.replace(':', ' -').replace('"', "'").replace('\n', ' ')

        # Custom type casting
        test('%(formats.:.id)l', 'id 1, id 2, id 3')
        test('%(formats.:.id)#l', ('id 1\nid 2\nid 3', 'id 1 id 2 id 3'))
        test('%(ext)l', 'mp4')
        test('%(formats.:.id) 18l', '  id 1, id 2, id 3')
        test('%(formats)j', (json.dumps(FORMATS), sanitize(json.dumps(FORMATS))))
        test('%(formats)#j', (json.dumps(FORMATS, indent=4), sanitize(json.dumps(FORMATS, indent=4))))
        test('%(title5).3B', 'á')
        test('%(title5)U', 'áéí 𝐀')
        test('%(title5)#U', 'a\u0301e\u0301i\u0301 𝐀')
        test('%(title5)+U', 'áéí A')
        test('%(title5)+#U', 'a\u0301e\u0301i\u0301 A')
        test('%(height)D', '1k')
        test('%(filesize)#D', '1Ki')
        test('%(height)5.2D', ' 1.08k')
        test('%(title4)#S', 'foo_bar_test')
        test('%(title4).10S', ('foo \'bar\' ', 'foo \'bar\'' + ('#' if compat_os_name == 'nt' else ' ')))
        if compat_os_name == 'nt':
            test('%(title4)q', ('"foo \\"bar\\" test"', "'foo _'bar_' test'"))
            test('%(formats.:.id)#q', ('"id 1" "id 2" "id 3"', "'id 1' 'id 2' 'id 3'"))
            test('%(formats.0.id)#q', ('"id 1"', "'id 1'"))
        else:
            test('%(title4)q', ('\'foo "bar" test\'', "'foo 'bar' test'"))
            test('%(formats.:.id)#q', "'id 1' 'id 2' 'id 3'")
            test('%(formats.0.id)#q', "'id 1'")

        # Internal formatting
        test('%(timestamp-1000>%H-%M-%S)s', '11-43-20')
        test('%(title|%)s %(title|%%)s', '% %%')
        test('%(id+1-height+3)05d', '00158')
        test('%(width+100)05d', 'NA')
        test('%(formats.0) 15s', ('% 15s' % FORMATS[0], '% 15s' % sanitize(str(FORMATS[0]))))
        test('%(formats.0)r', (repr(FORMATS[0]), sanitize(repr(FORMATS[0]))))
        test('%(height.0)03d', '001')
        test('%(-height.0)04d', '-001')
        test('%(formats.-1.id)s', FORMATS[-1]['id'])
        test('%(formats.0.id.-1)d', FORMATS[0]['id'][-1])
        test('%(formats.3)s', 'NA')
        test('%(formats.:2:-1)r', repr(FORMATS[:2:-1]))
        test('%(formats.0.id.-1+id)f', '1235.000000')
        test('%(formats.0.id.-1+formats.1.id.-1)d', '3')

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

        # Laziness
        def gen():
            yield from range(5)
            raise self.assertTrue(False, 'LazyList should not be evaluated till here')
        test('%(key.4)s', '4', info={'key': LazyList(gen())})

        # Empty filename
        test('%(foo|)s-%(bar|)s.%(ext)s', '-.mp4')
        # test('%(foo|)s.%(ext)s', ('.mp4', '_.mp4'))  # fixme
        # test('%(foo|)s', ('', '_'))  # fixme

        # Environment variable expansion for prepare_filename
        compat_setenv('__yt_dlp_var', 'expanded')
        envvar = '%__yt_dlp_var%' if compat_os_name == 'nt' else '$__yt_dlp_var'
        test(envvar, (envvar, 'expanded'))
        if compat_os_name == 'nt':
            test('%s%', ('%s%', '%s%'))
            compat_setenv('s', 'expanded')
            test('%s%', ('%s%', 'expanded'))  # %s% should be expanded before escaping %s
            compat_setenv('(test)s', 'expanded')
            test('%(test)s%', ('NA%', 'expanded'))  # Environment should take priority over template

        # Path expansion and escaping
        test('Hello %(title1)s', 'Hello $PATH')
        test('Hello %(title2)s', 'Hello %PATH%')
        test('%(title3)s', ('foo/bar\\test', 'foo_bar_test'))
        test('folder/%(title3)s', ('folder/foo/bar\\test', 'folder%sfoo_bar_test' % os.path.sep))

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
                with open(audiofile, 'wt') as f:
                    f.write('EXAMPLE')
                return [info['filepath']], info

        def run_pp(params, PP):
            with open(filename, 'wt') as f:
                f.write('EXAMPLE')
            ydl = YoutubeDL(params)
            ydl.add_post_processor(PP())
            ydl.post_process(filename, {'filepath': filename})

        run_pp({'keepvideo': True}, SimplePP)
        self.assertTrue(os.path.exists(filename), '%s doesn\'t exist' % filename)
        self.assertTrue(os.path.exists(audiofile), '%s doesn\'t exist' % audiofile)
        os.unlink(filename)
        os.unlink(audiofile)

        run_pp({'keepvideo': False}, SimplePP)
        self.assertFalse(os.path.exists(filename), '%s exists' % filename)
        self.assertTrue(os.path.exists(audiofile), '%s doesn\'t exist' % audiofile)
        os.unlink(audiofile)

        class ModifierPP(PostProcessor):
            def run(self, info):
                with open(info['filepath'], 'wt') as f:
                    f.write('MODIFIED')
                return [], info

        run_pp({'keepvideo': False}, ModifierPP)
        self.assertTrue(os.path.exists(filename), '%s doesn\'t exist' % filename)
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
            'uploader': "變態妍字幕版 太妍 тест",
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
            'uploader': "тест 123",
            'webpage_url': 'http://example.com/watch?v=SHENANIGANS',
        }
        videos = [first, second]

        def get_videos(filter_=None):
            ydl = YDL({'match_filter': filter_, 'simulate': True})
            for v in videos:
                ydl.process_ie_result(v, download=True)
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
        entries = [{
            'id': compat_str(i),
            'title': compat_str(i),
            'url': TEST_URL,
        } for i in range(1, 5)]
        playlist = {
            '_type': 'playlist',
            'id': 'test',
            'entries': entries,
            'extractor': 'test:playlist',
            'extractor_key': 'test:playlist',
            'webpage_url': 'http://example.com',
        }

        def get_downloaded_info_dicts(params):
            ydl = YDL(params)
            # make a deep copy because the dictionary and nested entries
            # can be modified
            ydl.process_ie_result(copy.deepcopy(playlist))
            return ydl.downloaded_info_dicts

        def test_selection(params, expected_ids):
            results = [
                (v['playlist_autonumber'] - 1, (int(v['id']), v['playlist_index']))
                for v in get_downloaded_info_dicts(params)]
            self.assertEqual(results, list(enumerate(zip(expected_ids, expected_ids))))

        test_selection({}, [1, 2, 3, 4])
        test_selection({'playlistend': 10}, [1, 2, 3, 4])
        test_selection({'playlistend': 2}, [1, 2])
        test_selection({'playliststart': 10}, [])
        test_selection({'playliststart': 2}, [2, 3, 4])
        test_selection({'playlist_items': '2-4'}, [2, 3, 4])
        test_selection({'playlist_items': '2,4'}, [2, 4])
        test_selection({'playlist_items': '10'}, [])
        test_selection({'playlist_items': '0'}, [])

        # Tests for https://github.com/ytdl-org/youtube-dl/issues/10591
        test_selection({'playlist_items': '2-4,3-4,3'}, [2, 3, 4])
        test_selection({'playlist_items': '4,2'}, [4, 2])

        # Tests for https://github.com/yt-dlp/yt-dlp/issues/720
        # https://github.com/yt-dlp/yt-dlp/issues/302
        test_selection({'playlistreverse': True}, [4, 3, 2, 1])
        test_selection({'playliststart': 2, 'playlistreverse': True}, [4, 3, 2])
        test_selection({'playlist_items': '2,4', 'playlistreverse': True}, [4, 2])
        test_selection({'playlist_items': '4,2'}, [4, 2])

    def test_urlopen_no_file_protocol(self):
        # see https://github.com/ytdl-org/youtube-dl/issues/8227
        ydl = YDL()
        self.assertRaises(compat_urllib_error.URLError, ydl.urlopen, 'file:///etc/passwd')

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
                    'title': 'Video %s' % video_id,
                    'formats': formats,
                }

        class PlaylistIE(InfoExtractor):
            _VALID_URL = r'playlist:'

            def _entries(self):
                for n in range(3):
                    video_id = compat_str(n)
                    yield {
                        '_type': 'url_transparent',
                        'ie_key': VideoIE.ie_key(),
                        'id': video_id,
                        'url': 'video:%s' % video_id,
                        'title': 'Video Transparent %s' % video_id,
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


if __name__ == '__main__':
    unittest.main()
