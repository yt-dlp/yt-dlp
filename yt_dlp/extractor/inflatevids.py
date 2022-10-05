from .common import InfoExtractor
from ..compat import (
    compat_urlparse,
)
from ..utils import (
    clean_html,
    ExtractorError,
    int_or_none,
    strip_or_none,
    unified_strdate,
    url_or_none,
    urlencode_postdata,
)


class InflateVidsIE(InfoExtractor):
    _LOGIN_URL = 'https://tube.inflatevids.xyz/login'
    _NETRC_MACHINE = 'inflatevids'
    _VALID_URL = r'https?://(?:www.)?tube.inflatevids.xyz/watch/(?P<id>[^>]+)'

    _TESTS = [{
        'url': 'https://tube.inflatevids.xyz/watch/8zdGbHUiIsi6hLg',
        'info_dict': {
            'id': '8zdGbHUiIsi6hLg',
            'ext': 'mp4',
            'title': 'Inside a double layered pvc Eevee pooltoy suit',
            'thumbnail': r're:^https?://.*\.(jpg|jpeg)',
        },
    }]

    # TODO: Broken; HTTP Error 404
    def _perform_login(self, username, password):
        login_page = self._download_webpage(
            self._LOGIN_URL, None, 'Downloading login page')

        login_form = self._hidden_inputs(login_page)

        login_form.update({
            'username': username,
            'password': password,
        })

        post_url = self._search_regex(
            r'<form[^.]+method=(["\'])(?P<url>.+?)\1', login_page,
            'post url', default=self._LOGIN_URL, group='url')

        if not post_url.startswith('http'):
            post_url = compat_urlparse.urljoin(self._LOGIN_URL, post_url)

        response = self._download_webpage(
            post_url, None, 'Logging in', data=urlencode_postdata(login_form),
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Host': 'tube.inflatevids.xyz',
                'Origin': 'https://tube.inflatevids.xyz',
                'Referer': 'https://tube.inflatevids.xyz/login',
            })

        # Successful login
        if any(p in response for p in (
                '/logout', 'Log out')):
            return

        error = self._html_search_regex(
            r'(<div class[^>]+errors form-group.*</i>)(?P<error>.*)</div>',
            response, 'error message', default=None, group='error')
        if error:
            raise ExtractorError('Login failed. Reason: %s' % error, expected=True)
        raise ExtractorError('Login failed.')

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        self._set_cookie(url, 'pop_up_18', '1')

        return {
            'id': video_id,
            'tags': self._html_search_meta('keywords', webpage, default=None),

            'title': self._html_search_meta(['og:title', 'twitter:title', 'title'],
                                            webpage, 'title'),

            # TODO: Strip out newlines and other escape sequences.
            'description': clean_html(
                self._html_search_regex(r'<div[^>]+itemprop="description"[^>]*>(.*)',
                                        webpage, 'description', default=None)
            ),

            'view_count': int_or_none(
                self._html_search_regex(r'<span[^>]+video-views-count[^>]*>([^<]+)<',
                                        webpage, 'view_count'),
            ),

            'like_count': int_or_none(
                self._html_search_regex(r'(?:<div[^<]+"likes-bar"[^<]+data-likes[^>])"([^<]*)"',
                                        webpage, 'like_count', default=None)
            ),

            'dislike_count': int_or_none(
                self._html_search_regex(r'(?:<div[^<]+"dislikes-bar"[^<]+data-likes[^>])"([^<]*)"',
                                        webpage, 'dislike_count', default=None)
            ),

            # TODO: Add support for this.
            # 'categories':

            'url': url_or_none(
                self._html_search_regex(r'(?:<div[^>]+contentUrl[^>]*>)([^<]+)<', webpage, url),
            ),

            'upload_date': unified_strdate(
                self._html_search_regex(r'<div[^>]+uploadDate[^>]*>([^<]+)<',
                                        webpage, 'upload_date', default=None)
            ),

            'thumbnail': self._html_search_meta(
                ['og:image', 'twitter:image', 'thumbnail'],
                webpage, 'thumbnail', default=None),

            'uploader': strip_or_none(
                self._html_search_regex(r'(?:<div[^>]+?publisher-name[^>]*>)[^<]*(?:<a href[^>]+id=)([^>"]+)',
                                        webpage, 'uploader'),
            ),
        }
