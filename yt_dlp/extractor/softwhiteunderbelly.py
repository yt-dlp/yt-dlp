
from .common import InfoExtractor
from .vimeo import VHXEmbedIE
from ..utils import (
    ExtractorError,
    clean_html,
    get_element_by_class,
    get_element_by_id,
    unified_strdate,
    urlencode_postdata,
)


class SoftWhiteUnderbellyIE(InfoExtractor):
    _LOGIN_URL = 'https://www.softwhiteunderbelly.com/login'
    _NETRC_MACHINE = 'softwhiteunderbelly'

    _VALID_URL = r'https?://(?:www\.)?softwhiteunderbelly\.com/videos/(?P<id>.+)'
    _TESTS = [
        {
            'url': 'https://www.softwhiteunderbelly.com/videos/kenneth-final1',
            'note': 'A single Soft White Underbelly Episode',
            'md5': '8e79f29ec1f1bda6da2e0b998fcbebb8',
            'info_dict': {
                'id': '3201266',
                'ext': 'mp4',
                'display_id': 'kenneth-final1',
                'title': 'Appalachian Man interview-Kenneth',
                'description': 'Soft White Underbelly interview and portrait of Kenneth, an Appalachian man in Clay County, Kentucky.',
                'thumbnail': 'https://vhx.imgix.net/softwhiteunderbelly/assets/249f6db0-2b39-49a4-979b-f8dad4681825.jpg',
                'uploader_url': 'https://vimeo.com/user80538407',
                'uploader': 'OTT Videos',
                'uploader_id': 'user80538407',
                'duration': 512,
            },
            'expected_warnings': ['Failed to parse XML: not well-formed'],
        },
        {
            'url': 'https://www.softwhiteunderbelly.com/videos/tj-2-final-2160p',
            'note': 'A single Soft White Underbelly Episode',
            'md5': '286bd8851b4824c62afb369e6f307036',
            'info_dict': {
                'id': '3506029',
                'ext': 'mp4',
                'display_id': 'tj-2-final-2160p',
                'title': 'Fentanyl Addict interview-TJ (follow up)',
                'description': 'Soft White Underbelly follow up interview and portrait of TJ, a fentanyl addict on Skid Row.',
                'thumbnail': 'https://vhx.imgix.net/softwhiteunderbelly/assets/c883d531-5da0-4faf-a2e2-8eba97e5adfc.jpg',
                'duration': 817,
                'uploader': 'OTT Videos',
                'uploader_url': 'https://vimeo.com/user80538407',
                'uploader_id': 'user80538407',
            },
            'expected_warnings': ['Failed to parse XML: not well-formed'],
        },
    ]

    def _get_authenticity_token(self, display_id):
        signin_page = self._download_webpage(self._LOGIN_URL, display_id, note='Getting authenticity token')
        return self._html_search_regex(
            r'name=["\']authenticity_token["\'] value=["\'](.+?)["\']', signin_page, 'authenticity_token',
        )

    def _login(self, display_id):
        username, password = self._get_login_info()
        if not username:
            return True

        response = self._download_webpage(
            self._LOGIN_URL,
            display_id,
            note='Logging in',
            fatal=False,
            data=urlencode_postdata({
                'email': username,
                'password': password,
                'authenticity_token': self._get_authenticity_token(display_id),
                'utf8': True,
            }),
        )

        user_has_subscription = self._search_regex(
            r'user_has_subscription:\s*["\'](.+?)["\']', response, 'subscription status', default='none',
        )
        if user_has_subscription.lower() == 'true':
            return
        elif user_has_subscription.lower() == 'false':
            return 'Account is not subscribed'
        else:
            return 'Incorrect username/password'

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = None
        if self._get_cookies('https://www.softwhiteunderbelly.com').get('_session'):
            webpage = self._download_webpage(url, display_id)
        if not webpage or '<div id="watch-unauthorized"' in webpage:
            login_err = self._login(display_id)
            webpage = self._download_webpage(url, display_id)
            if login_err and '<div id="watch-unauthorized"' in webpage:
                if login_err is True:
                    self.raise_login_required(method='any')
                raise ExtractorError(login_err, expected=True)

        embed_url = self._html_search_regex(r'embed_url:\s*["\'](.+?)["\']', webpage, 'embed url')
        thumbnail = self._og_search_thumbnail(webpage)
        watch_info = get_element_by_id('watch-info', webpage) or ''

        title = clean_html(get_element_by_class('video-title', watch_info))

        return {
            '_type': 'url_transparent',
            'ie_key': VHXEmbedIE.ie_key(),
            'url': VHXEmbedIE._smuggle_referrer(embed_url, 'https://www.softwhiteunderbelly.com'),
            'id': self._search_regex(r'embed\.vhx\.tv/videos/(.+?)\?', embed_url, 'id'),
            'display_id': display_id,
            'title': title,
            'description': self._html_search_meta('description', webpage, fatal=False),
            'thumbnail': thumbnail.split('?')[0] if thumbnail else None,  # Ignore crop/downscale
            'release_date': unified_strdate(
                self._search_regex(
                    r'data-meta-field-name=["\']release_dates["\'] data-meta-field-value=["\'](.+?)["\']',
                    watch_info,
                    'release date',
                    default=None,
                ),
            ),
        }
