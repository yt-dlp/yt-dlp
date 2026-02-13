from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    parse_iso8601,
    remove_end,
    remove_start,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import require, traverse_obj


class EbayIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ebay\.com/itm/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.ebay.com/itm/194509326719',
        'info_dict': {
            'id': '194509326719',
            'ext': 'mp4',
            'title': 'WiFi internal antenna adhesive for wifi 2.4GHz wifi 5 wifi 6 wifi 6E full bands',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        video_json = self._search_json(r'"video":', webpage, 'video json', video_id)

        formats = []
        for key, url in video_json['playlistMap'].items():
            if key == 'HLS':
                formats.extend(self._extract_m3u8_formats(url, video_id, fatal=False))
            elif key == 'DASH':
                formats.extend(self._extract_mpd_formats(url, video_id, fatal=False))
            else:
                self.report_warning(f'Unsupported format {key}', video_id)

        return {
            'id': video_id,
            'title': remove_end(self._html_extract_title(webpage), ' | eBay'),
            'formats': formats,
        }


class EbayLiveIE(InfoExtractor):
    IE_NAME = 'ebay:live'

    _VALID_URL = r'https?://(?:www\.)?ebay\.com/ebaylive/events/(?P<id>\w+)(?:/stream)?'
    _TESTS = [{
        'url': 'https://www.ebay.com/ebaylive/events/eOZ73pZfnvdnicEA/stream',
        'info_dict': {
            'id': 'eOZ73pZfnvdnicEA',
            'ext': 'mp4',
            'title': 'Coins, Currency, & Bullion w/ Brian! - 10/15',
            'description': 'md5:a290e26ae6e625419d4965e974dcac60',
            'live_status': 'was_live',
            'thumbnail': r're:https?://i\.ebayimg\.com/.+',
            'timestamp': 1760565884,
            'upload_date': '20251015',
            'uploader': 'everydaycoins',
            'uploader_id': 'gocpf_aqst6',
            'view_count': int,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        apollo_data = self._search_json(
            r'window\.__APOLLO_DATA__\s*=', webpage, 'apollo data', video_id)
        live_event = traverse_obj(apollo_data, (f'LiveEvent:{video_id}', {dict}))

        start_timestamp_str = traverse_obj(live_event, ('startTime', {str}))
        start_timestamp = parse_iso8601(start_timestamp_str)
        live_status = {
            'LIVE': 'is_live',
            'RECORDED': 'was_live',
            'UPCOMING': 'is_upcoming',
        }.get(live_event.get('state'))

        if live_status == 'is_upcoming':
            self.raise_no_formats(
                f'This livestream is scheduled to start at {start_timestamp_str}', expected=True)

            return {
                'id': video_id,
                'live_status': live_status,
                'release_timestamp': start_timestamp,
            }
        elif live_status == 'was_live':
            m3u8_url = traverse_obj(live_event, (
                'replay', 'replayUrl', {url_or_none}, {require('m3u8 URL')}))
        else:
            app_context = self._search_json(
                r'window\.__APP_CONTEXT__\s*=', webpage, 'app context', video_id)
            access_key = traverse_obj(app_context, (
                'shoplive', 'accessKey', {str_or_none}, {require('access key')}))
            event_id = traverse_obj(live_event, (
                'vendorEventId', {str_or_none}, {require('vendor event ID')}))
            shoplive = self._download_json(
                f'https://config.shoplive.cloud/{access_key}/{event_id}.json', video_id)
            m3u8_url = traverse_obj(shoplive, ('liveUrl', {url_or_none}, {require('m3u8 URL')}))

        host_key = traverse_obj(live_event, ('hosts', ..., '__ref', {str}, filter, any))
        tag_keys = traverse_obj(live_event, ('tags', ..., '__ref', {str}, filter))
        thumbnail_key = traverse_obj(live_event, ('previewImage', '__ref', {str}, filter))

        return {
            'id': video_id,
            'formats': self._extract_m3u8_formats(m3u8_url, video_id, 'mp4'),
            'live_status': live_status,
            'timestamp': start_timestamp,
            'uploader_id': remove_start(host_key, 'User:'),
            **traverse_obj(apollo_data, {
                'tags': (tag_keys, 'name', {clean_html}, filter),
                'thumbnail': (thumbnail_key, 'url', {url_or_none}),
                'uploader': (host_key, 'userAccountName', {clean_html}, filter),
            }),
            **traverse_obj(live_event, {
                'title': ('title', {clean_html}, filter),
                'description': ('description', {clean_html}, filter),
                'timestamp': ('startTime', {parse_iso8601}),
                'view_count': ('watchedCount', {int_or_none}),
            }),
        }
