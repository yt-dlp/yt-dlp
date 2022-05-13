import re

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    ExtractorError,
    try_get,
    urlencode_postdata, int_or_none, str_or_none,
)


class FreeTvBaseIE(InfoExtractor):
    def _get_api_response(self, content_id, postdata, resource_type):
        response = self._download_json(
            'https://www.freetv.com/wordpress/wp-admin/admin-ajax.php',
            content_id, data=urlencode_postdata(postdata), fatal=False,
            note='Downloading {} {} JSON'.format(content_id, resource_type))

        if response is False:
            raise ExtractorError("Couldn't get response", expected=True)

        if response.get('data') is False:
            raise ExtractorError("Response doesn't contain {} data".format(resource_type), expected=True)

        return response

    def _extract_video(self, content_id, action="olyott_video_play"):
        api_response = self._get_api_response(content_id, {'action': action, 'contentID': content_id}, 'video')

        video_id = try_get(api_response, lambda x: x['data']['displayMeta']['contentID'], expected_type=str)
        title = try_get(api_response, lambda x: x['data']['displayMeta']['title'])
        description = try_get(api_response, lambda x: x['data']['displayMeta']['desc'])
        video_url = try_get(api_response, lambda x: x['data']['displayMeta']['streamURLVideo'], expected_type=str)

        ext = determine_ext(video_url)
        if ext != 'm3u8':
            raise ExtractorError('No manifest was found', video_id=video_id, expected=True)

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(video_url, video_id, 'mp4')
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'formats': formats,
            'subtitles': subtitles,
        }

    def _extract_series(self, display_id, season_ids, series_title, series_description,
                        action="olyott_get_dynamic_series_content"):
        entries = []
        for season_id in season_ids:
            api_response = self._get_api_response(
                season_id, resource_type='series',
                postdata={'action': action, 'contentID': season_id, 'type': 'list', 'perPage': '1000'})

            season_episodes = try_get(api_response, lambda x: x['data']['1'])

            if season_episodes is None:
                raise ExtractorError("Response doesn't contain episode list", expected=True)

            for episode in season_episodes:
                video_id = str_or_none(episode.get('contentID'))
                video_url = episode.get('streamURL')
                title = episode.get('fullTitle')
                description = episode.get('description')
                thumbnail = episode.get('thumbnail')

                series_id = try_get(episode, lambda x: x['contentMeta']['displayMeta']['seriesID'])
                season_id = try_get(episode, lambda x: x['contentMeta']['displayMeta']['seasonID'])
                season_number = int_or_none(try_get(episode, lambda x: x['contentMeta']['displayMeta']['seasonNum']))
                episode_number = int_or_none(try_get(episode, lambda x: x['contentMeta']['displayMeta']['episodeNum']))

                ext = determine_ext(video_url)
                if ext == "m3u8":
                    formats, subtitles = self._extract_m3u8_formats_and_subtitles(video_url, video_id, 'mp4', fatal=False)
                    self._sort_formats(formats)

                    entries.append({
                        'id': video_id,
                        'title': title,
                        'description': description,
                        'formats': formats,
                        'subtitles': subtitles,
                        'thumbnail': thumbnail,
                        'series': series_title,
                        'series_id': series_id,
                        'season_id': season_id,
                        'season_number': season_number,
                        'episode_number': episode_number,
                    })
                else:
                    print("No manifest was found for video_id {}".format(video_id))

        return self.playlist_result(entries, display_id, series_title, series_description)


class FreeTvMoviesIE(FreeTvBaseIE):
    _VALID_URL = r'https?://(?:www\.)?freetv\.com/(?:peliculas)/(?:[^/]+/)*(?P<id>[^/]+)'
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

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        content_id = self._search_regex(
            (r'class=["\'][^>]+postid-(?P<video_id>\d+)',
             r'<link[^>]+freetv.com/\?p=(?P<video_id>\d+)'
             r'<div[^>]+data-params=["\'][^>]+post_id=(?P<video_id>\d+)'),
            webpage, 'video_id', group='video_id')

        return self._extract_video(content_id)


class FreeTvSeriesIE(FreeTvBaseIE):
    _VALID_URL = r'https?://(?:www\.)?freetv\.com/(?:series)/(?:[^/]+/)*(?P<id>[^/]+)'
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

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        title = self._html_search_regex(
            r'<h1[^>]+class=["\']synopis[^>]>(?P<title>[^<]+)',
            webpage, 'title', fatal=False, group='title')
        description = self._html_search_regex(
            r'<div[^>]+class=["\']+synopis content[^>]><p>(?P<description>[^<]+)',
            webpage, 'title', fatal=False, group='description')

        season_ids = re.findall(r'<option[^>]+value=["\'](?P<content_id>\d+)["\']', webpage)

        return self._extract_series(display_id, season_ids, title, description)
