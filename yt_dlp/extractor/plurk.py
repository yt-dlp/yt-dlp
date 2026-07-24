import functools
import re

from .common import ExtractorError, InfoExtractor, traverse_obj


class PlurkExtractorIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?plurk\.com/p/(?P<id>[0-9a-z]+)'
    _TESTS = [
        {
            'url': 'https://www.plurk.com/p/3i84keeuho',
            'md5': 'a608f427d2a5312445515f4db956df09',
            'info_dict': {
                'id': '3i84keeuho',
                'ext': 'mp4',
                'format_id': 're:hls-.*',

                'title': '功能更新 現在噗浪網頁和 App 最新版（iOS 7.20.0、Android 6.83.0），噗幣使用者可以上傳影片了！此功能目前為試營運中，相關使用說明下收留言區',
                'description': r're:Plurk by 噗浪技術部🛠 - \d+ response\(s\)',
                'uploader': '噗浪技術部🛠',
                'uploader_id': 'plurkwork',
                'uploader_url': 'https://www.plurk.com/plurkwork',
                'duration': 27,
                'thumbnail': 'https://video.plurk.com/4d64b1b5f43d46e0a1e5e0dcdc95d2b3/4d64b-thumbnail.0000000.jpg',
            },
        },
        {
            'url': 'https://www.plurk.com/p/3i64kdqlzy',
            'md5': 'ba5c23ac6b696c84aca502c809641c29',
            'info_dict': {
                'id': '3i64kdqlzy',
                'ext': 'mp4',
                'format_note': 'single',
                'title': '噗浪技術部🛠\'s Plurk',
                'description': r're:Plurk by 噗浪技術部🛠 - \d+ response\(s\)',
                'uploader': '噗浪技術部🛠',
                'uploader_id': 'plurkwork',
                'uploader_url': 'https://www.plurk.com/plurkwork',
                'duration': 10,
                'thumbnail': 'https://video.plurk.com/8836000bc037400c8ae3ae018e6e690c/88360-thumbnail.0000000.jpg',
            },

        },
    ]

    def _real_extract(self, url):
        unwrap_date = functools.partial(re.sub, r'new Date\(("[^"]+")\)', r'\1')

        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        plurk_info = self._search_json(
            r'<script[^>]*>\s*plurk\s*=', webpage, 'plurk_info', video_id, transform_source=unwrap_date)

        video_info = traverse_obj(plurk_info, ('videos', 0), expected_type=dict)
        if not video_info:
            raise ExtractorError('There\'s no video in this post')

        if 'token' not in video_info:
            raise ExtractorError('No token found')
        formats = self._extract_m3u8_formats(video_info.get('hls_url'), video_id, m3u8_id='hls',
                                             query={'verify': video_info['token']}, fatal=False)
        for ext in ('mov', 'mp4', 'webm'):
            if fmt := self._try_extract_single(ext, video_info):
                formats.append(fmt)
        if not formats:
            raise ExtractorError('No video format found')

        global_info = self._search_json(
            r'var GLOBAL\s*=', webpage, 'global_info', video_id, transform_source=unwrap_date, fatal=False)
        uploader_id = traverse_obj(global_info, ('page_user', 'nick_name'), expected_type=str)

        return {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'uploader': traverse_obj(global_info, ('page_user', 'display_name'), expected_type=str),
            'uploader_id': uploader_id,
            'uploader_url': uploader_id and f'https://www.plurk.com/{uploader_id}',
            'thumbnail': video_info.get('thumbnail'),
            'duration': video_info.get('duration'),
            'formats': formats,
        }

    def _try_extract_single(self, ext, info):
        url = info.get(f'{ext}_url')
        return url and {
            'url': url + '?verify=' + info['token'],
            'ext': ext,
            'width': info.get('width'),
            'height': info.get('height'),
            'format_note': 'single',
        }
