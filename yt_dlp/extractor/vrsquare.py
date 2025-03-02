import itertools

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    clean_html,
    extract_attributes,
    filter_dict,
    parse_duration,
    parse_qs,
    try_get,
)
from ..utils.traversal import (
    find_element,
    find_elements,
    traverse_obj,
)


class VRSQUAREIE(InfoExtractor):
    IE_NAME = 'vrsquare'
    IE_DESC = 'VR SQUARE'

    _VALID_URL = r'https?://livr\.jp/contents/(?P<id>[\w-]+)'
    _BASE_URL = 'https://livr.jp'
    _TESTS = [{
        'url': 'https://livr.jp/contents/P470896661',
        'info_dict': {
            'id': 'P470896661',
            'ext': 'mp4',
            'title': 'そこ曲がったら、櫻坂？ ７年間お疲れ様！菅井友香の卒業を祝う会！前半 2022年11月6日放送分',
            'description': 'md5:523726dc835aa8014dfe1e2b38d36cd1',
            'duration': 1515.0,
            'tags': list,
            'thumbnail': 're:^https?://media.livr.jp/vod/img/.*$',
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
            'thumbnail': 're:^https?://media.livr.jp/vod/img/.*$',
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
            'thumbnail': 're:^https?://media.livr.jp/vod/img/.*$',
        },
        'skip': 'Premium channel subscribers only',
    }, {
        # Accessible only in the VR SQUARE app
        'url': 'https://livr.jp/contents/P126481458',
        'only_matching': True,
    }]

    def _real_initialize(self):
        VRSQUAREIE._HEADERS = {
            'cookie': try_get(self._get_cookies(self._BASE_URL), lambda x: f'uh={x["uh"].value}') or '',
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        status = self._download_json(
            f'{self._BASE_URL}/webApi/contentsStatus/{video_id}',
            video_id, 'Checking contents status', headers=self._HEADERS)
        if isinstance(status, dict):
            self.raise_login_required('Unable to access this video')

        try:
            webApi = self._download_json(
                f'{self._BASE_URL}/webApi/play/url/{video_id}', video_id, headers=self._HEADERS)
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 500:
                raise ExtractorError('VR SQUARE app-only videos are not supported', expected=True)

        return {
            'id': video_id,
            'title': self._html_search_meta(['og:title', 'twitter:title'], webpage),
            'description': self._html_search_meta('description', webpage),
            'formats': self._extract_m3u8_formats(traverse_obj(webApi, (
                'urls', ..., 'url', any)), video_id, 'mp4', fatal=False),
            'thumbnail': self._html_search_meta('og:image', webpage),
            **traverse_obj(webpage, {
                'duration': ({find_element(cls='layout-product-data-time')}, {parse_duration}),
                'tags': ({find_elements(cls='search-tag')}, ..., {clean_html}),
            }),
        }


class VRSQUAREPlaylistIE(VRSQUAREIE):
    IE_NAME = 'vrsquare:playlist'

    _VALID_URL = r'https?://livr\.jp/(?P<type>category|channel|headline|web-search)/?(?P<id>(?!top\b)[\w-]+)?'
    _TESTS = [{
        'url': 'https://livr.jp/category/C133936275',
        'info_dict': {
            'id': 'C133936275',
            'title': 'そこ曲がったら、櫻坂？VR',
        },
        'playlist_mincount': 308,
    }, {
        'url': 'https://livr.jp/channel/H372648599',
        'info_dict': {
            'id': 'H372648599',
            'title': 'AKB48＋チャンネル',
        },
        'playlist_mincount': 499,
    }, {
        'url': 'https://livr.jp/headline/A296449604',
        'info_dict': {
            'id': 'A296449604',
            'title': 'AKB48 アフターVR',
        },
        'playlist_mincount': 22,
    }, {
        'url': 'https://livr.jp/web-search?w=%23%E5%B0%8F%E6%A0%97%E6%9C%89%E4%BB%A5',
        'info_dict': {
            'id': '#小栗有以',
            'title': '#小栗有以',
        },
        'playlist_mincount': 70,
    }]

    def _fetch_vids(self, source, keys=()):
        return [self.url_result(
            f'{self._BASE_URL}/contents/{x.removeprefix("/contents/")}', VRSQUAREIE)
            for x in traverse_obj(source, (
                *keys, {find_elements(cls='video', html=True)},
                ..., {extract_attributes}, 'data-url'))
        ]

    def _entries(self, webpage, playlist_type, playlist_id, query):
        if playlist_type in ('category', 'headline'):
            yield from self._fetch_vids(webpage)
        else:
            endpoint = {
                'channel': f'channel/{playlist_id}',
                'web-search': 'web-search',
            }[playlist_type]
            for page in itertools.count(1):
                ajax = self._download_json(
                    f'{self._BASE_URL}/ajax/{endpoint}', playlist_id,
                    query=filter_dict({'p': page, 'w': query}),
                )
                yield from self._fetch_vids(ajax, ('contents_render_list', ...))
                if not any(ajax.get(k) for k in ('has_next', 'hasNext')):
                    break

    def _real_extract(self, url):
        playlist_type, playlist_id = self._match_valid_url(url).groups()
        query = parse_qs(url).get('w', [None])[0]
        if not playlist_id:
            playlist_id = query
        webpage = self._download_webpage(url, playlist_id)
        playlist_title = query or self._html_search_meta('og:title', webpage)

        return self.playlist_result(
            self._entries(webpage, playlist_type, playlist_id, query), playlist_id, playlist_title)
