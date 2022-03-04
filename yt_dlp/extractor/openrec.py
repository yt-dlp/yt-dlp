# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    traverse_obj,
    unified_strdate,
    unified_timestamp,
    variadic,
)
from ..compat import compat_str


class OpenRecBaseIE(InfoExtractor):
    def _extract_pagestore(self, webpage, video_id):
        return self._parse_json(
            self._search_regex(r'(?m)window\.pageStore\s*=\s*(\{.+?\});$', webpage, 'window.pageStore'), video_id)

    def _extract_movie(self, webpage, video_id, name, is_live):
        window_stores = self._extract_pagestore(webpage, video_id)
        movie_stores = [
            # extract all three important data (most of data are duplicated each other, but slightly different!)
            traverse_obj(window_stores, ('v8', 'state', 'movie'), expected_type=dict),
            traverse_obj(window_stores, ('v8', 'movie'), expected_type=dict),
            traverse_obj(window_stores, 'movieStore', expected_type=dict),
        ]
        if not any(movie_stores):
            raise ExtractorError(f'Failed to extract {name} info')

        def get_first(path):
            return traverse_obj(movie_stores, (..., *variadic(path)), get_all=False)

        m3u8_playlists = get_first('media') or {}
        formats = []
        for name, m3u8_url in m3u8_playlists.items():
            if not m3u8_url:
                continue
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, video_id, ext='mp4', live=is_live, m3u8_id=name))

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': get_first('title'),
            'description': get_first('introduction'),
            'thumbnail': get_first('thumbnailUrl'),
            'formats': formats,
            'uploader': get_first(('channel', 'user', 'name')),
            'uploader_id': get_first(('channel', 'user', 'id')),
            'timestamp': int_or_none(get_first(['publishedAt', 'time']), scale=1000) or unified_timestamp(get_first('publishedAt')),
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
        webpage = self._download_webpage(f'https://www.openrec.tv/live/{video_id}', video_id)

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
        webpage = self._download_webpage(url, video_id)

        window_stores = self._extract_pagestore(webpage, video_id)
        movie_store = window_stores.get('movie')

        capture_data = window_stores.get('capture')
        if not capture_data:
            raise ExtractorError('Cannot extract title')

        formats = self._extract_m3u8_formats(
            capture_data.get('source'), video_id, ext='mp4')
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': capture_data.get('title'),
            'thumbnail': capture_data.get('thumbnailUrl'),
            'formats': formats,
            'timestamp': unified_timestamp(traverse_obj(movie_store, 'createdAt', expected_type=compat_str)),
            'uploader': traverse_obj(movie_store, ('channel', 'name'), expected_type=compat_str),
            'uploader_id': traverse_obj(movie_store, ('channel', 'id'), expected_type=compat_str),
            'upload_date': unified_strdate(capture_data.get('createdAt')),
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
        webpage = self._download_webpage(f'https://www.openrec.tv/movie/{video_id}', video_id)

        return self._extract_movie(webpage, video_id, 'movie', False)
