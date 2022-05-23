from .common import InfoExtractor
from ..compat import compat_urlparse
from ..utils import (
    ExtractorError,
    parse_duration,
    parse_filesize,
    str_to_int,
    unified_timestamp,
    urlencode_postdata,
)


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
    }, {
        'note': 'There are break lines in description, mandating (?s) flag',
        'url': 'https://piapro.jp/t/9cSd',
        'md5': '952bb6d1e8de95050206408a87790676',
        'info_dict': {
            'id': '9cSd',
            'ext': 'mp3',
            'title': '青に溶けた風船 / 初音ミク',
            'description': 'md5:d395a9bd151447631a5a1460bc7f9132',
            'uploader': 'シアン・キノ',
            'uploader_id': 'cyankino',
        }
    }]

    _login_status = False

    def _perform_login(self, username, password):
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
            self.report_warning(
                'unable to log in: bad username or password')
        self._login_status = login_ok

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        category_id = self._search_regex(r'categoryId=(.+)">', webpage, 'category ID')
        if category_id not in ('1', '2', '21', '22', '23', '24', '25'):
            raise ExtractorError('The URL does not contain audio.', expected=True)

        str_duration, str_filesize = self._search_regex(
            r'サイズ：</span>(.+?)/\(([0-9,]+?[KMG]?B)）', webpage, 'duration and size',
            group=(1, 2), default=(None, None))
        str_viewcount = self._search_regex(r'閲覧数：</span>([0-9,]+)\s+', webpage, 'view count', fatal=False)

        uploader_id, uploader = self._search_regex(
            r'<a\s+class="cd_user-name"\s+href="/(.*)">([^<]+)さん<', webpage, 'uploader',
            group=(1, 2), default=(None, None))
        content_id = self._search_regex(r'contentId\:\'(.+)\'', webpage, 'content ID')
        create_date = self._search_regex(r'createDate\:\'(.+)\'', webpage, 'timestamp')

        player_webpage = self._download_webpage(
            f'https://piapro.jp/html5_player_popup/?id={content_id}&cdate={create_date}',
            video_id, note='Downloading player webpage')

        return {
            'id': video_id,
            'title': self._html_search_regex(r'<h1\s+class="cd_works-title">(.+?)</h1>', webpage, 'title', fatal=False),
            'description': self._html_search_regex(r'(?s)<p\s+class="cd_dtl_cap">(.+?)</p>\s*<div', webpage, 'description', fatal=False),
            'uploader': uploader,
            'uploader_id': uploader_id,
            'timestamp': unified_timestamp(create_date, False),
            'duration': parse_duration(str_duration),
            'view_count': str_to_int(str_viewcount),
            'thumbnail': self._html_search_meta('twitter:image', webpage),

            'filesize_approx': parse_filesize(str_filesize.replace(',', '')),
            'url': self._search_regex(r'mp3:\s*\'(.*?)\'\}', player_webpage, 'url'),
            'ext': 'mp3',
            'vcodec': 'none',
        }
