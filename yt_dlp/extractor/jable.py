import re

from .common import InfoExtractor
from ..utils import (
    InAdvancePagedList,
    int_or_none,
    orderedSet,
    unified_strdate,
)


class JableIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?jable.tv/videos/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://jable.tv/videos/pppd-812/',
        'md5': 'f1537283a9bc073c31ff86ca35d9b2a6',
        'info_dict': {
            'id': 'pppd-812',
            'ext': 'mp4',
            'title': 'PPPD-812 只要表現好巨乳女教師吉根柚莉愛就獎勵學生們在白虎穴內射出精液',
            'description': 'md5:5b6d4199a854f62c5e56e26ccad19967',
            'thumbnail': r're:^https?://.*\.jpg$',
            'age_limit': 18,
            'like_count': int,
            'view_count': int,
        },
    }, {
        'url': 'https://jable.tv/videos/apak-220/',
        'md5': '71f9239d69ced58ab74a816908847cc1',
        'info_dict': {
            'id': 'apak-220',
            'ext': 'mp4',
            'title': 'md5:5c3861b7cf80112a6e2b70bccf170824',
            'description': '',
            'thumbnail': r're:^https?://.*\.jpg$',
            'age_limit': 18,
            'like_count': int,
            'view_count': int,
            'upload_date': '20220319',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        formats = self._extract_m3u8_formats(
            self._search_regex(r'var\s+hlsUrl\s*=\s*\'([^\']+)', webpage, 'hls_url'), video_id, 'mp4', m3u8_id='hls')

        return {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage, default=''),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'formats': formats,
            'age_limit': 18,
            'upload_date': unified_strdate(self._search_regex(
                r'class="inactive-color">\D+\s+(\d{4}-\d+-\d+)', webpage, 'upload_date', default=None)),
            'view_count': int_or_none(self._search_regex(
                r'#icon-eye"></use></svg>\n*<span class="mr-3">([\d ]+)',
                webpage, 'view_count', default='').replace(' ', '')),
            'like_count': int_or_none(self._search_regex(
                r'#icon-heart"></use></svg><span class="count">(\d+)', webpage, 'link_count', default=None)),
        }


class JablePlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?jable.tv/(?:categories|models|tags)/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://jable.tv/models/kaede-karen/',
        'info_dict': {
            'id': 'kaede-karen',
            'title': '楓カレン',
        },
        'playlist_count': 34,
    }, {
        'url': 'https://jable.tv/categories/roleplay/',
        'only_matching': True,
    }, {
        'url': 'https://jable.tv/tags/girl/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)

        def page_func(page_num):
            return [
                self.url_result(player_url, JableIE)
                for player_url in orderedSet(re.findall(
                    r'href="(https://jable.tv/videos/[\w-]+/?)"',
                    self._download_webpage(url, playlist_id, query={
                        'mode': 'async',
                        'from': page_num + 1,
                        'function': 'get_block',
                        'block_id': 'list_videos_common_videos_list',
                    }, note=f'Downloading page {page_num + 1}')))]

        return self.playlist_result(
            InAdvancePagedList(page_func, int_or_none(self._search_regex(
                r'from:(\d+)">[^<]+\s*&raquo;', webpage, 'last page number', default=1)), 24),
            playlist_id, self._search_regex(
                r'<h2 class="h3-md mb-1">([^<]+)', webpage, 'playlist title', default=None))
