import itertools

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    clean_html,
    extract_attributes,
    parse_duration,
    parse_qs,
)
from ..utils.traversal import (
    find_element,
    find_elements,
    traverse_obj,
)


class VrSquareIE(InfoExtractor):
    IE_NAME = 'vrsquare'
    IE_DESC = 'VR SQUARE'

    _BASE_URL = 'https://livr.jp'
    _VALID_URL = r'https?://livr\.jp/contents/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://livr.jp/contents/P470896661',
        'info_dict': {
            'id': 'P470896661',
            'ext': 'mp4',
            'title': 'そこ曲がったら、櫻坂？ ７年間お疲れ様！菅井友香の卒業を祝う会！前半 2022年11月6日放送分',
            'description': 'md5:523726dc835aa8014dfe1e2b38d36cd1',
            'duration': 1515.0,
            'tags': 'count:2',
            'thumbnail': r're:https?://media\.livr\.jp/vod/img/.+\.jpg',
        },
    }, {
        'url': 'https://livr.jp/contents/P589523973',
        'info_dict': {
            'id': 'P589523973',
            'ext': 'mp4',
            'title': '薄闇に仰ぐ しだれ桜の妖艶',
            'description': 'md5:a042f517b2cbb4ed6746707afec4d306',
            'duration': 1084.0,
            'tags': list,
            'thumbnail': r're:https?://media\.livr\.jp/vod/img/.+\.jpg',
        },
        'skip': 'Paid video',
    }, {
        'url': 'https://livr.jp/contents/P316939908',
        'info_dict': {
            'id': 'P316939908',
            'ext': 'mp4',
            'title': '2024年5月16日（木） 「今日は誰に恋をする？」公演 小栗有以 生誕祭',
            'description': 'md5:2110bdcf947f28bd7d06ec420e51b619',
            'duration': 8559.0,
            'tags': list,
            'thumbnail': r're:https?://media\.livr\.jp/vod/img/.+\.jpg',
        },
        'skip': 'Premium channel subscribers only',
    }, {
        # Accessible only in the VR SQUARE app
        'url': 'https://livr.jp/contents/P126481458',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        status = self._download_json(
            f'{self._BASE_URL}/webApi/contentsStatus/{video_id}',
            video_id, 'Checking contents status', fatal=False)
        if traverse_obj(status, 'result_code') == '40407':
            self.raise_login_required('Unable to access this video')

        try:
            web_api = self._download_json(
                f'{self._BASE_URL}/webApi/play/url/{video_id}', video_id)
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 500:
                raise ExtractorError('VR SQUARE app-only videos are not supported', expected=True)
            raise

        return {
            'id': video_id,
            'title': self._html_search_meta(['og:title', 'twitter:title'], webpage),
            'description': self._html_search_meta('description', webpage),
            'formats': self._extract_m3u8_formats(traverse_obj(web_api, (
                'urls', ..., 'url', any)), video_id, 'mp4', fatal=False),
            'thumbnail': self._html_search_meta('og:image', webpage),
            **traverse_obj(webpage, {
                'duration': ({find_element(cls='layout-product-data-time')}, {parse_duration}),
                'tags': ({find_elements(cls='search-tag')}, ..., {clean_html}),
            }),
        }


class VrSquarePlaylistBaseIE(InfoExtractor):
    _BASE_URL = 'https://livr.jp'

    def _fetch_vids(self, source, keys=()):
        for url_path in traverse_obj(source, (
            *keys, {find_elements(cls='video', html=True)}, ...,
            {extract_attributes}, 'data-url', {str}, filter),
        ):
            yield self.url_result(
                f'{self._BASE_URL}/contents/{url_path.removeprefix("/contents/")}', VrSquareIE)

    def _entries(self, path, display_id, query=None):
        for page in itertools.count(1):
            ajax = self._download_json(
                f'{self._BASE_URL}{path}', display_id,
                f'Downloading playlist JSON page {page}',
                query={'p': page, **(query or {})})
            yield from self._fetch_vids(ajax, ('contents_render_list', ...))
            if not traverse_obj(ajax, (('has_next', 'hasNext'), {bool}, any)):
                break


class VrSquareChannelIE(VrSquarePlaylistBaseIE):
    IE_NAME = 'vrsquare:channel'

    _VALID_URL = r'https?://livr\.jp/channel/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://livr.jp/channel/H372648599',
        'info_dict': {
            'id': 'H372648599',
            'title': 'AKB48＋チャンネル',
        },
        'playlist_mincount': 502,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)

        return self.playlist_result(
            self._entries(f'/ajax/channel/{playlist_id}', playlist_id),
            playlist_id, self._html_search_meta('og:title', webpage))


class VrSquareSearchIE(VrSquarePlaylistBaseIE):
    IE_NAME = 'vrsquare:search'

    _VALID_URL = r'https?://livr\.jp/web-search/?\?(?:[^#]+&)?w=[^#]+'
    _TESTS = [{
        'url': 'https://livr.jp/web-search?w=%23%E5%B0%8F%E6%A0%97%E6%9C%89%E4%BB%A5',
        'info_dict': {
            'id': '#小栗有以',
        },
        'playlist_mincount': 60,
    }]

    def _real_extract(self, url):
        search_query = parse_qs(url)['w'][0]

        return self.playlist_result(
            self._entries('/ajax/web-search', search_query, {'w': search_query}), search_query)


class VrSquareSectionIE(VrSquarePlaylistBaseIE):
    IE_NAME = 'vrsquare:section'

    _VALID_URL = r'https?://livr\.jp/(?:category|headline)/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://livr.jp/category/C133936275',
        'info_dict': {
            'id': 'C133936275',
            'title': 'そこ曲がったら、櫻坂？VR',
        },
        'playlist_mincount': 308,
    }, {
        'url': 'https://livr.jp/headline/A296449604',
        'info_dict': {
            'id': 'A296449604',
            'title': 'AKB48 アフターVR',
        },
        'playlist_mincount': 22,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)

        return self.playlist_result(
            self._fetch_vids(webpage), playlist_id, self._html_search_meta('og:title', webpage))
