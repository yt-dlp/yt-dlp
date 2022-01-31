# coding: utf-8
from __future__ import unicode_literals


from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    urlencode_postdata
)


class TumblrIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<blog_name>[^/?#&]+)\.tumblr\.com/(?:post|video)/(?P<id>[0-9]+)(?:$|[/?#])'
    _NETRC_MACHINE = 'tumblr'
    _LOGIN_URL = 'https://www.tumblr.com/login'
    _TESTS = [{
        'url': 'http://tatianamaslanydaily.tumblr.com/post/54196191430/orphan-black-dvd-extra-behind-the-scenes',
        'md5': '479bb068e5b16462f5176a6828829767',
        'info_dict': {
            'id': '54196191430',
            'ext': 'mp4',
            'title': 'tatiana maslany news, Orphan Black || DVD extra - behind the scenes ↳...',
            'description': 'md5:390ab77358960235b6937ab3b8528956',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 127,
        }
    }, {
        'url': 'https://maskofthedragon.tumblr.com/post/626907179849564160/mona-talking-in-english',
        'md5': 'f43ff8a8861712b6cf0e0c2bd84cfc68',
        'info_dict': {
            'id': '626907179849564160',
            'ext': 'mp4',
            'title': 'Me roast is buggered!, Mona\xa0“talking” in\xa0“english”',
            'description': 'md5:082a3a621530cb786ad2b7592a6d9e2c',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 7,
        },
        'params': {
            'format': 'hd',
        },
    }, {
        'url': 'http://naked-yogi.tumblr.com/post/118312946248/naked-smoking-stretching',
        'md5': 'de07e5211d60d4f3a2c3df757ea9f6ab',
        'info_dict': {
            'id': 'Wmur',
            'ext': 'mp4',
            'title': 'naked smoking & stretching',
            'upload_date': '20150506',
            'timestamp': 1430931613,
            'age_limit': 18,
            'uploader_id': '1638622',
            'uploader': 'naked-yogi',
        },
        # 'add_ie': ['Vidme'],
        'skip': 'dead embedded video host'
    }, {
        'url': 'https://dominustempori.tumblr.com/post/673572712813297664/youtubes-all-right-for-some-pretty-cool',
        'md5': '5e45724c70b748f64f5a1731ac72c84a',
        'info_dict': {
            'id': '87816359',
            'ext': 'mp4',
            'title': 'Harold Ramis',
            'uploader': 'Resolution Productions Group',
            'uploader_id': 'resolutionproductions',
            'uploader_url': 'https://vimeo.com/resolutionproductions',
            'thumbnail': r're:^https?://i.vimeocdn.com/video/.*',
            'duration': 291,
        },
        'add_ie': ['Vimeo'],
    }, {
        'url': 'http://sutiblr.tumblr.com/post/139638707273',
        'md5': '2dd184b3669e049ba40563a7d423f95c',
        'info_dict': {
            'id': 'ir7qBEIKqvq',
            'ext': 'mp4',
            'title': 'Vine by sutiblr',
            'alt_title': 'Vine by sutiblr',
            'uploader': 'sutiblr',
            'uploader_id': '1198993975374495744',
            'upload_date': '20160220',
            'like_count': int,
            'comment_count': int,
            'repost_count': int,
            'thumbnail': r're:^https?://.*\.jpg',
            'timestamp': 1455940159,
            'view_count': int,
        },
        'add_ie': ['Vine'],
    }, {
        'url': 'https://silami.tumblr.com/post/84250043974/my-bad-river-flows-in-you-impression-on-maschine',
        'md5': '3c92d7c3d867f14ccbeefa2119022277',
        'info_dict': {
            'id': 'nYtvtTPuTl',
            'ext': 'mp4',
            'title': 'Video by silbulterman',
            'description': '#maschine',
            'uploader_id': '242859024',
            'thumbnail': r're:^https?://.*\.jpg',
            'timestamp': 1398801174,
            'like_count': int,
            'uploader': 'Sil',
            'channel': 'silbulterman',
            'comment_count': int,
            'upload_date': '20140429',
        },
        'add_ie': ['Instagram'],
    }]

    def _real_initialize(self):
        self._login()

    def _login(self):
        username, password = self._get_login_info()
        if username is None:
            return

        login_page = self._download_webpage(
            self._LOGIN_URL, None, 'Downloading login page')

        login_form = self._hidden_inputs(login_page)
        login_form.update({
            'user[email]': username,
            'user[password]': password
        })

        response, urlh = self._download_webpage_handle(
            self._LOGIN_URL, None, 'Logging in',
            data=urlencode_postdata(login_form), headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': self._LOGIN_URL,
            })

        # Successful login
        if '/dashboard' in urlh.geturl():
            return

        login_errors = self._parse_json(
            self._search_regex(
                r'RegistrationForm\.errors\s*=\s*(\[.+?\])\s*;', response,
                'login errors', default='[]'),
            None, fatal=False)
        if login_errors:
            raise ExtractorError(
                'Unable to login: %s' % login_errors[0], expected=True)

        self.report_warning('Login has probably failed')

    def _real_extract(self, url):
        m_url = self._match_valid_url(url)
        video_id = m_url.group('id')
        blog = m_url.group('blog_name')

        url = 'http://%s.tumblr.com/post/%s/' % (blog, video_id)
        webpage, urlh = self._download_webpage_handle(url, video_id)

        redirect_url = urlh.geturl()
        if 'tumblr.com/safe-mode' in redirect_url or redirect_url.startswith('/safe-mode'):
            raise ExtractorError(
                'This Tumblr may contain sensitive media. '
                'Disable safe mode in your account settings '
                'at https://www.tumblr.com/settings/account#safe_mode',
                expected=True)

        iframe_url = self._search_regex(
            r'src=\'(https?://www\.tumblr\.com/video/[^\']+)\'',
            webpage, 'iframe url', default=None)
        if iframe_url is None:
            iframe_url = self._search_regex(
                r'src=["\'](https?://safe\.txmblr\.com/svc/embed/inline/[^"\']+)["\']',
                webpage, 'embed iframe url', default=None)
            return self.url_result(iframe_url or redirect_url, 'Generic')

        iframe = self._download_webpage(
            iframe_url, video_id, 'Downloading iframe page',
            headers={'Referer': redirect_url})

        duration = None
        sources = []

        sd_url = self._search_regex(
            r'<source[^>]+src=(["\'])(?P<url>.+?)\1', iframe,
            'sd video url', default=None, group='url')
        if sd_url:
            sources.append((sd_url, 'sd'))

        options = self._parse_json(
            self._search_regex(
                r'data-crt-options=(["\'])(?P<options>.+?)\1', iframe,
                'hd video url', default='', group='options'),
            video_id, fatal=False)
        if options:
            duration = int_or_none(options.get('duration'))
            hd_url = options.get('hdUrl')
            if hd_url:
                sources.append((hd_url, 'hd'))

        formats = [{
            'url': video_url,
            'ext': 'mp4',
            'format_id': format_id,
            'height': int_or_none(self._search_regex(
                r'/(\d{3,4})$', video_url, 'height', default=None)),
            'quality': quality,
        } for quality, (video_url, format_id) in enumerate(sources)]

        self._sort_formats(formats)

        # The only place where you can get a title, it's not complete,
        # but searching in other places doesn't work for all videos
        video_title = self._html_search_regex(
            r'(?s)<title>(?P<title>.*?)(?: \| Tumblr)?</title>',
            webpage, 'title')

        return {
            'id': video_id,
            'title': video_title,
            'description': self._og_search_description(webpage, default=None),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'duration': duration,
            'formats': formats,
        }
