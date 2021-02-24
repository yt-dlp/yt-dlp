# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_age_limit,
    str_or_none,
    try_get,
    unified_strdate,
    unified_timestamp,
    url_or_none,
)


class Zee5IE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?zee5\.com/[^#?]*/(?P<display_id>[-\w]+)/(?P<id>[-\d]+)'
    _TESTS = [{
        'url': 'https://www.zee5.com/movies/details/krishna-the-birth/0-0-63098',
        'info_dict': {
            "id": "0-0-63098",
            "ext": "m3u8",
            "display_id": "krishna-the-birth",
            "title": "Krishna - The Birth",
            "duration": 4368,
            "average_rating": 4,
            "description": str,
            "alt_title": "Krishna - The Birth",
            "uploader": "Zee Entertainment Enterprises Ltd",
            "release_date": "20060101",
            "upload_date": "20060101",
            "timestamp": 1136073600,
            "thumbnail": "https://akamaividz.zee5.com/resources/0-0-63098/list/270x152/0063098_list_80888170.jpg",
            "tags": list
        },
        'params': {
            'format': 'bv',
        },
    }, {
        'url': 'https://zee5.com/tvshows/details/krishna-balram/0-6-1871/episode-1-the-test-of-bramha/0-1-233402',
        'info_dict': {
            "id": "0-1-233402",
            'ext': 'm3u8',
            "display_id": "episode-1-the-test-of-bramha",
            "title": "Episode 1 - The Test Of Bramha",
            "duration": 1336,
            "average_rating": 4,
            "description": str,
            "alt_title": "Episode 1 - The Test Of Bramha",
            "uploader": "Green Gold",
            "release_date": "20090101",
            "upload_date": "20090101",
            "timestamp": 1230768000,
            "thumbnail": "https://akamaividz.zee5.com/resources/0-1-233402/list/270x152/01233402_list.jpg",
            "series": "Krishna Balram",
            "season_number": 1,
            "episode_number": 1,
            "tags": list,
        },
        'params': {
            'format': 'bv',
        },
    }]

    def _real_extract(self, url):
        video_id, display_id = re.match(self._VALID_URL, url).group('id', 'display_id')
        access_token_request = self._download_json(
            'https://useraction.zee5.com/token/platform_tokens.php?platform_name=web_app',
            video_id, note="Downloading access token")
        token_request = self._download_json(
            'https://useraction.zee5.com/tokennd',
            video_id, note="Downloading video token")
        json_data = self._download_json(
            'https://gwapi.zee5.com/content/details/{}?translation=en&country=IN'.format(video_id),
            video_id, headers={'X-Access-Token': access_token_request['token']})
        m3u8_url = try_get(
            json_data,
            (lambda x: x['hls'][0], lambda x: x['video_details']['hls_url']),
            str)
        formats = self._extract_m3u8_formats(
            'https://zee5vodnd.akamaized.net' + m3u8_url.replace('/drm1/', '/hls1/') + token_request['video_token'],
            video_id, fatal=False)
        mpd_url = try_get(
            json_data,
            (lambda x: x['video'][0], lambda x: x['video_details']['url']),
            str)
        formats += self._extract_mpd_formats(
            'https://zee5vodnd.akamaized.net' + mpd_url + token_request['video_token'],
            video_id, fatal=False)

        self._sort_formats(formats)
        return {
            'id': video_id,
            'display_id': display_id,
            'title': json_data['title'],
            'formats': formats,
            'duration': int_or_none(json_data.get('duration')),
            'average_rating': int_or_none(json_data.get('rating')),
            'description': str_or_none(json_data.get('description')),
            'alt_title': str_or_none(json_data.get('original_title')),
            'uploader': str_or_none(json_data.get('content_owner')),
            'age_limit': parse_age_limit(json_data.get('age_rating')),
            'release_date': unified_strdate(json_data.get('release_date')),
            'timestamp': unified_timestamp(json_data.get('release_date')),
            'thumbnail': url_or_none(json_data.get('image_url')),
            'series': try_get(json_data, lambda x: x['tvshow_details']['title'], str),
            'season': try_get(json_data, lambda x: x['season_details']['title'], str),
            'season_number': int_or_none(try_get(json_data, lambda x: x['season_details']['index'])),
            'episode_number': int_or_none(try_get(json_data, lambda x: x['index'])),
            'tags': try_get(json_data, lambda x: x['tags'], list)
        }
