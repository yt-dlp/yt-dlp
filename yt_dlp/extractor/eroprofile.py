from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_urllib_parse_urlencode
from ..utils import (
    ExtractorError,
    merge_dicts,
)


class EroProfileIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?eroprofile\.com/m/videos/view/(?P<id>[^/]+)'
    _LOGIN_URL = 'http://www.eroprofile.com/auth/auth.php?'
    _NETRC_MACHINE = 'eroprofile'
    _TESTS = [{
        'url': 'http://www.eroprofile.com/m/videos/view/sexy-babe-softcore',
        'md5': 'c26f351332edf23e1ea28ce9ec9de32f',
        'info_dict': {
            'id': '3733775',
            'display_id': 'sexy-babe-softcore',
            'ext': 'm4v',
            'title': 'sexy babe softcore',
            'thumbnail': r're:https?://.*\.jpg',
            'age_limit': 18,
        },
        'skip': 'Video not found',
    }, {
        'url': 'http://www.eroprofile.com/m/videos/view/Try-It-On-Pee_cut_2-wmv-4shared-com-file-sharing-download-movie-file',
        'md5': '1baa9602ede46ce904c431f5418d8916',
        'info_dict': {
            'id': '1133519',
            'ext': 'm4v',
            'title': 'Try It On Pee_cut_2.wmv - 4shared.com - file sharing - download movie file',
            'thumbnail': r're:https?://.*\.jpg',
            'age_limit': 18,
        },
        'skip': 'Requires login',
    }]

    def _login(self):
        (username, password) = self._get_login_info()
        if username is None:
            return

        query = compat_urllib_parse_urlencode({
            'username': username,
            'password': password,
            'url': 'http://www.eroprofile.com/',
        })
        login_url = self._LOGIN_URL + query
        login_page = self._download_webpage(login_url, None, False)

        m = re.search(r'Your username or password was incorrect\.', login_page)
        if m:
            raise ExtractorError(
                'Wrong username and/or password.', expected=True)

        self.report_login()
        redirect_url = self._search_regex(
            r'<script[^>]+?src="([^"]+)"', login_page, 'login redirect url')
        self._download_webpage(redirect_url, None, False)

    def _real_initialize(self):
        self._login()

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        m = re.search(r'You must be logged in to view this video\.', webpage)
        if m:
            self.raise_login_required('This video requires login')

        video_id = self._search_regex(
            [r"glbUpdViews\s*\('\d*','(\d+)'", r'p/report/video/(\d+)'],
            webpage, 'video id', default=None)

        title = self._html_search_regex(
            (r'Title:</th><td>([^<]+)</td>', r'<h1[^>]*>(.+?)</h1>'),
            webpage, 'title')

        info = self._parse_html5_media_entries(url, webpage, video_id)[0]

        return merge_dicts(info, {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'age_limit': 18,
        })
