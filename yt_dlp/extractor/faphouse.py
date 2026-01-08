import itertools
import re

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    str_or_none,
)
from ..utils.traversal import traverse_obj


class FaphouseIE(InfoExtractor):
    _VALID_URL = r'https://?faphouse\.com/videos/(?P<id>[^#?&]+)'
    IE_NAME = 'faphouse'
    _TESTS = [{
        'url': 'https://faphouse.com/videos/pegged-milked-Yd1x34#dmVwPU1haW4gcGFnZSZ2ZWI9Rmlyc3QgNjAgb24gbWFpbg==',
        'info_dict': {
            'id': 'pegged-milked-Yd1x34',
            'ext': 'mp4',
            'title': 'Pegged and Milked',
            'description': 'md5:5e0b2e6b39ffe437d16a3d1be463556c',
            'thumbnail': r're:https://?[^.]+\.flixcdn\.com/[^#?&]+',
            'age_limit': 18,
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://faphouse.com/videos/zDUKkr',
        'info_dict': {
            'id': 'zDUKkr',
            'ext': 'mp4',
            'title': 'Ball Busted and Jerked off',
            'description': 'md5:821c28e78392bc7683637f615b51113a',
            'thumbnail': r're:https://?[^.]+\.flixcdn\.com/[^#?&]+',
            'age_limit': 18,
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://faphouse.com/videos/zDUKkr#dmVwPVZpZGVvIHBhZ2UmdmViPVJlbGF0ZWQmcmVsYXRlZF90eXBlPW1s',
        'only_matching': True,
    }]

    def _parse_formats(self, video_id, webpage):
        common_qualites = {360: 640, 480: 854, 720: 1280}
        formats = []
        trailer_block = self._search_regex(
            r'(<video\s*id="video-trailer"[^>]+>)',
            webpage, 'trailer', default=None)
        video_block = self._search_regex(
            r'(<div\s*class="video__player"[^>]+>)',
            webpage, 'video url', default=None)
        if msg := self._search_regex(
                r'<span\s*class="\w+-purchase[^"]+">(\s*Streaming[\s\S]+?)<\/span>', webpage, 'msg', default=None):
            msg = msg if '<br' not in msg.strip() else msg.strip().replace('<br />', ' ')
            self.to_screen(msg)

        if trailer_block:
            trailer_json = extract_attributes(trailer_block)
            trailer_url = traverse_obj(trailer_json, ('src'), ('data-fallback'))
            trailer_path = self._search_regex(
                r'(https://?[^/]+/[^.]+)/',
                trailer_url, 'trailer path', default=None)
            for height, width in common_qualites.items():
                formats.append({
                    'format_id': f'Trailer-{height}',
                    'url': f'{trailer_path}/{height}.mp4',
                    'height': height,
                    'width': width,
                })
        if video_block:
            video_json = extract_attributes(video_block)
            if hls_url := video_json.get('data-el-hls-url'):
                formats.extend(self._extract_m3u8_formats(hls_url, video_id))
            elif video_json.get('data-el-formats'):
                for q, url in video_json.get('data-el-formats'):
                    formats.append({
                        'url': url,
                        'height': q,
                        'width': self.COMMON_QTY.get(q) or 0,
                    })
        return formats

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        return {
            'id': video_id,
            'title': self._og_search_title(webpage, default=''),
            'description': self._og_search_description(webpage, default=''),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'formats': self._parse_formats(video_id, webpage),
            'age_limit': 18,
        }


class FaphouseUserIE(InfoExtractor):
    _VALID_URL = r'https://?faphouse\.com/(?P<type>models|pornstars|studios)/(?P<id>[^/?#]+)'
    IE_NAME = 'faphouse:user'
    _TESTS = [{
        'url': 'https://faphouse.com/pornstars/sofia-moon',
        'info_dict': {
            'id': 'sofia-moon',
            'title': 'sofia-moon',
        },
        'playlist_count': 4,
    }, {
        'url': 'https://faphouse.com/models/vincemayvideo',
        'info_dict': {
            'id': 'vincemayvideo',
            'title': 'vincemayvideo',
        },
        'playlist_count': 69,
    }, {
        'url': 'https://faphouse.com/studios/family-strokes',
        'info_dict': {
            'id': 'family-strokes',
            'title': 'family-strokes',
        },
        'playlist_count': 353,
    }]

    def _entries(self, prefix, username):
        next_page_path = f'/{prefix}/{username}'
        next_page_url = f'https://faphouse.com{next_page_path}'
        seen_paths = set()
        for pagenum in itertools.count(1):
            page = self._download_webpage(
                next_page_url, username, note=f'Downloading page {pagenum}')
            for video_tag in re.findall(r'(<a\s+class="t-vl"[^>]+#[^>]+>)', page):
                video_path = extract_attributes(video_tag).get('href')
                if video_path in seen_paths or video_path is None:
                    continue
                seen_paths.add(video_path)
                yield self.url_result(f'https://faphouse.com{video_path}', FaphouseIE.ie_key(), username)
            next_page = self._search_regex(r'(<a[^>]+data-page=["\'][^>]+>\s*[^>]+>\s*Next[^>]+>)', page, 'next_page', default=None)
            if not next_page:
                break
            next_page = extract_attributes(next_page)
            next_page_path = str_or_none(next_page.get('href'))
            if not next_page_path:
                break
            next_page_url = f'https://faphouse.com{next_page_path}'

    def _real_extract(self, url):
        username, prefix = self._match_valid_url(url).group('id', 'type')
        return self.playlist_result(self._entries(prefix, username), username, username)
