# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    traverse_obj,
    try_get,
    unified_strdate
)
from ..compat import compat_str


class OpenRecIE(InfoExtractor):
    IE_NAME = 'openrec'
    _VALID_URL = r'https?://(?:www\.)?openrec\.tv/live/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://www.openrec.tv/live/2p8v31qe4zy',
        'only_matching': True,
    }, {
        'url': 'https://www.openrec.tv/live/wez93eqvjzl',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage('https://www.openrec.tv/live/%s' % video_id, video_id)

        window_stores = self._parse_json(
            self._search_regex(r'(?m)window\.pageStore\s*=\s*(\{.+?\});$', webpage, 'window.pageStore'), video_id)
        movie_store = traverse_obj(
            window_stores,
            ('v8', 'state', 'movie'),
            ('v8', 'movie'),
            expected_type=dict)
        if not movie_store:
            raise ExtractorError('Failed to extract live info')

        title = movie_store.get('title')
        description = movie_store.get('introduction')
        thumbnail = movie_store.get('thumbnailUrl')

        channel_user = movie_store.get('channel', {}).get('user')
        uploader = try_get(channel_user, lambda x: x['name'], compat_str)
        uploader_id = try_get(channel_user, lambda x: x['id'], compat_str)

        timestamp = traverse_obj(movie_store, ('startedAt', 'time'), expected_type=int)

        m3u8_playlists = movie_store.get('media')
        formats = []
        for (name, m3u8_url) in m3u8_playlists.items():
            if not m3u8_url:
                continue
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, video_id, ext='mp4', entry_protocol='m3u8',
                m3u8_id='hls-%s' % name, live=True))

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': formats,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'timestamp': timestamp,
            'is_live': True,
        }


class OpenRecCaptureIE(InfoExtractor):
    IE_NAME = 'openrec:capture'
    _VALID_URL = r'https?://(?:www\.)?openrec\.tv/capture/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://www.openrec.tv/capture/l9nk2x4gn14',
        'only_matching': True,
    }, {
        'url': 'https://www.openrec.tv/capture/mldjr82p7qk',
        'info_dict': {
            'id': 'mldjr82p7qk',
            'title': 'たいじの恥ずかしい英語力',
            'uploader': 'たいちゃんねる',
            'uploader_id': 'Yaritaiji',
            'upload_date': '20210803',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage('https://www.openrec.tv/capture/%s' % video_id, video_id)

        window_stores = self._parse_json(
            self._search_regex(r'(?m)window\.pageStore\s*=\s*(\{.+?\});$', webpage, 'window.pageStore'), video_id)
        movie_store = window_stores.get('movie')

        capture_data = window_stores.get('capture')
        if not capture_data:
            raise ExtractorError('Cannot extract title')
        title = capture_data.get('title')
        thumbnail = capture_data.get('thumbnailUrl')
        upload_date = unified_strdate(capture_data.get('createdAt'))

        channel_info = movie_store.get('channel') or {}
        uploader = channel_info.get('name')
        uploader_id = channel_info.get('id')

        m3u8_url = capture_data.get('source')
        if not m3u8_url:
            raise ExtractorError('Cannot extract m3u8 url')
        formats = self._extract_m3u8_formats(
            m3u8_url, video_id, ext='mp4', entry_protocol='m3u8_native',
            m3u8_id='hls')

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'formats': formats,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'upload_date': upload_date,
        }
