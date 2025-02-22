import base64

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    extract_attributes,
    int_or_none,
    str_or_none,
    traverse_obj,
    try_call,
    unescapeHTML,
    url_basename,
    url_or_none,
)


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
        page_elem = self._search_regex(rf'(<{name}[^>]+>)', string, name)
        attrs = {}
        for key, value in extract_attributes(page_elem).items():
            if key.startswith(':'):
                attrs[key[1:]] = self._parse_json(
                    value, video_id, transform_source=unescapeHTML, fatal=False)
        return attrs


class ZaikoIE(ZaikoBaseIE):
    _VALID_URL = r'https?://(?:[\w-]+\.)?zaiko\.io/event/(?P<id>\d+)/stream(?:/\d+)+'
    _TESTS = [{
        'url': 'https://zaiko.io/event/324868/stream/20571/20571',
        'info_dict': {
            'id': '324868',
            'ext': 'mp4',
            'title': 'ZAIKO STREAMING TEST',
            'alt_title': '[VOD] ZAIKO STREAMING TEST_20210603(Do Not Delete)',
            'uploader_id': '454',
            'uploader': 'ZAIKO ZERO',
            'release_timestamp': 1583809200,
            'thumbnail': r're:^https://[\w.-]+/\w+/\w+',
            'thumbnails': 'maxcount:2',
            'release_date': '20200310',
            'categories': ['Tech House'],
            'live_status': 'was_live',
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'Your account does not have tickets to this event',
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_real_webpage(url, video_id)
        stream_meta = self._parse_vue_element_attr('stream-page', webpage, video_id)

        player_page = self._download_webpage(
            stream_meta['stream-access']['video_source'], video_id,
            'Downloading player page', headers={'referer': 'https://zaiko.io/'})
        player_meta = self._parse_vue_element_attr('player', player_page, video_id)
        initial_event_info = traverse_obj(player_meta, ('initial_event_info', {dict})) or {}

        status = traverse_obj(initial_event_info, ('status', {str}))
        live_status, msg, expected = {
            'vod': ('was_live', 'No VOD stream URL was found', False),
            'archiving': ('post_live', 'Event VOD is still being processed', True),
            'deleting': ('post_live', 'This event has ended', True),
            'deleted': ('post_live', 'This event has ended', True),
            'error': ('post_live', 'This event has ended', True),
            'disconnected': ('post_live', 'Stream has been disconnected', True),
            'live_to_disconnected': ('post_live', 'Stream has been disconnected', True),
            'live': ('is_live', 'No livestream URL found was found', False),
            'waiting': ('is_upcoming', 'Live event has not yet started', True),
            'cancelled': ('not_live', 'Event has been cancelled', True),
        }.get(status) or ('not_live', f'Unknown event status "{status}"', False)

        if traverse_obj(initial_event_info, ('is_jwt_protected', {bool})):
            stream_url = self._download_json(
                initial_event_info['jwt_token_url'], video_id, 'Downloading JWT-protected stream URL',
                'Failed to download JWT-protected stream URL')['playback_url']
        else:
            stream_url = traverse_obj(initial_event_info, ('endpoint', {url_or_none}))

        formats = self._extract_m3u8_formats(
            stream_url, video_id, live=True, fatal=False) if stream_url else []
        if not formats:
            self.raise_no_formats(msg, expected=expected)

        thumbnail_urls = [
            traverse_obj(initial_event_info, ('poster_url', {url_or_none})),
            self._og_search_thumbnail(self._download_webpage(
                f'https://zaiko.io/event/{video_id}', video_id, 'Downloading event page', fatal=False) or ''),
        ]

        return {
            'id': video_id,
            'formats': formats,
            'live_status': live_status,
            **traverse_obj(stream_meta, {
                'title': ('event', 'name', {str}),
                'uploader': ('profile', 'name', {str}),
                'uploader_id': ('profile', 'id', {str_or_none}),
                'release_timestamp': ('stream', 'start', 'timestamp', {int_or_none}),
                'categories': ('event', 'genres', ..., filter),
            }),
            'alt_title': traverse_obj(initial_event_info, ('title', {str})),
            'thumbnails': [{'url': url, 'id': url_basename(url)} for url in thumbnail_urls if url_or_none(url)],
        }


class ZaikoETicketIE(ZaikoBaseIE):
    _VALID_URL = r'https?://(?:www.)?zaiko\.io/account/eticket/(?P<id>[\w=-]{49})'
    _TESTS = [{
        'url': 'https://zaiko.io/account/eticket/TZjMwMzQ2Y2EzMXwyMDIzMDYwNzEyMTMyNXw1MDViOWU2Mw==',
        'playlist_count': 1,
        'info_dict': {
            'id': 'f30346ca31-20230607121325-505b9e63',
            'title': 'ZAIKO STREAMING TEST',
            'thumbnail': 'https://media.zkocdn.net/pf_1/1_3wdyjcjyupseatkwid34u',
        },
        'skip': 'Only available with the ticketholding account',
    }]

    def _real_extract(self, url):
        ticket_id = self._match_id(url)
        ticket_id = try_call(
            lambda: base64.urlsafe_b64decode(ticket_id[1:]).decode().replace('|', '-')) or ticket_id

        webpage = self._download_real_webpage(url, ticket_id)
        eticket = self._parse_vue_element_attr('eticket', webpage, ticket_id)

        return self.playlist_result(
            [self.url_result(stream, ZaikoIE) for stream in traverse_obj(eticket, ('streams', ..., 'url'))],
            ticket_id, **traverse_obj(eticket, ('ticket-details', {
                'title': 'event_name',
                'thumbnail': 'event_img_url',
            })))
