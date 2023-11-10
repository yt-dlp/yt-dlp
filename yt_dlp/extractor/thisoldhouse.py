import json

from .common import InfoExtractor
from .zype import ZypeIE
from ..networking import HEADRequest
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    filter_dict,
    parse_qs,
    try_call,
    urlencode_postdata,
)


class ThisOldHouseIE(InfoExtractor):
    _NETRC_MACHINE = 'thisoldhouse'
    _VALID_URL = r'https?://(?:www\.)?thisoldhouse\.com/(?:watch|how-to|tv-episode|(?:[^/?#]+/)?\d+)/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.thisoldhouse.com/furniture/21017078/how-to-build-a-storage-bench',
        'info_dict': {
            'id': '5dcdddf673c3f956ef5db202',
            'ext': 'mp4',
            'title': 'How to Build a Storage Bench',
            'description': 'In the workshop, Tom Silva and Kevin O\'Connor build a storage bench for an entryway.',
            'timestamp': 1442548800,
            'upload_date': '20150918',
            'duration': 674,
            'view_count': int,
            'average_rating': 0,
            'thumbnail': r're:^https?://.*\.jpg\?\d+$',
            'display_id': 'how-to-build-a-storage-bench',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # Page no longer has video
        'url': 'https://www.thisoldhouse.com/watch/arlington-arts-crafts-arts-and-crafts-class-begins',
        'only_matching': True,
    }, {
        # 404 Not Found
        'url': 'https://www.thisoldhouse.com/tv-episode/ask-toh-shelf-rough-electric',
        'only_matching': True,
    }, {
        # 404 Not Found
        'url': 'https://www.thisoldhouse.com/how-to/how-to-build-storage-bench',
        'only_matching': True,
    }, {
        'url': 'https://www.thisoldhouse.com/21113884/s41-e13-paradise-lost',
        'only_matching': True,
    }, {
        # iframe www.thisoldhouse.com
        'url': 'https://www.thisoldhouse.com/21083431/seaside-transformation-the-westerly-project',
        'only_matching': True,
    }]

    _LOGIN_URL = 'https://login.thisoldhouse.com/usernamepassword/login'

    def _perform_login(self, username, password):
        self._request_webpage(
            HEADRequest('https://www.thisoldhouse.com/insider'), None, 'Requesting session cookies')
        urlh = self._request_webpage(
            'https://www.thisoldhouse.com/wp-login.php', None, 'Requesting login info',
            errnote='Unable to login', query={'redirect_to': 'https://www.thisoldhouse.com/insider'})

        try:
            auth_form = self._download_webpage(
                self._LOGIN_URL, None, 'Submitting credentials', headers={
                    'Content-Type': 'application/json',
                    'Referer': urlh.url,
                }, data=json.dumps(filter_dict({
                    **{('client_id' if k == 'client' else k): v[0] for k, v in parse_qs(urlh.url).items()},
                    'tenant': 'thisoldhouse',
                    'username': username,
                    'password': password,
                    'popup_options': {},
                    'sso': True,
                    '_csrf': try_call(lambda: self._get_cookies(self._LOGIN_URL)['_csrf'].value),
                    '_intstate': 'deprecated',
                }), separators=(',', ':')).encode())
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 401:
                raise ExtractorError('Invalid username or password', expected=True)
            raise

        self._request_webpage(
            'https://login.thisoldhouse.com/login/callback', None, 'Completing login',
            data=urlencode_postdata(self._hidden_inputs(auth_form)))

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        if 'To Unlock This content' in webpage:
            self.raise_login_required(
                'This video is only available for subscribers. '
                'Note that --cookies-from-browser may not work due to this site using session cookies')

        video_url, video_id = self._search_regex(
            r'<iframe[^>]+src=[\'"]((?:https?:)?//(?:www\.)?thisoldhouse\.(?:chorus\.build|com)/videos/zype/([0-9a-f]{24})[^\'"]*)[\'"]',
            webpage, 'video url', group=(1, 2))
        video_url = self._request_webpage(HEADRequest(video_url), video_id, 'Resolving Zype URL').url

        return self.url_result(video_url, ZypeIE, video_id)
