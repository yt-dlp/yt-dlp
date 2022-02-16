# coding: utf-8

from __future__ import unicode_literals
from .common import InfoExtractor
from ..compat import compat_urlparse
from ..utils import int_or_none, parse_duration, parse_filesize, unified_timestamp, urlencode_postdata, ExtractorError


class PiaproIE(InfoExtractor):
    _NETRC_MACHINE = 'piapro'
    _VALID_URL = r'https?://piapro\.jp/t/(?P<id>\w+)/?'
    _TESTS = [{
        'url': 'https://piapro.jp/t/NXYR',
        'md5': 'a9d52f27d13bafab7ee34116a7dcfa77',
        'info_dict': {
            'id': 'NXYR',
            'ext': 'mp3',
            'uploader': 'wowaka',
            'uploader_id': 'wowaka',
            'title': '裏表ラバーズ',
            'thumbnail': r're:^https?://.*\.jpg$',
        }
    }]

    def _real_initialize(self):
        self._login_status = self._login()

    def _login(self):
        username, password = self._get_login_info()
        if not username:
            return False
        login_ok = True
        login_form_strs = {
            '_username': username,
            '_password': password,
            '_remember_me': 'on',
            'login': 'ログイン'
        }
        self._request_webpage('https://piapro.jp/login/', None)
        urlh = self._request_webpage(
            'https://piapro.jp/login/exe', None,
            note='Logging in', errnote='Unable to log in',
            data=urlencode_postdata(login_form_strs))
        if urlh is False:
            login_ok = False
        else:
            parts = compat_urlparse.urlparse(urlh.geturl())
            if parts.path != '/':
                login_ok = False
        if not login_ok:
            self._downloader.report_warning(
                'unable to log in: bad username or password')
        return login_ok

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        category_id = self._search_regex(r'categoryId=(.+)">', webpage, 'category ID')
        if category_id not in ('1', '2', '21', '22', '23', '24', '25'):
            raise ExtractorError('The URL does not contain audio.', expected=True)

        title = self._html_search_regex(r'<h1\s+class="cd_works-title">(.+?)</h1>', webpage, 'title')
        description = self._html_search_regex(r'<p\s+class="cd_dtl_cap">(.+?)</p>\s*<div', webpage, 'description')

        str_duration, str_filesize = self._search_regex(
            r'サイズ：</span>(.+?)/\(([0-9,]+?[KMG]?B)）', webpage, 'duration and size',
            group=(1, 2))
        str_viewcount = self._search_regex(r'閲覧数：</span>([0-9,]+)\s+', webpage, 'view count')

        str_filesize = str_filesize.replace(',', '')
        str_viewcount = str_viewcount.replace(',', '')

        duration = parse_duration(str_duration)
        # this isn't accurate actually
        fs_approx = parse_filesize(str_filesize)
        view_count = int_or_none(str_viewcount)

        uploader_id, uploader = self._search_regex(
            r'<a\s+class="cd_user-name"\s+href="/(.*)">([^<]+)さん<', webpage, 'uploader',
            group=(1, 2))
        content_id = self._search_regex(r'contentId\:\'(.+)\'', webpage, 'content ID')
        create_date = self._search_regex(r'createDate\:\'(.+)\'', webpage, 'timestamp')

        player_webpage = self._download_webpage(
            f'https://piapro.jp/html5_player_popup/?id={content_id}&cdate={create_date}',
            video_id, note='Downloading player webpage')
        mp3_url = self._search_regex(
            r'mp3:\s*\'(.*?)\'\}', player_webpage, 'url')

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'timestamp': unified_timestamp(create_date, False),
            'duration': duration,
            'view_count': view_count,

            'filesize_approx': fs_approx,
            'url': mp3_url,
            'ext': 'mp3',
            'vcodec': 'none',
        }
