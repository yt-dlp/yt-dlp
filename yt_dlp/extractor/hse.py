# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    try_get,
    unified_timestamp,
)


class HSEShowIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?hse\.de/dpl/c/tv-shows/(?P<id>[0-9]+)'
    _GEO_COUNTRIES = ['DE']
    _TESTS = [{
        'url': 'https://www.hse.de/dpl/c/tv-shows/505350',
        'info_dict': {
            'id': '505350',
            'ext': 'mp4',
            'title': 'Pfeffinger Mode & Accessoires',
            'timestamp': 1638810000,
            'upload_date': '20211206',
            'channel': 'HSE24',
            'uploader': 'Arina Pirayesh'
        },
        'params': {
            'skip_download': True,
        },
    },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        json_str = self._html_search_regex(r'window\.__REDUX_DATA__ = ({.*});?', webpage, 'json_str')
        json_str = json_str.replace('\n', '')
        json_data = self._parse_json(json_str, video_id)

        if not try_get(json_data, lambda x: x['tvShowPage']['tvShowVideo']['sources']):
            raise ExtractorError('No show or video found', expected=True)

        page = json_data['tvShowPage']
        video = page['tvShowVideo']
        formats = []
        subtitles = {}
        for src in video['sources']:
            if src['mimetype'] == 'application/x-mpegURL':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(src['url'], video_id, ext='mp4')
                formats.extend(fmts)
                subtitles = self._merge_subtitles(subtitles, subs)
        self._sort_formats(formats)

        show = try_get(page, lambda x: x['tvShow'])
        date = try_get(show, lambda x: x['date'])
        hour = try_get(show, lambda x: x['hour'])

        return {
            'id': video_id,
            'title': try_get(show, lambda x: x['title']),
            'formats': formats,
            'timestamp': unified_timestamp(f'{date} {hour}:00'),
            'thumbnail': try_get(video, lambda x: x['poster']),
            'channel': self._search_regex(r'tvShow \| ([A-Z0-9]+)_', try_get(show, lambda x: x['actionFieldText']), video_id),
            'uploader': try_get(show, lambda x: x['presenter']),
            'subtitles': subtitles,
        }


class HSEProductIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?hse\.de/dpl/p/product/(?P<id>[0-9]+)'
    _GEO_COUNTRIES = ['DE']
    _TESTS = [{
        'url': 'https://www.hse.de/dpl/p/product/408630',
        'info_dict': {
            'id': '408630',
            'ext': 'mp4',
            'title': 'Hose im Ponte-Mix',
            'uploader': 'Judith Williams'
        },
        'params': {
            'skip_download': True,
        },
    },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        json_str = self._html_search_regex(r'window\.__REDUX_DATA__ = ({.*});?', webpage, 'json_str')
        json_str = json_str.replace('\n', '')
        json_data = self._parse_json(json_str, video_id)

        if not try_get(json_data, lambda x: x['productContent']['productContent']['videos']):
            raise ExtractorError('No product or video found', expected=True)

        formats = []
        subtitles = {}
        for video in json_data['productContent']['productContent']['videos']:
            thumbnail = video['poster']
            sources = video['sources']
            for src in sources:
                if src['mimetype'] == 'application/x-mpegURL':
                    fmts, subs = self._extract_m3u8_formats_and_subtitles(src['url'], video_id, ext='mp4')
                    formats.extend(fmts)
                    subtitles = self._merge_subtitles(subtitles, subs)

        self._sort_formats(formats)

        product = try_get(json_data, lambda x: x['productDetail']['product'])

        return {
            'id': video_id,
            'title': try_get(product, lambda x: x['name']['short']),
            'formats': formats,
            'thumbnail': thumbnail,
            'uploader': try_get(product, lambda x: x['brand']['brandName']),
            'subtitles': subtitles,
        }
