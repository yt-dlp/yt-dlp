import itertools

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    parse_qs,
    str_or_none,
    try_call,
    urlencode_postdata,
)
from ..utils.traversal import require, traverse_obj


class CiscoLiveBaseIE(InfoExtractor):
    _BASE_URL = 'https://www.ciscolive.com'
    _HEADERS = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Rfapiprofileid': 'HEedDIRblcZk7Ld3KHm1T0VUtZog9eG9',
        'Rfwidgetid': 'M7n14I8sz0pklW1vybwVRdKrgdREj8sR',
    }

    def _call_api(self, endpoint, payload, doseq=False, **kwargs):
        api_resp = self._download_json(
            f'https://events.rainfocus.com/api/{endpoint}', payload.get('id'),
            headers=self._HEADERS, data=urlencode_postdata(payload, doseq=doseq), **kwargs)
        if traverse_obj(api_resp, 'responseCode') != '0':
            msg = traverse_obj(api_resp, ('responseMessage', {str}, filter))
            raise ExtractorError(
                msg or 'API returned an error response', expected=bool(msg))

        return api_resp


class CiscoLiveSessionIE(CiscoLiveBaseIE):
    IE_NAME = 'ciscolive:session'
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/5647924234001/SyK2FdqjM_default/index.html?videoId=%s'

    _VALID_URL = r'https?://(?:www\.)?ciscolive\.com/on-demand/on-demand-library\.html[^#]*#/(?P<type>session|video)/(?P<id>[^/?&]+)'
    _TESTS = [{
        'url': 'https://www.ciscolive.com/on-demand/on-demand-library.html#/session/1749591952508001pGUf',
        'info_dict': {
            'id': '6374109944112',
            'ext': 'mp4',
            'title': 'AI Changes Everything: A New Blueprint for Network Security, Zero Trust, and the SOC - KDDSEC-1000',
            'creators': 'count:4',
            'description': 'md5:70ee6edf45c8221d7e9346426ae25fb0',
            'display_id': '1749591952508001pGUf',
            'duration': 2921.387,
            'series': 'Cisco Live On Demand',
            'series_id': '1749591952508001pGUf',
            'thumbnail': r're:https?://cf-images\.us-east-1\.prod\.boltdns\.net/.+\.jpg',
            'timestamp': 1749602136,
            'upload_date': '20250611',
            'uploader_id': '5647924234001',
        },
        'add_ie': ['BrightcoveNew'],
    }, {
        'url': 'https://www.ciscolive.com/on-demand/on-demand-library.html#/video/1749603837855001eWhB',
        'info_dict': {
            'id': '6374109944112',
            'ext': 'mp4',
            'title': 'AI Changes Everything: A New Blueprint for Network Security, Zero Trust, and the SOC - KDDSEC-1000',
            'creators': 'count:4',
            'description': 'md5:70ee6edf45c8221d7e9346426ae25fb0',
            'display_id': '1749603837855001eWhB',
            'duration': 2921.387,
            'series': 'Cisco Live On Demand',
            'series_id': '1749591952508001pGUf',
            'thumbnail': r're:https?://cf-images\.us-east-1\.prod\.boltdns\.net/.+\.jpg',
            'timestamp': 1749602136,
            'upload_date': '20250611',
            'uploader_id': '5647924234001',
        },
        'add_ie': ['BrightcoveNew'],
    }, {
        'url': 'https://www.ciscolive.com/on-demand/on-demand-library.html?search.sessiontype=Keynote#/session/1748956425383001aEIK',
        'info_dict': {
            'id': '6373626841112',
            'ext': 'mp4',
            'title': 'Keynote: Innovation in Action - KEYGEN-1002',
            'creators': 'count:6',
            'description': 'md5:3a1d82ca9e4e3505e251c251d3509cc5',
            'display_id': '1748956425383001aEIK',
            'duration': 4405.739,
            'series': 'Cisco Live On Demand',
            'series_id': '1748956425383001aEIK',
            'thumbnail': r're:https?://cf-images\.us-east-1\.prod\.boltdns\.net/.+\.jpg',
            'timestamp': 1748553118,
            'upload_date': '20250529',
            'uploader_id': '5647924234001',
        },
        'add_ie': ['BrightcoveNew'],
    }]

    def _real_extract(self, url):
        url_type, display_id = self._match_valid_url(url).group('type', 'id')
        if url_type == 'video':
            auth_token = try_call(lambda: self._get_cookies(self._BASE_URL)['rfjwt'].value)
            if not auth_token:
                self.raise_login_required()

            self._HEADERS['Rfauthtoken'] = auth_token
            file = self._call_api('file', {'id': display_id})
            rf_id = traverse_obj(file, ('items', 'file', 'rainfocusId', {str}))
        else:
            rf_id = display_id

        return {
            '_type': 'url_transparent',
            'ie_key': 'BrightcoveNew',
            'display_id': display_id,
            **traverse_obj(self._call_api('session', {'id': rf_id}), ('items', ..., {
                'title': ('title', {clean_html}),
                'creators': ('participants', ..., 'fullName', {str}),
                'description': ('abstract', {clean_html}),
                'series': ('eventName', {clean_html}),
                'series_id': ('sessionID', {str}),
                'url': ('videos', ..., 'url', {str_or_none},
                        {lambda x: self.BRIGHTCOVE_URL_TEMPLATE % x}, any, {require('brightcove video ID')}),
            }, any)),
        }


class CiscoLiveSearchIE(CiscoLiveBaseIE):
    IE_NAME = 'ciscolive:search'

    _VALID_URL = r'https?://(?:www\.)?ciscolive\.com/on-demand/on-demand-library\.html\?[^#]+#/(?!session|video)[^/?#]*$'
    _TESTS = [{
        'url': 'https://www.ciscolive.com/on-demand/on-demand-library.html?search.event=1737762187215001jsy4#/',
        'info_dict': {
            'id': 'search',
        },
        'playlist_count': 500,
    }, {
        'url': 'https://www.ciscolive.com/on-demand/on-demand-library.html?search.event=1707169032930001EEu2&search.technology=1538390420915002wPJx#/',
        'info_dict': {
            'id': 'search',
        },
        'playlist_count': 34,
    }]

    def _entries(self, payload):
        from_val = 0

        for page in itertools.count(1):
            search = self._call_api(
                'search', {**payload, 'from': from_val},
                doseq=True, note=f'Downloading page {page}')
            if not traverse_obj(search, 'sectionList'):
                return

            yield from [self.url_result(
                f'{self._BASE_URL}/on-demand/on-demand-library.html#/session/{session_id}', CiscoLiveSessionIE)
                for session_id in traverse_obj(search, (
                    'sectionList', ..., 'items', ..., 'sessionID', {str_or_none}, filter, all, filter))]

            from_val += int_or_none(payload['size'])
            if from_val >= min(500, traverse_obj(search, (
                'sectionList', ..., 'total', {int_or_none}, any,
            ))):
                break

    def _real_extract(self, url):
        payload = {
            'size': '50',
            'type': 'session',
            **parse_qs(url),
        }

        return self.playlist_result(self._entries(payload), 'search')
