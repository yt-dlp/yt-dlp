from .common import InfoExtractor
from .vimeo import VHXEmbedIE
from ..utils import (
    ExtractorError,
    clean_html,
    update_url,
    urlencode_postdata,
)
from ..utils.traversal import find_element, traverse_obj


class SoftWhiteUnderbellyIE(InfoExtractor):
    _LOGIN_URL = 'https://www.softwhiteunderbelly.com/login'
    _NETRC_MACHINE = 'softwhiteunderbelly'
    _VALID_URL = r'https?://(?:www\.)?softwhiteunderbelly\.com/videos/(?P<id>[\w-]+)'
    _TESTS = [{
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
    }, {
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
    }]

    def _perform_login(self, username, password):
        signin_page = self._download_webpage(self._LOGIN_URL, None, 'Fetching authenticity token')
        self._download_webpage(
            self._LOGIN_URL, None, 'Logging in',
            data=urlencode_postdata({
                'email': username,
                'password': password,
                'authenticity_token': self._html_search_regex(
                    r'name=["\']authenticity_token["\']\s+value=["\']([^"\']+)', signin_page, 'authenticity_token'),
                'utf8': True,
            }),
        )

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)
        if '<div id="watch-unauthorized"' in webpage:
            if self._get_cookies('https://www.softwhiteunderbelly.com').get('_session'):
                raise ExtractorError('This account is not subscribed to this content', expected=True)
            self.raise_login_required()

        embed_url, embed_id = self._html_search_regex(
            r'embed_url:\s*["\'](?P<url>https?://embed\.vhx\.tv/videos/(?P<id>\d+)[^"\']*)',
            webpage, 'embed url', group=('url', 'id'))

        return {
            '_type': 'url_transparent',
            'ie_key': VHXEmbedIE.ie_key(),
            'url': VHXEmbedIE._smuggle_referrer(embed_url, 'https://www.softwhiteunderbelly.com'),
            'id': embed_id,
            'display_id': display_id,
            'title': traverse_obj(webpage, ({find_element(id='watch-info')}, {find_element(cls='video-title')}, {clean_html})),
            'description': self._html_search_meta('description', webpage, default=None),
            'thumbnail': update_url(self._og_search_thumbnail(webpage) or '', query=None) or None,
        }
