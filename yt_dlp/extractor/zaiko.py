import base64
import contextlib
import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    extract_attributes,
    parse_iso8601,
    str_or_none,
    try_call,
    url_or_none,
)
from ..utils.traversal import require, traverse_obj


class ZaikoBaseIE(InfoExtractor):
    def _download_real_webpage(self, url, video_id):
        webpage, urlh = self._download_webpage_handle(url, video_id)
        final_url = urlh.url
        if 'zaiko.io/login' in final_url:
            self.raise_login_required()
        elif '/_buy/' in final_url:
            raise ExtractorError('Your account does not have tickets to this event', expected=True)
        return webpage

    def _parse_vue_element_attr(self, name, string, video_id):
        page_elem = self._search_regex(
            rf'(<{name}\b(?:[^>"\']+|"[^"]*"|\'[^\']*\')+>)', string, name)

        attrs = {}
        for key, value in extract_attributes(page_elem).items():
            if key.startswith(':'):
                with contextlib.suppress(ValueError):
                    value = json.loads(value)
            attrs[key] = value
        return attrs


class ZaikoIE(ZaikoBaseIE):
    IE_NAME = 'zaiko'
    IE_DESC = 'ZAIKO'

    _HEADERS = {
        'Origin': 'https://live.zaiko.services',
        'Referer': 'https://live.zaiko.services/',
    }
    _VALID_URL = r'https?://(?:[\w-]+\.)?zaiko\.io/event/(?P<id>\d+)/stream(?:/\d+)+'
    _TESTS = [{
        'url': 'https://zaiko.io/event/369121/stream/153826/156172',
        'info_dict': {
            'id': '369121',
            'ext': 'mp4',
            'title': '【ZAIKO】視聴テスト用イベント',
            'alt_title': '【ZAIKO】視聴テスト用イベント',
            'display_id': '156172',
            'live_status': 'was_live',
            'release_date': '20250106',
            'release_timestamp': 1736132400,
            'thumbnail': r're:https?://.+',
            'uploader': 'ZCS_Ops',
            'uploader_id': 'cs-strmngopstest',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://zaiko.io/event/380198/stream/193215/166068',
        'info_dict': {
            'id': '380198',
            'ext': 'mp4',
            'title': '飯田ヒカルの3時間クッキング＜ゲスト：小鹿なお・伊藤舞音・浅見香月＞',
            'alt_title': '飯田ヒカルの3時間クッキング＜ゲスト：小鹿なお・伊藤舞音・浅見香月＞',
            'display_id': '166068',
            'live_status': 'was_live',
            'release_date': '20260330',
            'release_timestamp': 1774866600,
            'thumbnail': r're:https?://.+',
            'uploader': 'ボイスガレッジチャンネル',
            'uploader_id': 'voicegarage',
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'Paid video',
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_real_webpage(url, video_id)

        stream_meta = self._parse_vue_element_attr('stream-page', webpage, video_id)
        video_source = traverse_obj(stream_meta, (
            ':stream-access', 'video_source', {url_or_none}))
        player_page = self._download_webpage(
            video_source, video_id, headers={'Referer': 'https://zaiko.io/'})

        player_meta = self._parse_vue_element_attr('player', player_page, video_id)
        initial_info = traverse_obj(player_meta, (':initial_event_info', {dict})) or {}
        status = traverse_obj(initial_info, ('status', {str}))
        live_status = {
            'live': 'is_live',
            'vod': 'was_live',
            'waiting': 'is_upcoming',
        }.get(status)

        scheduled_time = traverse_obj(stream_meta, (':stream', 'start', 'iso', {str}))
        release_timestamp = parse_iso8601(scheduled_time)
        if live_status == 'is_upcoming':
            self.raise_no_formats(
                f'This livestream is scheduled to start at {scheduled_time}', expected=True)

            return {
                'id': video_id,
                'live_status': live_status,
                'release_timestamp': release_timestamp,
            }

        if live_status not in ('is_live', 'was_live'):
            err_msg = {
                'archiving': 'VOD is still being processed',
                'cancelled': 'Event has been cancelled',
                'deleted': 'Event has ended',
                'deleting': 'Event has ended',
                'disconnected': 'Stream has been disconnected',
                'error': 'Event has ended',
                'live_to_disconnected': 'Stream has been disconnected',
            }.get(status)

            raise ExtractorError(
                err_msg or f'Unknown status: {status}', expected=err_msg is not None)

        if is_jwt_protected := traverse_obj(initial_info, (
            'is_jwt_protected', {bool},
        )):
            token = self._download_json(
                initial_info['jwt_token_url'], video_id, headers=self._HEADERS)
            m3u8_url = traverse_obj(token, (
                'playback_url', {url_or_none}, {require('signed m3u8 URL')}))
        else:
            m3u8_url = traverse_obj(initial_info, (
                'endpoint', {url_or_none}, {require('m3u8 URL')}))

        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4')
        if is_jwt_protected:
            for fmt in formats:
                fmt['protocol'] = 'zaiko'

        return {
            'id': video_id,
            'display_id': traverse_obj(stream_meta, (':stream', 'id', {str_or_none})),
            'downloader_options': {
                'referer': video_source,
                **traverse_obj(player_meta, {
                    'event_id': ('event_id', {str}),
                    'external_id': ('external_id', {str}),
                }),
            },
            'formats': formats,
            'http_headers': self._HEADERS,
            'live_status': live_status,
            'release_timestamp': release_timestamp,
            **traverse_obj(initial_info, {
                'alt_title': ('title', {clean_html}, filter),
                'thumbnail': ('poster_url', {url_or_none}),
            }),
            **traverse_obj(stream_meta, (':event', {
                'title': ('name', {clean_html}, filter),
                'categories': ('genres', ..., filter, all, filter),
            })),
            **traverse_obj(stream_meta, (':profile', {
                'uploader': ('name', {clean_html}, filter),
                'uploader_id': ('whitelabel', {str}),
            })),
        }


class ZaikoETicketIE(ZaikoBaseIE):
    _VALID_URL = r'https?://(?:www.)?zaiko\.io/account/eticket/(?P<id>[\w=-]{49})'
    _TESTS = [{
        'url': 'https://zaiko.io/account/eticket/TZjMwMzQ2Y2EzMXwyMDIzMDYwNzEyMTMyNXw1MDViOWU2Mw==',
        'playlist_count': 1,
        'info_dict': {
            'id': 'f30346ca31-20230607121325-505b9e63',
            'title': 'ZAIKO STREAMING TEST',
            'thumbnail': r're:https?://.+',
        },
        'skip': 'Ticket holders only',
    }]

    def _real_extract(self, url):
        ticket_id = self._match_id(url)
        ticket_id = try_call(
            lambda: base64.urlsafe_b64decode(ticket_id[1:]).decode().replace('|', '-')) or ticket_id

        webpage = self._download_real_webpage(url, ticket_id)
        eticket = self._parse_vue_element_attr('eticket', webpage, ticket_id)

        return self.playlist_result([
            self.url_result(stream, ZaikoIE)
            for stream in traverse_obj(eticket, (':streams', ..., 'url', {url_or_none}))
        ], ticket_id, **traverse_obj(eticket, (':ticket-details', {
            'title': ('event_name', {clean_html}, filter),
            'thumbnail': ('event_img_url', {url_or_none}),
        })))
