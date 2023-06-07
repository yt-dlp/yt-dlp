from .common import InfoExtractor
from ..utils import (
    traverse_obj,
    extract_attributes,
    remove_start,
    unescapeHTML,
    url_or_none,
    str_or_none,
    int_or_none,
)


class ZaikoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?zaiko\.io/event/(?P<id>\d+)/stream(?:/\d+)+'
    _TESTS = [{
        'url': 'https://zaiko.io/event/324868/stream/20571/20571',
        'info_dict': {
            'id': 324868,
            'ext': 'mp4',
            'title': 'ZAIKO STREAMING TEST',
            'uploader_id': 454,
            'timestamp': 1583809200,
        }
    }]

    def _parse_vue_element_attr(self, name, string, video_id):
        page_elem = self._search_regex(rf'(<{name}[^>]+>)', string, name)
        attrs = {}
        for key, value in extract_attributes(page_elem).items():
            if key[0] == ':':
                attrs[remove_start(key, ':')] = self._parse_json(
                    value, video_id, transform_source=unescapeHTML, fatal=False)
            else:
                attrs[key] = value
        return attrs

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage, urlh = self._download_webpage_handle(url, video_id)
        if 'zaiko.io/login' in urlh.geturl():
            self.raise_login_required()
        stream_meta = self._parse_vue_element_attr('stream-page', webpage, video_id)

        player_page = self._download_webpage(
            stream_meta['stream-access']['video_source'], video_id,
            'Downloading player page', headers={'referer': 'https://zaiko.io/'})
        player_meta = self._parse_vue_element_attr('player', player_page, video_id)

        return {
            'id': video_id,
            'formats': self._extract_m3u8_formats(
                player_meta['initial_event_info']['endpoint'], video_id),
            **traverse_obj(stream_meta, {
                'title': ('event', 'name', {str}),
                'uploader': ('profile', 'name', {str}),
                'uploader_id': ('profile', 'id', {str_or_none}),
                'timestamp': ('stream', 'start', 'timestamp', {int_or_none}),
                'release_timestamp': ('stream', 'start', 'timestamp', {int_or_none}),
                'categories': ('event', 'genres', ..., {lambda x: x or None}),
            }),
            **traverse_obj(player_meta, ('initial_event_info', {
                'alt_title': ('title', {str}),
                'thumbnail': ('poster_url', {url_or_none}),
            })),
        }
