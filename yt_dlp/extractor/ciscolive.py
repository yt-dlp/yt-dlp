import itertools
import json
import urllib

from .common import InfoExtractor
from ..utils import (
    clean_html,
    float_or_none,
    int_or_none,
    parse_qs,
    traverse_obj,
    try_get,
    urlencode_postdata,
    write_string,
)


class CiscoLiveBaseIE(InfoExtractor):
    # These appear to be constant across all Cisco Live presentations
    # and are not tied to any user session or event
    RAINFOCUS_API_URL = 'https://events.rainfocus.com/api/%s'
    RAINFOCUS_API_PROFILE_ID = 'HEedDIRblcZk7Ld3KHm1T0VUtZog9eG9'
    RAINFOCUS_WIDGET_ID = 'M7n14I8sz0pklW1vybwVRdKrgdREj8sR'
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/5647924234001/SyK2FdqjM_default/index.html?videoId=%s'
    # Origin header will be set dynamically in _call_api
    HEADERS = {
        'rfApiProfileId': RAINFOCUS_API_PROFILE_ID,
        'rfWidgetId': RAINFOCUS_WIDGET_ID,
    }

    def _call_api(self, ep, rf_id, query, referrer, note=None):
        headers = self.HEADERS.copy()
        headers['Referer'] = referrer
        # Dynamically set Origin based on the referrer URL's scheme and hostname
        parsed_referrer = urllib.parse.urlparse(referrer)
        if parsed_referrer.scheme and parsed_referrer.hostname:
            headers['Origin'] = f'{parsed_referrer.scheme}://{parsed_referrer.hostname}'
        else:
            # Fallback, though referrer should always be a full URL here
            headers['Origin'] = 'https://www.ciscolive.com'
        return self._download_json(
            self.RAINFOCUS_API_URL % ep, rf_id, note=note,
            data=urlencode_postdata(query), headers=headers)

    def _parse_rf_item(self, rf_item):
        event_name = rf_item.get('eventName')
        title = rf_item['title']
        description = clean_html(rf_item.get('abstract'))
        presenter_name = try_get(rf_item, lambda x: x['participants'][0]['fullName'])
        bc_id = rf_item['videos'][0]['url']
        bc_url = self.BRIGHTCOVE_URL_TEMPLATE % bc_id
        duration = float_or_none(traverse_obj(rf_item, ('times', 0, 'length')))
        location = traverse_obj(rf_item, ('times', 0, 'room'))

        if duration:
            duration = duration * 60

        return {
            '_type': 'url_transparent',
            'url': bc_url,
            'ie_key': 'BrightcoveNew',
            'title': title,
            'description': description,
            'duration': duration,
            'creator': presenter_name,
            'location': location,
            'series': event_name,
        }


class CiscoLiveSessionIE(CiscoLiveBaseIE):
    _VALID_URL = r'https?://(?:www\.)?ciscolive(?:\.cisco)?\.com/[^#]*#/session/(?P<id>[^/?&]+)'
    _TESTS = [{
        'url': 'https://ciscolive.cisco.com/on-demand-library/?#/session/1423353499155001FoSs',
        'md5': 'c98acf395ed9c9f766941c70f5352e22',
        'info_dict': {
            'id': '5803694304001',
            'ext': 'mp4',
            'title': '13 Smart Automations to Monitor Your Cisco IOS Network',
            'description': 'md5:ec4a436019e09a918dec17714803f7cc',
            'timestamp': 1530305395,
            'upload_date': '20180629',
            'uploader_id': '5647924234001',
            'location': '16B Mezz.',
        },
    }, {
        'url': 'https://www.ciscolive.com/global/on-demand-library.html?search.event=ciscoliveemea2019#/session/15361595531500013WOU',
        'only_matching': True,
    }, {
        'url': 'https://www.ciscolive.com/global/on-demand-library.html?#/session/1490051371645001kNaS',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        rf_id = self._match_id(url)
        rf_result = self._call_api('session', rf_id, {'id': rf_id}, url)
        return self._parse_rf_item(rf_result['items'][0])


class CiscoLiveSearchIE(CiscoLiveBaseIE):
    _VALID_URL = r'https?://(?:www\.)?ciscolive(?:\.cisco)?\.com/(?:(?:global|on-demand)/)?on-demand-library(?:\.html|/)'
    _TESTS = [{
        'url': 'https://ciscolive.cisco.com/on-demand-library/?search.event=ciscoliveus2018&search.technicallevel=scpsSkillLevel_aintroductory&search.focus=scpsSessionFocus_designAndDeployment#/',
        'info_dict': {
            'title': 'Search query',
        },
        'playlist_count': 5,
    }, {
        'url': 'https://ciscolive.cisco.com/on-demand-library/?search.technology=scpsTechnology_applicationDevelopment&search.technology=scpsTechnology_ipv6&search.focus=scpsSessionFocus_troubleshootingTroubleshooting#/',
        'only_matching': True,
    }, {
        'url': 'https://www.ciscolive.com/global/on-demand-library.html?search.technicallevel=scpsSkillLevel_aintroductory&search.event=ciscoliveemea2019&search.technology=scpsTechnology_dataCenter&search.focus=scpsSessionFocus_bestPractices#/',
        'only_matching': True,
    }, {
        'url': 'https://www.ciscolive.com/on-demand/on-demand-library.html?search.technology=1604969230267001eE2f',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if CiscoLiveSessionIE.suitable(url) else super().suitable(url)

    def _check_bc_id_exists(self, rf_item):  # noqa: B027
        if not isinstance(rf_item, dict) or not isinstance(rf_item.get('videos'), list) or not rf_item['videos']:
            self.write_debug(f'Item missing "videos" list or "videos" is not a list/empty: {rf_item.get("title", rf_item.get("id", "Unknown item"))}')
            return False
        if not isinstance(rf_item['videos'][0], dict) or 'url' not in rf_item['videos'][0]:
            self.write_debug(f'Item\'s first video entry missing "url": {rf_item.get("title", rf_item.get("id", "Unknown item"))}')
            return False
        return int_or_none(try_get(rf_item, lambda x: x['videos'][0]['url'])) is not None

    def _entries(self, query, url):
        current_page_query = query.copy()
        current_page_query['size'] = 50
        current_page_query['from'] = 0

        for page_num in itertools.count(1):
            self.write_debug(f'Querying API page {page_num} with params: {current_page_query}')
            results = self._call_api(
                'search', None, current_page_query, url,
                f'Downloading search JSON page {page_num}')

            if self.get_param('verbose'):
                write_string(f'\n\n[debug] API response for page {page_num}:\n')
                write_string(json.dumps(results, indent=2) + '\n\n')

            sl = traverse_obj(results, ('sectionList', 0, {dict}))
            items_data_source = results
            source_name_for_debug = 'root of results'

            if sl:
                if isinstance(sl.get('items'), list):
                    self.write_debug('Using items, total, and size from sectionList[0]')
                    items_data_source = sl
                    source_name_for_debug = 'sectionList[0]'
                else:
                    self.write_debug(
                        'sectionList[0] exists but has no "items" key. '
                        'Using items, total, and size from root of results (if available).')  # noqa: Q000
            else:
                self.write_debug('No sectionList found. Using items, total, and size from root of results.')

            items = items_data_source.get('items')
            if not items or not isinstance(items, list):
                self.write_debug(f'No "items" list found in {source_name_for_debug}.')
                break

            for item in items:
                if not isinstance(item, dict):
                    continue
                if not self._check_bc_id_exists(item):
                    self.write_debug(f"Skipping item without Brightcove ID: {item.get('title', item.get('id', 'Unknown item'))}")
                    continue  # Ensure this is single-quoted if it was double
                yield self._parse_rf_item(item)

            # Pagination logic using items_data_source for total and size
            page_size_from_response = int_or_none(items_data_source.get('size'))
            current_page_size = page_size_from_response or current_page_query['size']

            total = int_or_none(items_data_source.get('total'))
            if total is not None and (current_page_query['from'] + current_page_size) >= total:
                self.write_debug(
                    f'Reached end of results based on "total": {total} from {source_name_for_debug}, '
                    f'current "from": {current_page_query["from"]}, "size": {current_page_size}.')
                break

            if not items and page_num > 1:
                self.write_debug('No items found on subsequent page, stopping pagination.')
                break

            current_page_query['from'] += current_page_size
            if page_size_from_response is not None:
                current_page_query['size'] = page_size_from_response

    def _real_extract(self, url):
        raw_query_params = parse_qs(url)
        self.write_debug(f'Raw query parameters from URL: {raw_query_params}')

        # Initialize api_query with parameters that are always sent or have defaults,
        # based on browser inspection.
        api_query = {
            'type': 'session',
            'search': '',  # Static parameter from browser payload  # Ensure this is single-quoted if it was double
            'browserTimezone': 'America/New_York',  # Default, as seen in browser
            'catalogDisplay': 'grid',  # Default, as seen in browser
        }

        # Add/override with parameters from the input URL's query string
        for key, value_list in raw_query_params.items():
            if not value_list:
                continue

            # The key 'search' from the URL (e.g. search=#/...) is a fragment for client-side,
            # and is different from the 'search: ""' payload parameter.
            # The 'search: ""' is added above.
            # We only care about actual filter parameters like 'search.technology', 'search.event'.
            if key == 'search' and value_list[0].startswith('#'):
                self.write_debug(f'Skipping fragment query parameter: {key}={value_list[0]}')
                continue

            api_query[key] = value_list[0]  # Keep original key name, e.g., 'search.technology'

        self.write_debug(f'Processed API query parameters (before size/from): {api_query}')

        return self.playlist_result(
            self._entries(api_query, url), playlist_title='Search query')
