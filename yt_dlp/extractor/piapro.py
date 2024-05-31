from .common import InfoExtractor
from ..compat import compat_urlparse
from ..utils import (
    ExtractorError,
    clean_html,
    get_element_by_class,
    parse_duration,
    parse_filesize,
    str_to_int,
    unified_timestamp,
    urlencode_postdata,
)


class PiaproIE(InfoExtractor):
    _NETRC_MACHINE = 'piapro'
    _VALID_URL = r'https?://piapro\.jp/(?:t|content)/(?P<id>[\w-]+)/?'
    _TESTS = [{
        'url': 'https://piapro.jp/t/NXYR',
        'md5': 'f7c0f760913fb1d44a1c45a4af793909',
        'info_dict': {
            'id': 'NXYR',
            'ext': 'mp3',
            'uploader': 'wowaka',
            'uploader_id': 'wowaka',
            'title': '裏表ラバーズ',
            'description': 'http://www.nicovideo.jp/watch/sm8082467',
            'duration': 189.0,
            'timestamp': 1251785475,
            'thumbnail': r're:^https?://.*\.(?:png|jpg)$',
            'upload_date': '20090901',
            'view_count': int,
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
            'duration': 229.0,
            'timestamp': 1644030039,
            'upload_date': '20220205',
            'view_count': int,
            'thumbnail': r're:^https?://.*\.(?:png|jpg)$',
            'uploader_id': 'cyankino',
        }
    }, {
        'url': 'https://piapro.jp/content/hcw0z3a169wtemz6',
        'only_matching': True
    }, {
        'url': 'https://piapro.jp/t/-SO-',
        'only_matching': True
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
            parts = compat_urlparse.urlparse(urlh.url)
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

        def extract_info(name, description):
            return self._search_regex(rf'{name}[：:]\s*([\d\s,:/]+)\s*</p>', webpage, description, default=None)

        return {
            'id': video_id,
            'title': clean_html(get_element_by_class('contents_title', webpage)),
            'description': clean_html(get_element_by_class('contents_description', webpage)),
            'uploader': clean_html(get_element_by_class('contents_creator_txt', webpage)),
            'uploader_id': self._search_regex(
                r'<a\s+href="/([^"]+)"', get_element_by_class('contents_creator', webpage), 'uploader id', default=None),
            'timestamp': unified_timestamp(extract_info('投稿日', 'timestamp'), False),
            'duration': parse_duration(extract_info('長さ', 'duration')),
            'view_count': str_to_int(extract_info('閲覧数', 'view count')),
            'thumbnail': self._html_search_meta('twitter:image', webpage),
            'filesize_approx': parse_filesize((extract_info('サイズ', 'size') or '').replace(',', '')),
            'url': self._search_regex(r'\"url\":\s*\"(.*?)\"', webpage, 'url'),
            'ext': 'mp3',
            'vcodec': 'none',
        }
