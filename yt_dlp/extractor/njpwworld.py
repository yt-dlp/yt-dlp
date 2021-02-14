# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_urlparse
from ..utils import (
    get_element_by_class,
    urlencode_postdata,
)


class NJPWWorldIE(InfoExtractor):
    _VALID_URL = r'https?://(front\.)?njpwworld\.com/p/(?P<id>[a-z0-9_]+)'
    IE_DESC = '新日本プロレスワールド'
    _NETRC_MACHINE = 'njpwworld'

    _TESTS = [{
        'url': 'http://njpwworld.com/p/s_series_00155_1_9/',
        'info_dict': {
            'id': 's_series_00155_1_9',
            'ext': 'mp4',
            'title': '闘強導夢2000 2000年1月4日 東京ドーム 第9試合 ランディ・サベージ VS リック・スタイナー',
            'tags': list,
        },
        'params': {
            'skip_download': True,  # AES-encrypted m3u8
        },
        'skip': 'Requires login',
    }, {
        'url': 'https://front.njpwworld.com/p/s_series_00563_16_bs',
        'info_dict': {
            'id': 's_series_00563_16_bs',
            'ext': 'mp4',
            'title': 'WORLD TAG LEAGUE 2020 & BEST OF THE SUPER Jr.27 2020年12月6日 福岡・福岡国際センター バックステージコメント（字幕あり）',
            'tags': ["福岡・福岡国際センター", "バックステージコメント", "2020", "20年代"],
        },
        'params': {
            'skip_download': True,
        },
    }]

    _LOGIN_URL = 'https://front.njpwworld.com/auth/login'

    def _real_initialize(self):
        self._login()

    def _login(self):
        username, password = self._get_login_info()
        # No authentication to be performed
        if not username:
            return True

        # Setup session (will set necessary cookies)
        self._request_webpage(
            'https://njpwworld.com/', None, note='Setting up session')

        webpage, urlh = self._download_webpage_handle(
            self._LOGIN_URL, None,
            note='Logging in', errnote='Unable to login',
            data=urlencode_postdata({'login_id': username, 'pw': password}),
            headers={'Referer': 'https://front.njpwworld.com/auth'})
        # /auth/login will return 302 for successful logins
        if urlh.geturl() == self._LOGIN_URL:
            self.report_warning('unable to login')
            return False

        return True

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        formats = []
        for kind, vid in re.findall(r'if\s+\(\s*imageQualityType\s*==\s*\'([^\']+)\'\s*\)\s*{\s*video_id\s*=\s*"(\d+)"', webpage):
            player_path = '/intent?id=%s&type=url' % vid
            player_url = compat_urlparse.urljoin(url, player_path)
            formats.append({
                'url': player_url,
                'format_id': kind,
                'ext': 'mp4',
                'protocol': 'm3u8',
                'quality': 2 if kind == 'high' else 1,
            })

        self._sort_formats(formats)

        tag_block = get_element_by_class('tag-block', webpage)
        tags = re.findall(
            r'<a[^>]+class="tag-[^"]+"[^>]*>([^<]+)</a>', tag_block
        ) if tag_block else None

        return {
            'id': video_id,
            'title': get_element_by_class('article-title', webpage) or self._og_search_title(webpage),
            'formats': formats,
            'tags': tags,
        }
