from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    ExtractorError,
    get_first,
    int_or_none,
    traverse_obj,
    try_get,
    unified_strdate,
    unified_timestamp,
)


class OpenRecBaseIE(InfoExtractor):
    _M3U8_HEADERS = {'Referer': 'https://www.openrec.tv/'}

    def _extract_pagestore(self, webpage, video_id):
        return self._parse_json(
            self._search_regex(r'(?m)window\.pageStore\s*=\s*(\{.+?\});$', webpage, 'window.pageStore'), video_id)

    def _expand_media(self, video_id, media):
        for name, m3u8_url in (media or {}).items():
            if not m3u8_url:
                continue
            yield from self._extract_m3u8_formats(
                m3u8_url, video_id, ext='mp4', m3u8_id=name, headers=self._M3U8_HEADERS)

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

        formats = list(self._expand_media(video_id, get_first(movie_stores, 'media')))
        if not formats:
            # archived livestreams or subscriber-only videos
            cookies = self._get_cookies('https://www.openrec.tv/')
            detail = self._download_json(
                f'https://apiv5.openrec.tv/api/v5/movies/{video_id}/detail', video_id,
                headers={
                    'Origin': 'https://www.openrec.tv',
                    'Referer': 'https://www.openrec.tv/',
                    'access-token': try_get(cookies, lambda x: x.get('access_token').value),
                    'uuid': try_get(cookies, lambda x: x.get('uuid').value),
                })
            new_media = traverse_obj(detail, ('data', 'items', ..., 'media'), get_all=False)
            formats = list(self._expand_media(video_id, new_media))
            is_live = False

        return {
            'id': video_id,
            'title': get_first(movie_stores, 'title'),
            'description': get_first(movie_stores, 'introduction'),
            'thumbnail': get_first(movie_stores, 'thumbnailUrl'),
            'formats': formats,
            'uploader': get_first(movie_stores, ('channel', 'user', 'name')),
            'uploader_id': get_first(movie_stores, ('channel', 'user', 'id')),
            'timestamp': int_or_none(get_first(movie_stores, ['publishedAt', 'time']), scale=1000) or unified_timestamp(get_first(movie_stores, 'publishedAt')),
            'is_live': is_live,
            'http_headers': self._M3U8_HEADERS,
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
        webpage = self._download_webpage(f'https://www.openrec.tv/capture/{video_id}', video_id)

        window_stores = self._extract_pagestore(webpage, video_id)
        movie_store = window_stores.get('movie')

        capture_data = window_stores.get('capture')
        if not capture_data:
            raise ExtractorError('Cannot extract title')

        formats = self._extract_m3u8_formats(
            capture_data.get('source'), video_id, ext='mp4', headers=self._M3U8_HEADERS)

        return {
            'id': video_id,
            'title': capture_data.get('title'),
            'thumbnail': capture_data.get('thumbnailUrl'),
            'formats': formats,
            'timestamp': unified_timestamp(traverse_obj(movie_store, 'createdAt', expected_type=compat_str)),
            'uploader': traverse_obj(movie_store, ('channel', 'name'), expected_type=compat_str),
            'uploader_id': traverse_obj(movie_store, ('channel', 'id'), expected_type=compat_str),
            'upload_date': unified_strdate(capture_data.get('createdAt')),
            'http_headers': self._M3U8_HEADERS,
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
