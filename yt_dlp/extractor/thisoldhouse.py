import json
import time

from .common import InfoExtractor
from ..networking import HEADRequest
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    filter_dict,
    parse_qs,
    strip_jsonp,
    try_call,
    urlencode_postdata,
)
from ..utils.traversal import traverse_obj


class ThisOldHouseIE(InfoExtractor):
    _NETRC_MACHINE = 'thisoldhouse'
    _VALID_URL = r'https?://(?:www\.)?thisoldhouse\.com/(?:watch|how-to|tv-episode|(?:[^/]+/)?\d+)/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.thisoldhouse.com/how-to/how-to-build-storage-bench',
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
        'url': 'https://www.thisoldhouse.com/watch/arlington-arts-crafts-arts-and-crafts-class-begins',
        'only_matching': True,
    }, {
        'url': 'https://www.thisoldhouse.com/tv-episode/ask-toh-shelf-rough-electric',
        'only_matching': True,
    }, {
        'url': 'https://www.thisoldhouse.com/furniture/21017078/how-to-build-a-storage-bench',
        'only_matching': True,
    }, {
        'url': 'https://www.thisoldhouse.com/21113884/s41-e13-paradise-lost',
        'only_matching': True,
    }, {
        # iframe www.thisoldhouse.com
        'url': 'https://www.thisoldhouse.com/21083431/seaside-transformation-the-westerly-project',
        'only_matching': True,
    }]
    _ZYPE_TMPL = 'https://player.zype.com/embed/%s.html?api_key=hsOk_yMSPYNrT22e9pu8hihLXjaZf0JW5jsOWv4ZqyHJFvkJn6rtToHl09tbbsbe'
    _LOGIN_URL = 'https://login.thisoldhouse.com/usernamepassword/login'

    def _perform_login(self, username, password):
        self._request_webpage(
            HEADRequest('https://www.thisoldhouse.com/insider'), None, 'Requesting session cookies')

        urlh = self._request_webpage(
            'https://www.thisoldhouse.com/wp-login.php', None, 'Requesting login info',
            errnote='Unable to login', query={'redirect_to': 'https://www.thisoldhouse.com/insider'})
        login_info = traverse_obj(parse_qs(urlh.url), {
            'state': ('state', 0),
            'client_id': ('client', 0),
            'protocol': ('protocol', 0),
            'connection': ('connection', 0),
            'scope': ('scope', 0),
            'nonce': ('nonce', 0),
            'response_type': ('response_type', 0),
            'response_mode': ('response_mode', 0),
            'redirect_uri': ('redirect_uri', 0),
        })

        headers = {'Referer': urlh.url}
        auth_info = self._download_json(
            f'https://login.thisoldhouse.com/client/{login_info["client_id"]}.js?t{int(time.time() * 1000)}',
            None, 'Downloading auth info JSON', headers=headers, transform_source=strip_jsonp)

        headers['Content-Type'] = 'application/json'
        try:
            auth_form = self._download_webpage(
                self._LOGIN_URL, None, 'Submitting credentials', headers=headers,
                data=json.dumps(filter_dict({
                    **login_info,
                    'tenant': traverse_obj(auth_info, ('tenant', {str})) or 'thisoldhouse',
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
            self.raise_login_required(method='cookies')
        video_url = self._search_regex(
            r'<iframe[^>]+src=[\'"]((?:https?:)?//(?:www\.)?thisoldhouse\.(?:chorus\.build|com)/videos/zype/([0-9a-f]{24})[^\'"]*)[\'"]',
            webpage, 'video url')
        if 'subscription_required=true' in video_url or 'c-entry-group-labels__image' in webpage:
            return self.url_result(self._request_webpage(HEADRequest(video_url), display_id).url, 'Zype', display_id)
        video_id = self._search_regex(r'(?:https?:)?//(?:www\.)?thisoldhouse\.(?:chorus\.build|com)/videos/zype/([0-9a-f]{24})', video_url, 'video id')
        return self.url_result(self._ZYPE_TMPL % video_id, 'Zype', video_id)
