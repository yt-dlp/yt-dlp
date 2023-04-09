import hashlib
import re

from ..utils import (
    ExtractorError,
    int_or_none,
    js_to_json,
    time_seconds,
    traverse_obj,
    unified_timestamp,
)
from .common import InfoExtractor


class MixBoxHomepageIE(InfoExtractor):
    IE_NAME = 'MixBox:homepage'
    IE_DESC = 'ミックスボックス'
    _VALID_URL = r'https?://mixbox\.live/?$'
    _TESTS = [{
        'url': 'https://mixbox.live/',
        'info_dict': {
            'id': 'mixbox-live',
            'title': 'MixBox',
            'ext': 'ts',
            'live_status': 'is_live',
        },
    }]

    def _real_extract(self, url):
        video_id = 'mixbox-live'

        asset_js_urls = re.findall(
            r'<script src="(/assets/.+?\.js)"', self._download_webpage(url, video_id))
        asset_js_urls.reverse()  # the live video info always seems to be placed in the last file

        live_video_key, live_video_url = '', ''
        for asset_js_url in asset_js_urls:
            asset_js_content = self._download_webpage(
                f'https://mixbox.live/{asset_js_url}', video_id,
                note='Fetching asset js file', errnote='Unable to fetch asset js file')
            live_video_key, live_video_url = self._search_regex(
                r'LIVE_VIDEO_key:\s*"(?P<key>[\dA-Z]{64})".+LIVE_VIDEO_url:\s*"(?P<url>https://[^"]+)"',
                asset_js_content, name='live video info', group=('key', 'url'), default=(None, None))
            if live_video_key and live_video_url:
                break
        if not live_video_key or not live_video_url:
            raise ExtractorError('Cannot find live video info', expected=True)

        a_string = 'just a meaningless but non-empty string'
        bearer_token = hashlib.sha256((live_video_key + a_string).encode()).hexdigest().upper()

        live_video_json = self._download_json(
            live_video_url, video_id=video_id, query={'hash': a_string},
            note='Fetching playlist json', errnote='Unable to fetch playlist json',
            headers={'Authorization': f'Bearer {bearer_token}'})

        m3u8_url = live_video_json.get('url')
        if not m3u8_url:
            formats = []
            live_status = 'is_upcoming'
        else:
            formats = self._extract_m3u8_formats(m3u8_url, video_id=video_id, ext='ts')
            live_status = 'is_live'

        return {
            'id': video_id,
            'title': 'MixBox',
            'formats': formats,
            'live_status': live_status,
        }


class MixBoxCampaignIE(InfoExtractor):
    IE_NAME = 'MixBox:campaign'
    IE_DESC = 'ミックスボックス：イベント'
    _VALID_URL = r'https?://mixbox\.live/(?:campaign|campaign_live)/(?P<id>\d{3,})$'
    _TESTS = [{
        'url': 'https://mixbox.live/campaign/023',
        'info_dict': {
            'id': '023',
            'ext': 'mp4',
        },
        'skip': 'This event is too old to be supported',
    }, {
        'url': 'https://mixbox.live/campaign_live/039',
        'info_dict': {
            'id': '039',
            'ext': 'mp4',
        },
        'skip': 'This event has ended',
    }, {
        'url': 'https://mixbox.live/campaign/046',
        'info_dict': {
            'id': '046',
            'title': 'MixBox 『ウマ娘 プリティーダービー WINNING LIVE 10』発売記念イベント',
            'ext': 'mp4',
            'live_status': 'was_live',
        },
    }, {
        'url': 'https://mixbox.live/campaign_live/046',
        'info_dict': {
            'id': '046',
            'title': 'MixBox 『ウマ娘 プリティーダービー WINNING LIVE 10』発売記念イベント',
            'ext': 'mp4',
            'live_status': 'was_live',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        if int_or_none(video_id, default=-1) < 39:
            raise ExtractorError('This event is too old to be supported', expected=True)
        # In the webpage of the non-existing 47th event, I've seen new data structure. Sigh...

        webpage = self._download_webpage(f'https://mixbox.live/campaign_live/{video_id}', video_id)
        title = self._html_search_regex(
            r'<section class="campaign__section" data-v-\w+><p class="campaign__heading-first" data-v-\w+>(.+?)</p>',
            webpage, 'title')
        asset_js_urls = re.findall(r'<script src="(/assets/.+?\.js)"', webpage)

        asset_js_content = ''
        info_json = {}
        for asset_js_url in asset_js_urls:
            asset_js_content = self._download_webpage(
                f'https://mixbox.live/{asset_js_url}', video_id,
                note='Fetching asset js file', errnote='Unable to fetch asset js file')
            info_json = self._search_json(
                r'data:\s*function\(\)\s*{\s*return\s*', asset_js_content, 'data', video_id,
                contains_pattern=r'\{event:.+movieStatus:.+', transform_source=js_to_json, default={})
            if info_json:
                break
        if not info_json:
            raise ExtractorError('Cannot find event info', expected=True)

        _, archive_start_datetime, _, archive_end_datetime = self._search_regex(
            r'openArchiveTimer\s*\(\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)"',
            asset_js_content, 'archive info', group=(1, 2, 3, 4))

        archive_start_timestamp = int_or_none(unified_timestamp(archive_start_datetime, day_first=False))
        archive_end_timestamp = int_or_none(unified_timestamp(archive_end_datetime, day_first=False))
        if not archive_start_timestamp or not archive_end_timestamp:
            raise ExtractorError('Wrong timestamps in archive info', expected=True)

        timestamp_now = time_seconds(hours=9)
        if timestamp_now > archive_end_timestamp:
            raise ExtractorError('This event has ended', expected=True)
        elif timestamp_now > archive_start_timestamp:
            live_status = 'was_live'
        else:
            # TODO: support live streaming and upcoming live streaming
            raise ExtractorError('Downloading live streaming is not yet supported. PR is welcomed', expected=True)

        formats = []

        if live_status == 'was_live':
            src_archive_url = traverse_obj(info_json, ('event', 'srcArchive'))
            if not src_archive_url:
                raise ExtractorError('Unable to extract archive url', expected=True)

            archive_authorization_info_page = self._download_webpage(
                src_archive_url, video_id, headers={'Referer': 'https://mixbox.live/'},
                note='Fetching archive authorization info', errnote='Unable to fetch archive authorization info')
            authtoken, tenant_id, episode_aid = self._search_regex(
                r'data-authtoken="([^"]+)"\s+data-tenant_id="([^"]+)"\s+data-episode_id="([^"]+)"\s+',
                archive_authorization_info_page, 'archive authorization info', group=(1, 2, 3))

            play_params_json = self._download_json(
                'https://npfbgn.b-ch.com/api/episode/playparam', video_id,
                query={
                    'authtoken': authtoken,
                    'tenant_id': tenant_id,
                    'episode_aid': episode_aid,
                },
                note='Fetching play parameters', errnote='Unable to fetch play parameters')

            m3u8_url = traverse_obj(play_params_json, ('data', 'playparam', 'url'))
            title = traverse_obj(play_params_json, ('data', 'display_title'), default=title)

            if m3u8_url:
                formats = self._extract_m3u8_formats(m3u8_url, video_id=video_id)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'live_status': live_status,
        }
