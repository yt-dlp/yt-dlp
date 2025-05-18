import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
    url_or_none,
    variadic,
)
from ..utils.traversal import traverse_obj


class DWIE(InfoExtractor):
    IE_NAME = 'dw'
    IE_DESC = 'Deutsche Welle'

    _VALID_URL = r'https?://(?:(?:amp|www)\.)?dw\.com/(?P<lang>[^/]+)/[^/]+/(?P<type>a(?:udio)?|live|program|video)-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.dw.com/en/intelligent-light/video-19112290',
        'info_dict': {
            'id': '19112290',
            'ext': 'mp4',
            'title': 'Intelligent light',
            'categories': ['Science'],
            'description': 'md5:90e00d5881719f2a6a5827cb74985af1',
            'duration': 194,
            'modified_date': '20160603',
            'modified_timestamp': 1464917222,
            'release_date': '20160605',
            'release_timestamp': 1465162200,
            'thumbnail': 'https://static.dw.com/image/18342580_605.webp',
        },
    }, {
        'url': 'https://www.dw.com/en/30-years-since-the-fall-of-the-berlin-wall-what-happened-to-the-euphoria/audio-51155232',
        'info_dict': {
            'id': '51155232',
            'ext': 'mp3',
            'title': '30 years since the fall of the Berlin Wall: What happened to the euphoria?',
            'categories': ['Politics'],
            'description': 'md5:ed0686725ef2d8fa5230aa8171b6476b',
            'duration': 1561,
            'release_date': '20191107',
            'release_timestamp': 1573140547,
            'thumbnail': 'https://static.dw.com/image/51151661_605.webp',
        },
    }, {
        'url': 'https://www.dw.com/en/10-years-since-higgs-boson-whats-next/a-62353123',
        'info_dict': {
            'id': '62353123',
            'title': '10 years since Higgs boson. What\'s next?',
        },
        'playlist_count': 1,
    }, {
        'url': 'https://www.dw.com/am/31-%E1%8B%93%E1%88%98%E1%89%B5-%E1%8A%A0%E1%8C%88%E1%88%8D%E1%8C%8D%E1%88%88%E1%8B%8D-%E1%8A%A8100-%E1%8B%B6%E1%88%8B%E1%88%AD-%E1%8B%AB%E1%8A%90%E1%88%B0-%E1%88%B6%E1%88%9B%E1%88%8A%E1%88%8B%E1%8A%95%E1%8B%B5-4%E1%88%BA%E1%88%85-%E1%8B%B6%E1%88%8B%E1%88%AD-%E1%8B%A8%E1%8B%88%E1%88%AD-%E1%8A%AD%E1%8D%8D%E1%8B%AB-%E1%8B%B6-%E1%88%AD-%E1%8D%8D%E1%88%B5%E1%88%83/a-72565331',
        'info_dict': {
            'id': '72565331',
            'title': 'md5:b01a937d9023dc9d6e96f0c30e86816e',
        },
        'playlist_count': 1,
    }, {
        'url': 'https://amp.dw.com/am/%E1%88%81%E1%88%88%E1%89%B5-%E1%8B%A8%E1%88%98%E1%8A%95%E1%8C%8D%E1%88%B5%E1%89%B5-%E1%8D%8B%E1%89%A5%E1%88%AA%E1%8A%AB%E1%8B%8E%E1%89%BD-%E1%8B%88%E1%8B%B0-%E1%8C%A5%E1%88%A8%E1%89%B5-%E1%88%8A%E1%8B%9B%E1%8B%88%E1%88%A9-%E1%8A%90%E1%8B%8D/a-37166407',
        'info_dict': {
            'id': '37166407',
            'title': 'md5:56fc6855d20de908fc5bd6cff226ddb4',
        },
        'playlist_count': 1,
    }, {
        'url': 'https://www.dw.com/en/0/live-72516011',
        'info_dict': {
            'id': '72516011',
            'title': 'Germany updates: Afghan family sues government — report',
        },
        'playlist_count': 5,
    }, {
        'url': 'https://www.dw.com/en/choices/program-68776240',
        'info_dict': {
            'id': '68776240',
            'title': 'CHOICES',
        },
        'playlist_count': 13,
    }]

    def _entries(self, url, graph_api, media_type):
        if path := {
            'a': 'videos',
            'live': ('posts', ..., 'videos'),
            'program': 'moreContentsFromUnifiedProgram',
        }.get(media_type):
            for dct in traverse_obj(graph_api, (
                *variadic(path), lambda _, v: v['namedUrl'] not in url,
            )):
                yield self.url_result(
                    f'https://www.dw.com{dct["namedUrl"]}', DWIE)

        if media_type == 'a':
            for dct in traverse_obj(graph_api, ('audios', lambda _, v: v['mp3Src'])):
                m3u8_url = traverse_obj(dct, 'mp3Src', {url_or_none})

                yield from [{
                    'id': m3u8_url.rpartition('/')[2].removesuffix('.mp3'),
                    'ext': 'mp3',
                    'title': dct.get('title'),
                    'url': m3u8_url,
                }]

    def _real_extract(self, url):
        lang, media_type, media_id = self._match_valid_url(url).groups()
        webpage = self._download_webpage(url, media_id)

        path = {
            'a': 'article',
            'audio': 'audio',
            'live': 'liveblog',
            'program': 'unified-program',
            'video': 'video',
        }[media_type]

        if not (app_state := self._search_json(
            r'window\.__APP_STATE__\s*=\s*', webpage, 'app state', media_id, default={},
        )):
            title = self._html_search_meta('twitter:title', webpage)
            pattern = re.compile(r'<source[^>]+src\s*=\s*(["\'])(?P<url>.+?)\1')
            entries = [{
                'id': m.group('url').rpartition('/')[2].removesuffix('.mp3'),
                'ext': 'mp3',
                'title': title,
                'url': m.group('url'),
            } for m in pattern.finditer(webpage)]

            return self.playlist_result(entries, media_id, title)
        else:
            graph_api = traverse_obj(app_state, (
                f'/graph-api/{lang}/content/{path}/{media_id}', 'data', 'content', {dict}))

            if media_type in {'a', 'live', 'program'}:
                return self.playlist_result(
                    self._entries(url, graph_api, media_type), media_id, graph_api.get('title'))
            elif media_type == 'audio':
                formats = [{
                    'ext': 'mp3',
                    'url': traverse_obj(graph_api, 'mp3Src', {url_or_none}),
                }]
            else:
                m3u8_url = traverse_obj(graph_api, 'hlsVideoSrc', {url_or_none})
                formats = self._extract_m3u8_formats(m3u8_url, media_id, 'mp4', m3u8_id='hls')

        return {
            'id': media_id,
            'formats': formats,
            **traverse_obj(graph_api, {
                'title': ('title', {str}),
                'categories': ('thematicFocusCategory', 'name', {str}, all, filter),
                'description': ('teaser', {str}),
                'duration': ('duration', {int_or_none}),
                'modified_timestamp': ('lastModifiedDate', {parse_iso8601}),
                'thumbnail': ('posterImageUrl', {url_or_none}),
                'release_timestamp': ('contentDate', {parse_iso8601}),
            }),
        }
