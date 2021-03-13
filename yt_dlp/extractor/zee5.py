# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_str
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
    _VALID_URL = r'''(?x)
                     (?:
                        zee5:|
                        (?:https?://)(?:www\.)?zee5\.com/(?:[^#?]+/)?
                        (?:
                            (?:tvshows|kids|zee5originals)(?:/[^#/?]+){3}
                            |movies/[^#/?]+
                        )/(?P<display_id>[^#/?]+)/
                     )
                     (?P<id>[^#/?]+)/?(?:$|[?#])
                     '''
    _TESTS = [{
        'url': 'https://www.zee5.com/movies/details/krishna-the-birth/0-0-63098',
        'info_dict': {
            'id': '0-0-63098',
            'ext': 'mp4',
            'display_id': 'krishna-the-birth',
            'title': 'Krishna - The Birth',
            'duration': 4368,
            'average_rating': 4,
            'description': str,
            'alt_title': 'Krishna - The Birth',
            'uploader': 'Zee Entertainment Enterprises Ltd',
            'release_date': '20060101',
            'upload_date': '20060101',
            'timestamp': 1136073600,
            'thumbnail': 'https://akamaividz.zee5.com/resources/0-0-63098/list/270x152/0063098_list_80888170.jpg',
            'tags': list
        },
        'params': {
            'format': 'bv',
        },
    }, {
        'url': 'https://zee5.com/tvshows/details/krishna-balram/0-6-1871/episode-1-the-test-of-bramha/0-1-233402',
        'info_dict': {
            'id': '0-1-233402',
            'ext': 'mp4',
            'display_id': 'episode-1-the-test-of-bramha',
            'title': 'Episode 1 - The Test Of Bramha',
            'duration': 1336,
            'average_rating': 4,
            'description': str,
            'alt_title': 'Episode 1 - The Test Of Bramha',
            'uploader': 'Green Gold',
            'release_date': '20090101',
            'upload_date': '20090101',
            'timestamp': 1230768000,
            'thumbnail': 'https://akamaividz.zee5.com/resources/0-1-233402/list/270x152/01233402_list.jpg',
            'series': 'Krishna Balram',
            'season_number': 1,
            'episode_number': 1,
            'tags': list,
        },
        'params': {
            'format': 'bv',
        },
    }, {
        'url': 'https://www.zee5.com/hi/tvshows/details/kundali-bhagya/0-6-366/kundali-bhagya-march-08-2021/0-1-manual_7g9jv1os7730?country=IN',
        'only_matching': True
    }, {
        'url': 'https://www.zee5.com/global/hi/tvshows/details/kundali-bhagya/0-6-366/kundali-bhagya-march-08-2021/0-1-manual_7g9jv1os7730',
        'only_matching': True
    }]

    def _real_extract(self, url):
        video_id, display_id = re.match(self._VALID_URL, url).group('id', 'display_id')
        access_token_request = self._download_json(
            'https://useraction.zee5.com/token/platform_tokens.php?platform_name=web_app',
            video_id, note='Downloading access token')
        token_request = self._download_json(
            'https://useraction.zee5.com/tokennd',
            video_id, note='Downloading video token')
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


class Zee5SeriesIE(InfoExtractor):
    IE_NAME = 'zee5:series'
    _VALID_URL = r'''(?x)
                     (?:
                        zee5:series:|
                        (?:https?://)(?:www\.)?zee5\.com/(?:[^#?]+/)?
                        (?:tvshows|kids|zee5originals)(?:/[^#/?]+){2}/
                     )
                     (?P<id>[^#/?]+)/?(?:$|[?#])
                     '''
    _TESTS = [{
        'url': 'https://www.zee5.com/kids/kids-shows/krishna-balram/0-6-1871',
        'playlist_mincount': 43,
        'info_dict': {
            'id': '0-6-1871',
        },
    }, {
        'url': 'https://www.zee5.com/tvshows/details/bhabi-ji-ghar-par-hai/0-6-199',
        'playlist_mincount': 1500,
        'info_dict': {
            'id': '0-6-199',
        },
    }, {
        'url': 'https://www.zee5.com/tvshows/details/agent-raghav-crime-branch/0-6-965',
        'playlist_mincount': 25,
        'info_dict': {
            'id': '0-6-965',
        },
    }, {
        'url': 'https://www.zee5.com/ta/tvshows/details/nagabhairavi/0-6-3201',
        'playlist_mincount': 3,
        'info_dict': {
            'id': '0-6-3201',
        },
    }, {
        'url': 'https://www.zee5.com/global/hi/tvshows/details/khwaabon-ki-zamin-par/0-6-270',
        'playlist_mincount': 150,
        'info_dict': {
            'id': '0-6-270',
        },
    }
    ]

    def _entries(self, show_id):
        access_token_request = self._download_json(
            'https://useraction.zee5.com/token/platform_tokens.php?platform_name=web_app',
            show_id, note='Downloading access token')
        headers = {
            'X-Access-Token': access_token_request['token'],
            'Referer': 'https://www.zee5.com/',
        }
        show_url = 'https://gwapi.zee5.com/content/tvshow/{}?translation=en&country=IN'.format(show_id)

        page_num = 0
        show_json = self._download_json(show_url, video_id=show_id, headers=headers)
        for season in show_json.get('seasons') or []:
            season_id = try_get(season, lambda x: x['id'], compat_str)
            next_url = 'https://gwapi.zee5.com/content/tvshow/?season_id={}&type=episode&translation=en&country=IN&on_air=false&asset_subtype=tvshow&page=1&limit=100'.format(season_id)
            while next_url:
                page_num += 1
                episodes_json = self._download_json(
                    next_url, video_id=show_id, headers=headers,
                    note='Downloading JSON metadata page %d' % page_num)
                for episode in try_get(episodes_json, lambda x: x['episode'], list) or []:
                    video_id = episode.get('id')
                    yield self.url_result(
                        'zee5:%s' % video_id,
                        ie=Zee5IE.ie_key(), video_id=video_id)
                next_url = url_or_none(episodes_json.get('next_episode_api'))

    def _real_extract(self, url):
        show_id = self._match_id(url)
        return self.playlist_result(self._entries(show_id), playlist_id=show_id)
