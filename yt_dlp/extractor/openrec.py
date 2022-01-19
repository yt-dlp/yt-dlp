# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    traverse_obj,
    unified_strdate,
    unified_timestamp
)
from ..compat import compat_str


class OpenRecBaseIE(InfoExtractor):
    def _extract_pagestore(self, webpage, video_id):
        return self._parse_json(
            self._search_regex(r'(?m)window\.pageStore\s*=\s*(\{.+?\});$', webpage, 'window.pageStore'), video_id)

    def _extract_movie(self, webpage, video_id, name, is_live):
        window_stores = self._extract_pagestore(webpage, video_id)
        movie_store = traverse_obj(
            window_stores,
            ('v8', 'state', 'movie'),
            ('v8', 'movie'),
            expected_type=dict)
        if not movie_store:
            raise ExtractorError(f'Failed to extract {name} info')

        title = movie_store.get('title')
        description = movie_store.get('introduction')
        thumbnail = movie_store.get('thumbnailUrl')

        uploader = traverse_obj(movie_store, ('channel', 'user', 'name'), expected_type=compat_str)
        uploader_id = traverse_obj(movie_store, ('channel', 'user', 'id'), expected_type=compat_str)

        timestamp = int_or_none(traverse_obj(movie_store, ('publishedAt', 'time')), scale=1000)

        m3u8_playlists = movie_store.get('media') or {}
        formats = []
        for name, m3u8_url in m3u8_playlists.items():
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
            'is_live': is_live,
        }


class OpenRecIE(OpenRecBaseIE):
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

        return self._extract_movie(webpage, video_id, 'live', True)


class OpenRecCaptureIE(OpenRecBaseIE):
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

        window_stores = self._extract_pagestore(webpage, video_id)
        movie_store = window_stores.get('movie')

        capture_data = window_stores.get('capture')
        if not capture_data:
            raise ExtractorError('Cannot extract title')
        title = capture_data.get('title')
        thumbnail = capture_data.get('thumbnailUrl')
        upload_date = unified_strdate(capture_data.get('createdAt'))

        uploader = traverse_obj(movie_store, ('channel', 'name'), expected_type=compat_str)
        uploader_id = traverse_obj(movie_store, ('channel', 'id'), expected_type=compat_str)

        timestamp = traverse_obj(movie_store, 'createdAt', expected_type=compat_str)
        timestamp = unified_timestamp(timestamp)

        formats = self._extract_m3u8_formats(
            capture_data.get('source'), video_id, ext='mp4')
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'formats': formats,
            'timestamp': timestamp,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'upload_date': upload_date,
        }


class OpenRecMovieIE(OpenRecBaseIE):
    IE_NAME = 'openrec:movie'
    _VALID_URL = r'https?://(?:www\.)?openrec\.tv/movie/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://www.openrec.tv/movie/nqz5xl5km8v',
        'info_dict': {
            'id': 'nqz5xl5km8v',
            'title': '限定コミュニティ(Discord)参加方法ご説明動画',
            'description': 'md5:ebd563e5f5b060cda2f02bf26b14d87f',
            'thumbnail': r're:https://.+',
            'uploader': 'タイキとカズヒロ',
            'uploader_id': 'taiki_to_kazuhiro',
            'timestamp': 1638856800,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage('https://www.openrec.tv/movie/%s' % video_id, video_id)

        return self._extract_movie(webpage, video_id, 'movie', False)
