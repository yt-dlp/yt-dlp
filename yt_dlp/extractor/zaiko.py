import json
import html
import re

from .common import InfoExtractor
from ..utils import traverse_obj


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
            attrs[remove_start(key, ':')] = self._parse_json(
                value, video_id, transform_source=unescapeHTML, fatal=False)
        return attrs

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage, urlh = self._download_webpage_handle(url, video_id)
        if 'zaiko.io/login' in urlh.geturl():
            self.raise_login_required()
        stream_meta = self._parse_vue_element_attr('stream-page', webpage)

        headers = {'referer': 'https://zaiko.io/'}
        player_page = self._download_webpage(stream_meta['stream-access']['video_source'], video_id, headers=headers)
        player_meta = self._parse_vue_element_attr('player', player_page)

        return {
            'id': video_id,
            'title': stream_meta['event']['name'],
            "alt_title": traverse_obj(player_meta, ("initial_event_info", "title")),
            'formats': self._extract_m3u8_formats(player_meta["initial_event_info"]["endpoint"], video_id),
            "thumbnail": traverse_obj(player_meta, ("initial_event_info", "poster_url")),
            "uploader": traverse_obj(stream_meta, ("profile", "name")),
            "timestamp": traverse_obj(stream_meta, ("stream", "start", "timestamp")),
            "release_timestamp": traverse_obj(stream_meta, ("stream", "start", "timestamp")),
            "uploader_id": traverse_obj(stream_meta, ("profile", "id")),
            "categories": traverse_obj(stream_meta, ("event", "genres")),
            "_raw": [stream_meta, player_meta],
        }
