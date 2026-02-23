import urllib.parse

from .brightcove import BrightcoveNewIE
from .common import InfoExtractor
from .zype import ZypeIE
from ..networking import HEADRequest
from ..utils import (
    ExtractorError,
    filter_dict,
    parse_qs,
    smuggle_url,
    urlencode_postdata,
)
from ..utils.traversal import traverse_obj


class ThisOldHouseIE(InfoExtractor):
    _NETRC_MACHINE = 'thisoldhouse'
    _VALID_URL = r'https?://(?:www\.)?thisoldhouse\.com/(?:watch|how-to|tv-episode|(?:[^/?#]+/)?\d+)/(?P<id>[^/?#]+)'
    _TESTS = [{
        # Unresolved Brightcove URL embed (formerly Zype), free
        'url': 'https://www.thisoldhouse.com/furniture/21017078/how-to-build-a-storage-bench',
        'info_dict': {
            'id': '6325298523112',
            'ext': 'mp4',
            'title': 'How to Build a Storage Bench',
            'description': 'In the workshop, Tom Silva and Kevin O\'Connor build a storage bench for an entryway.',
            'timestamp': 1681793639,
            'upload_date': '20230418',
            'duration': 674.54,
            'tags': 'count:11',
            'uploader_id': '6314471934001',
            'thumbnail': r're:^https?://.*\.jpg',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # Brightcove embed, authwalled
        'url': 'https://www.thisoldhouse.com/glen-ridge-generational/99537/s45-e17-multi-generational',
        'info_dict': {
            'id': '6349675446112',
            'ext': 'mp4',
            'title': 'E17 | Glen Ridge Generational | Multi-Generational',
            'description': 'md5:53c6bc2e8031f3033d693d9a3563222c',
            'timestamp': 1711382202,
            'upload_date': '20240325',
            'duration': 1422.229,
            'tags': 'count:13',
            'uploader_id': '6314471934001',
            'thumbnail': r're:^https?://.*\.jpg',
        },
        'expected_warnings': ['Login with password is not supported for this website'],
        'params': {
            'skip_download': True,
        },
        'skip': 'Requires subscription',
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

    def _perform_login(self, username, password):
        login_page = self._download_webpage(
            'https://www.thisoldhouse.com/insider-login', None, 'Downloading login page')
        hidden_inputs = self._hidden_inputs(login_page)
        response = self._download_json(
            'https://www.thisoldhouse.com/wp-admin/admin-ajax.php', None, 'Logging in',
            headers={
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            }, data=urlencode_postdata(filter_dict({
                'action': 'onebill_subscriber_login',
                'email': username,
                'password': password,
                'pricingPlanTerm': hidden_inputs['pricing_plan_term'],
                'utm_parameters': hidden_inputs.get('utm_parameters'),
                'nonce': hidden_inputs['mdcr_onebill_login_nonce'],
            })))

        message = traverse_obj(response, ('data', 'message', {str}))
        if not response['success']:
            if message and 'Something went wrong' in message:
                raise ExtractorError('Invalid username or password', expected=True)
            raise ExtractorError(message or 'Login was unsuccessful')
        if message and 'Your subscription is not active' in message:
            self.report_warning(
                f'{self.IE_NAME} said your subscription is not active. '
                f'If your subscription is active, this could be caused by too many sign-ins, '
                f'and you should instead try using {self._login_hint(method="cookies")[4:]}')
        else:
            self.write_debug(f'{self.IE_NAME} said: {message}')

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage, urlh = self._download_webpage_handle(url, display_id)
        # If login response says inactive subscription, site redirects to frontpage for Insider content
        if 'To Unlock This content' in webpage or urllib.parse.urlparse(urlh.url).path in ('', '/'):
            self.raise_login_required('This video is only available for subscribers')

        video_url, video_id = self._search_regex(
            r'<iframe[^>]+src=[\'"]((?:https?:)?//(?:www\.)?thisoldhouse\.(?:chorus\.build|com)/videos/zype/([0-9a-f]{24})[^\'"]*)[\'"]',
            webpage, 'zype url', group=(1, 2), default=(None, None))
        if video_url:
            video_url = self._request_webpage(HEADRequest(video_url), video_id, 'Resolving Zype URL').url
            return self.url_result(video_url, ZypeIE, video_id)

        video_url, video_id = self._search_regex([
            r'<iframe[^>]+src=[\'"]((?:https?:)?//players\.brightcove\.net/\d+/\w+/index\.html\?videoId=(\d+))',
            r'<iframe[^>]+src=[\'"]((?:https?:)?//(?:www\.)thisoldhouse\.com/videos/brightcove/(\d+))'],
            webpage, 'iframe url', group=(1, 2))
        if not parse_qs(video_url).get('videoId'):
            video_url = self._request_webpage(HEADRequest(video_url), video_id, 'Resolving Brightcove URL').url
        return self.url_result(smuggle_url(video_url, {'referrer': url}), BrightcoveNewIE, video_id)
