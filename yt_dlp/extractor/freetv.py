import itertools
import re

from .common import InfoExtractor
from ..utils import int_or_none, traverse_obj, urlencode_postdata


class FreeTvBaseIE(InfoExtractor):
    def _get_api_response(self, content_id, resource_type, postdata):
        return self._download_json(
            'https://www.freetv.com/wordpress/wp-admin/admin-ajax.php',
            content_id, data=urlencode_postdata(postdata),
            note=f'Downloading {content_id} {resource_type} JSON')['data']


class FreeTvMoviesIE(FreeTvBaseIE):
    _VALID_URL = r'https?://(?:www\.)?freetv\.com/peliculas/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://www.freetv.com/peliculas/atrapame-si-puedes/',
        'md5': 'dc62d5abf0514726640077cd1591aa92',
        'info_dict': {
            'id': '428021',
            'title': 'Atrápame Si Puedes',
            'description': 'md5:ca63bc00898aeb2f64ec87c6d3a5b982',
            'ext': 'mp4',
        }
    }, {
        'url': 'https://www.freetv.com/peliculas/monstruoso/',
        'md5': '509c15c68de41cb708d1f92d071f20aa',
        'info_dict': {
            'id': '377652',
            'title': 'Monstruoso',
            'description': 'md5:333fc19ee327b457b980e54a911ea4a3',
            'ext': 'mp4',
        }
    }]

    def _extract_video(self, content_id, action='olyott_video_play'):
        api_response = self._get_api_response(content_id, 'video', {
            'action': action,
            'contentID': content_id,
        })

        video_id, video_url = api_response['displayMeta']['contentID'], api_response['displayMeta']['streamURLVideo']
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(video_url, video_id, 'mp4')
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': traverse_obj(api_response, ('displayMeta', 'title')),
            'description': traverse_obj(api_response, ('displayMeta', 'desc')),
            'formats': formats,
            'subtitles': subtitles,
        }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        return self._extract_video(
            self._search_regex((
                r'class=["\'][^>]+postid-(?P<video_id>\d+)',
                r'<link[^>]+freetv.com/\?p=(?P<video_id>\d+)',
                r'<div[^>]+data-params=["\'][^>]+post_id=(?P<video_id>\d+)',
            ), webpage, 'video id', group='video_id'))


class FreeTvIE(FreeTvBaseIE):
    IE_NAME = 'freetv:series'
    _VALID_URL = r'https?://(?:www\.)?freetv\.com/series/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://www.freetv.com/series/el-detective-l/',
        'info_dict': {
            'id': 'el-detective-l',
            'title': 'El Detective L',
            'description': 'md5:f9f1143bc33e9856ecbfcbfb97a759be'
        },
        'playlist_count': 24,
    }, {
        'url': 'https://www.freetv.com/series/esmeraldas/',
        'info_dict': {
            'id': 'esmeraldas',
            'title': 'Esmeraldas',
            'description': 'md5:43d7ec45bd931d8268a4f5afaf4c77bf'
        },
        'playlist_count': 62,
    }, {
        'url': 'https://www.freetv.com/series/las-aventuras-de-leonardo/',
        'info_dict': {
            'id': 'las-aventuras-de-leonardo',
            'title': 'Las Aventuras de Leonardo',
            'description': 'md5:0c47130846c141120a382aca059288f6'
        },
        'playlist_count': 13,
    },
    ]

    def _extract_series_season(self, season_id, series_title):
        episodes = self._get_api_response(season_id, 'series', {
            'contentID': season_id,
            'action': 'olyott_get_dynamic_series_content',
            'type': 'list',
            'perPage': '1000',
        })['1']

        for episode in episodes:
            video_id = str(episode['contentID'])
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(episode['streamURL'], video_id, 'mp4')
            self._sort_formats(formats)

            yield {
                'id': video_id,
                'title': episode.get('fullTitle'),
                'description': episode.get('description'),
                'formats': formats,
                'subtitles': subtitles,
                'thumbnail': episode.get('thumbnail'),
                'series': series_title,
                'series_id': traverse_obj(episode, ('contentMeta', 'displayMeta', 'seriesID')),
                'season_id': traverse_obj(episode, ('contentMeta', 'displayMeta', 'seasonID')),
                'season_number': traverse_obj(
                    episode, ('contentMeta', 'displayMeta', 'seasonNum'), expected_type=int_or_none),
                'episode_number': traverse_obj(
                    episode, ('contentMeta', 'displayMeta', 'episodeNum'), expected_type=int_or_none),
            }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        title = self._html_search_regex(
            r'<h1[^>]+class=["\']synopis[^>]>(?P<title>[^<]+)', webpage, 'title', group='title', fatal=False)
        description = self._html_search_regex(
            r'<div[^>]+class=["\']+synopis content[^>]><p>(?P<description>[^<]+)',
            webpage, 'description', group='description', fatal=False)

        return self.playlist_result(
            itertools.chain.from_iterable(
                self._extract_series_season(season_id, title)
                for season_id in re.findall(r'<option[^>]+value=["\'](\d+)["\']', webpage)),
            display_id, title, description)
