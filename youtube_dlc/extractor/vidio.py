# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
    str_or_none,
    strip_or_none,
    try_get,
)


class VidioIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?vidio\.com/watch/(?P<id>\d+)-(?P<display_id>[^/?#&]+)'
    _TESTS = [{
        'url': 'http://www.vidio.com/watch/165683-dj_ambred-booyah-live-2015',
        'md5': 'cd2801394afc164e9775db6a140b91fe',
        'info_dict': {
            'id': '165683',
            'display_id': 'dj_ambred-booyah-live-2015',
            'ext': 'mp4',
            'title': 'DJ_AMBRED - Booyah (Live 2015)',
            'description': 'md5:27dc15f819b6a78a626490881adbadf8',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 149,
            'like_count': int,
            'uploader': 'TWELVE Pic',
            'timestamp': 1444902800,
            'upload_date': '20151015',
            'uploader_id': 'twelvepictures',
            'channel': 'Cover Music Video',
            'channel_id': '280236',
            'view_count': int,
            'dislike_count': int,
            'comment_count': int,
            'tags': 'count:4',
        },
    }, {
        'url': 'https://www.vidio.com/watch/77949-south-korea-test-fires-missile-that-can-strike-all-of-the-north',
        'only_matching': True,
    }]

    def _real_initialize(self):
        self._api_key = self._download_json(
            'https://www.vidio.com/auth', None, data=b'')['api_key']

    def _real_extract(self, url):
        video_id, display_id = re.match(self._VALID_URL, url).groups()
        data = self._download_json(
            'https://api.vidio.com/videos/' + video_id, display_id, headers={
                'Content-Type': 'application/vnd.api+json',
                'X-API-KEY': self._api_key,
            })
        video = data['videos'][0]
        title = video['title'].strip()

        formats = self._extract_m3u8_formats(
            data['clips'][0]['hls_url'], display_id, 'mp4', 'm3u8_native')
        self._sort_formats(formats)

        get_first = lambda x: try_get(data, lambda y: y[x + 's'][0], dict) or {}
        channel = get_first('channel')
        user = get_first('user')
        username = user.get('username')
        get_count = lambda x: int_or_none(video.get('total_' + x))

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': strip_or_none(video.get('description')),
            'thumbnail': video.get('image_url_medium'),
            'duration': int_or_none(video.get('duration')),
            'like_count': get_count('likes'),
            'formats': formats,
            'uploader': user.get('name'),
            'timestamp': parse_iso8601(video.get('created_at')),
            'uploader_id': username,
            'uploader_url': 'https://www.vidio.com/@' + username if username else None,
            'channel': channel.get('name'),
            'channel_id': str_or_none(channel.get('id')),
            'view_count': get_count('view_count'),
            'dislike_count': get_count('dislikes'),
            'comment_count': get_count('comments'),
            'tags': video.get('tag_list'),
        }
