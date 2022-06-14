import functools

from .common import InfoExtractor
from .dailymotion import DailymotionIE
from ..utils import (
    InAdvancePagedList,
    smuggle_url,
    traverse_obj,
)


class NetverseBaseIE(InfoExtractor):
    _ENDPOINTS = {
        'watch': 'watchvideo',
        'video': 'watchvideo',
        'webseries': 'webseries',
        'season': 'webseason_videos',
    }

    def _call_api(self, input_data, query={}, season='',
                  custom_id=None, force_endpoint_type='auto', input_type='url'):

        slug = None
        if input_type == 'url':
            display_id, sites_type = self._match_valid_url(input_data).group('display_id', 'type')
        elif input_type == 'slug':
            slug = input_data
        display_id = display_id if slug is None else slug
        endpoint = self._ENDPOINTS[sites_type] if force_endpoint_type == 'auto' else self._ENDPOINTS[force_endpoint_type]

        json_data = self._download_json(
            f'https://api.netverse.id/medias/api/v2/{endpoint}/{display_id}/{season}',
            custom_id or display_id, query=query)
        return display_id, json_data


class NetverseIE(NetverseBaseIE):
    _VALID_URL = r'https?://(?:\w+\.)?netverse\.id/(?P<type>watch|video)/(?P<display_id>[^/?#&]+)'
    _TESTS = [{
        # Watch video
        'url': 'https://www.netverse.id/watch/waktu-indonesia-bercanda-edisi-spesial-lebaran-2016',
        'info_dict': {
            'id': 'k4yhqUwINAGtmHx3NkL',
            'title': 'Waktu Indonesia Bercanda - Edisi Spesial Lebaran 2016',
            'ext': 'mp4',
            'season': 'Season 2016',
            'description': 'md5:fc27747c0aa85067b6967c816f01617c',
            'thumbnail': 'https://vplayed-uat.s3-ap-southeast-1.amazonaws.com/images/webseries/thumbnails/2021/11/619cfce45c827.jpeg',
            'episode_number': 22,
            'series': 'Waktu Indonesia Bercanda',
            'episode': 'Episode 22',
            'uploader_id': 'x2ir3vq',
            'age_limit': 0,
            'tags': [],
            'view_count': int,
            'display_id': 'waktu-indonesia-bercanda-edisi-spesial-lebaran-2016',
            'duration': 2990,
            'upload_date': '20210722',
            'timestamp': 1626919804,
            'like_count': int,
            'uploader': 'Net Prime',
        }
    }, {
        # series
        'url': 'https://www.netverse.id/watch/jadoo-seorang-model',
        'info_dict': {
            'id': 'x88izwc',
            'title': 'Jadoo Seorang Model',
            'ext': 'mp4',
            'season': 'Season 2',
            'description': 'md5:c616e8e59d3edf2d3d506e3736120d99',
            'thumbnail': 'https://storage.googleapis.com/netprime-live/images/webseries/thumbnails/2021/11/619cf63f105d3.jpeg',
            'episode_number': 2,
            'series': 'Hello Jadoo',
            'episode': 'Episode 2',
            'view_count': int,
            'like_count': int,
            'display_id': 'jadoo-seorang-model',
            'uploader_id': 'x2ir3vq',
            'duration': 635,
            'timestamp': 1646372927,
            'tags': ['PG069497-hellojadooseason2eps2'],
            'upload_date': '20220304',
            'uploader': 'Net Prime',
            'age_limit': 0,
        },
        'skip': 'video get Geo-blocked for some country'
    }, {
        # non www host
        'url': 'https://netverse.id/watch/tetangga-baru',
        'info_dict': {
            'id': 'k4CNGz7V0HJ7vfwZbXy',
            'ext': 'mp4',
            'title': 'Tetangga Baru',
            'season': 'Season 1',
            'description': 'md5:ed6dd355bed84d139b1154c3d8d65957',
            'thumbnail': 'https://vplayed-uat.s3-ap-southeast-1.amazonaws.com/images/webseries/thumbnails/2021/11/619cfd9d32c5f.jpeg',
            'episode_number': 1,
            'series': 'Tetangga Masa Gitu',
            'episode': 'Episode 1',
            'timestamp': 1624538169,
            'view_count': int,
            'upload_date': '20210624',
            'age_limit': 0,
            'uploader_id': 'x2ir3vq',
            'like_count': int,
            'uploader': 'Net Prime',
            'tags': ['PG008534', 'tetangga', 'Baru'],
            'display_id': 'tetangga-baru',
            'duration': 1406,
        },
    }, {
        # /video url
        'url': 'https://www.netverse.id/video/pg067482-hellojadoo-season1',
        'title': 'Namaku Choi Jadoo',
        'info_dict': {
            'id': 'x887jzz',
            'ext': 'mp4',
            'thumbnail': 'https://storage.googleapis.com/netprime-live/images/webseries/thumbnails/2021/11/619cf63f105d3.jpeg',
            'season': 'Season 1',
            'episode_number': 1,
            'description': 'md5:c616e8e59d3edf2d3d506e3736120d99',
            'title': 'Namaku Choi Jadoo',
            'series': 'Hello Jadoo',
            'episode': 'Episode 1',
            'age_limit': 0,
            'like_count': int,
            'view_count': int,
            'tags': ['PG067482', 'PG067482-HelloJadoo-season1'],
            'duration': 780,
            'display_id': 'pg067482-hellojadoo-season1',
            'uploader_id': 'x2ir3vq',
            'uploader': 'Net Prime',
            'timestamp': 1645764984,
            'upload_date': '20220225',
        },
        'skip': 'This video get Geo-blocked for some country'
    }]

    def _real_extract(self, url):
        display_id, program_json = self._call_api(url)
        videos = program_json['response']['videos']

        return {
            '_type': 'url_transparent',
            'ie_key': DailymotionIE.ie_key(),
            'url': smuggle_url(videos['dailymotion_url'], {'query': {'embedder': 'https://www.netverse.id'}}),
            'display_id': display_id,
            'title': videos.get('title'),
            'season': videos.get('season_name'),
            'thumbnail': traverse_obj(videos, ('program_detail', 'thumbnail_image')),
            'description': traverse_obj(videos, ('program_detail', 'description')),
            'episode_number': videos.get('episode_order'),
            'series': traverse_obj(videos, ('program_detail', 'title')),
        }


class NetversePlaylistIE(NetverseBaseIE):
    _VALID_URL = r'https?://(?:\w+\.)?netverse\.id/(?P<type>webseries)/(?P<display_id>[^/?#&]+)'
    _TESTS = [{
        # multiple season
        'url': 'https://netverse.id/webseries/tetangga-masa-gitu',
        'info_dict': {
            'id': 'tetangga-masa-gitu',
            'title': 'Tetangga Masa Gitu',
        },
        'playlist_count': 519,
    }, {
        # single season
        'url': 'https://netverse.id/webseries/kelas-internasional',
        'info_dict': {
            'id': 'kelas-internasional',
            'title': 'Kelas Internasional',
        },
        'playlist_count': 158,
    }]

    def parse_single_season_playlist(self, input_data, page_num, custom_id=None, season_id='',
                                     force_endpoint_type='auto', input_type='url'):

        _, playlist_json = self._call_api(
            input_data, query={'page': page_num + 1}, season=season_id, custom_id=custom_id,
            force_endpoint_type=force_endpoint_type, input_type=input_type)
        for slug in traverse_obj(playlist_json, ('response', ..., 'data', ..., 'slug')):
            yield self.url_result(f'https://www.netverse.id/video/{slug}', NetverseIE)

    def parse_playlist(self, url, json_data, playlist_id):
        slug_sample = traverse_obj(json_data, ('related', 'data', ..., 'slug'))[0]
        season_id_list = [season.get('id') for season in json_data.get('seasons')]

        for season in season_id_list:
            # initial data
            _, playlist_json = self._call_api(
                input_data=slug_sample, custom_id=playlist_id, season=season, force_endpoint_type='season', input_type='slug')

            number_video_per_page = traverse_obj(playlist_json, ('response', 'season_list', 'to')) - traverse_obj(playlist_json, ('response', 'season_list', 'from')) + 1
            number_of_pages = traverse_obj(playlist_json, ('response', 'season_list', 'last_page'))

            yield from InAdvancePagedList(
                functools.partial(
                    self.parse_single_season_playlist, slug_sample, custom_id=playlist_id,
                    season_id=season, force_endpoint_type='season', input_type='slug'),
                number_of_pages, number_video_per_page)

    def _real_extract(self, url):
        _, playlist_data = self._call_api(url)
        return self.playlist_result(
            self.parse_playlist(url, playlist_data['response'], _),
            traverse_obj(playlist_data, ('response', 'webseries_info', 'slug')),
            traverse_obj(playlist_data, ('response', 'webseries_info', 'title')))
