#!/usr/bin/env python3

# Allow direct execution
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from test.helper import FakeYDL
from yt_dlp.extractor.ceskatelevize import CeskaTelevizeIE
from yt_dlp.utils import ExtractorError


class TestCeskaTelevizeIE(unittest.TestCase):
    URL = 'https://www.ceskatelevize.cz/porady/1234-test-show/567890'
    WEBPAGE = '''
        <html>
            <head>
                <meta property="og:title" content="Test episode">
                <meta property="og:description" content="Episode description">
                <meta property="og:image" content="https://example.com/thumbnail.jpg">
            </head>
        </html>
    '''

    def setUp(self):
        self.ie = CeskaTelevizeIE(FakeYDL())

    def test_url_matching(self):
        self.assertTrue(self.ie.suitable(self.URL))
        self.assertTrue(self.ie.suitable('http://ceskatelevize.cz/porady/1234-test-show/567890'))
        self.assertFalse(self.ie.suitable('https://www.ceskatelevize.cz/porady/1234-test-show'))

    @mock.patch('yt_dlp.extractor.ceskatelevize.uuid.uuid4', return_value='test-device-id')
    def test_extracts_metadata_formats_and_subtitles(self, uuid4):
        api_data = {
            'stream': {
                'url': 'https://media.example.com/video.mpd?token=abc',
            },
            'subtitles': [{
                'url': 'https://media.example.com/subtitles.vtt',
            }],
        }
        extracted_formats = [{'format_id': 'dash-720p', 'url': 'https://media.example.com/video-720p.mp4'}]
        extracted_subtitles = {'en': [{'url': 'https://media.example.com/subtitles-en.vtt'}]}

        with (
            mock.patch.object(self.ie, '_download_webpage', return_value=self.WEBPAGE),
            mock.patch.object(self.ie, '_download_json', return_value=api_data) as download_json,
            mock.patch.object(
                self.ie, '_extract_mpd_formats_and_subtitles',
                return_value=(extracted_formats, extracted_subtitles),
            ) as extract_mpd,
        ):
            result = self.ie._real_extract(self.URL)

        uuid4.assert_called_once_with()
        download_json.assert_called_once()
        api_url = download_json.call_args.args[0]
        self.assertIn('/media/external/567890?', api_url)
        self.assertIn('canPlayDrm=true', api_url)
        self.assertIn('quality=web', api_url)
        self.assertIn('streamType=dash', api_url)
        self.assertIn('deviceId=test-device-id', api_url)
        self.assertIn('origin=ivysilani', api_url)
        self.assertIn('client=iVysilaniWeb', api_url)
        self.assertIn('clientVersion=0.37.8', api_url)
        self.assertEqual(download_json.call_args.kwargs['headers'], {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0',
        })
        extract_mpd.assert_called_once_with(
            api_data['stream']['url'], '567890', mpd_id='dash', fatal=False)
        self.assertEqual(result, {
            'id': '567890',
            'title': 'Test episode',
            'description': 'Episode description',
            'thumbnail': 'https://example.com/thumbnail.jpg',
            'formats': extracted_formats,
            'subtitles': {
                'en': extracted_subtitles['en'],
                'cs': [{'url': 'https://media.example.com/subtitles.vtt', 'ext': 'vtt'}],
            },
        })

    def test_raises_for_missing_stream(self):
        with (
            mock.patch.object(self.ie, '_download_webpage', return_value=self.WEBPAGE),
            mock.patch.object(self.ie, '_download_json', return_value={}),
        ):
            with self.assertRaisesRegex(ExtractorError, 'Could not find stream URL'):
                self.ie._real_extract(self.URL)

    @mock.patch('yt_dlp.extractor.ceskatelevize.uuid.uuid4', return_value='test-device-id')
    def test_uses_html_title_and_allows_missing_optional_metadata(self, _uuid4):
        webpage = '<html><head><title>Fallback title | Ceska televize</title></head></html>'
        api_data = {'streamUrl': 'https://media.example.com/video.mpd'}

        with (
            mock.patch.object(self.ie, '_download_webpage', return_value=webpage),
            mock.patch.object(self.ie, '_download_json', return_value=api_data),
            mock.patch.object(
                self.ie, '_extract_mpd_formats_and_subtitles',
                return_value=([{'format_id': 'dash'}], {}),
            ),
        ):
            result = self.ie._real_extract(self.URL)

        self.assertEqual(result['title'], 'Fallback title')
        self.assertIsNone(result['description'])
        self.assertIsNone(result['thumbnail'])
        self.assertEqual(result['subtitles'], {})

    def test_unescapes_api_urls(self):
        api_data = {'response': 'escaped URLs'}
        expected_stream_url = 'https://media.example.com/video.mpd?token=abc'
        expected_subtitle_url = 'https://media.example.com/subtitles.vtt'
        escaped_json = (
            r'{"streamUrl":"https:\/\/media.example.com\/video.mpd?token=abc",'
            r'"subtitleUrl":"https:\/\/media.example.com\/subtitles.vtt"}')

        with (
            mock.patch.object(self.ie, '_download_webpage', return_value=self.WEBPAGE),
            mock.patch.object(self.ie, '_download_json', return_value=api_data),
            mock.patch('yt_dlp.extractor.ceskatelevize.json.dumps', return_value=escaped_json),
            mock.patch.object(
                self.ie, '_extract_mpd_formats_and_subtitles',
                return_value=([], {}),
            ) as extract_mpd,
        ):
            result = self.ie._real_extract(self.URL)

        self.assertEqual(extract_mpd.call_args.args[0], expected_stream_url)
        self.assertEqual(result['subtitles'], {
            'cs': [{'url': expected_subtitle_url, 'ext': 'vtt'}],
        })

    @mock.patch('yt_dlp.extractor.ceskatelevize.uuid.uuid4', return_value='test-device-id')
    def test_defaults_title_to_video_id(self, _uuid4):
        api_data = {'stream': 'https://media.example.com/video.mpd?token=abc'}

        with (
            mock.patch.object(self.ie, '_download_webpage', return_value='<html></html>'),
            mock.patch.object(self.ie, '_download_json', return_value=api_data),
            mock.patch.object(
                self.ie, '_extract_mpd_formats_and_subtitles',
                return_value=([{'format_id': 'dash'}], {}),
            ),
        ):
            result = self.ie._real_extract(self.URL)

        self.assertEqual(result['title'], '567890')
        self.assertEqual(result['formats'], [{'format_id': 'dash'}])
        self.assertEqual(result['subtitles'], {})

    def test_selects_mpd_url_and_preserves_existing_cs_subtitles(self):
        api_data = {
            'thumbnail': 'https://media.example.com/poster.jpg',
            'stream': 'https://media.example.com/video.mpd',
            'subtitle': 'https://media.example.com/direct.vtt',
        }
        extracted_subtitles = {
            'cs': [{'url': 'https://media.example.com/manifest-cs.vtt'}],
        }

        with (
            mock.patch.object(self.ie, '_download_webpage', return_value=self.WEBPAGE),
            mock.patch.object(self.ie, '_download_json', return_value=api_data),
            mock.patch.object(
                self.ie, '_extract_mpd_formats_and_subtitles',
                return_value=([], extracted_subtitles),
            ) as extract_mpd,
        ):
            result = self.ie._real_extract(self.URL)

        extract_mpd.assert_called_once_with(
            'https://media.example.com/video.mpd', '567890', mpd_id='dash', fatal=False)
        self.assertEqual(result['subtitles']['cs'], [
            {'url': 'https://media.example.com/manifest-cs.vtt'},
            {'url': 'https://media.example.com/direct.vtt', 'ext': 'vtt'},
        ])


if __name__ == '__main__':
    unittest.main()
