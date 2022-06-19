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
    }

    def _call_api(self, url, query={}):
        display_id, sites_type = self._match_valid_url(url).group('display_id', 'type')

        json_data = self._download_json(
            f'https://api.netverse.id/medias/api/v2/{self._ENDPOINTS[sites_type]}/{display_id}',
            display_id, query=query)

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
    _TEST = {
        'url': 'https://netverse.id/webseries/tetangga-masa-gitu',
        'info_dict': {
            'id': 'tetangga-masa-gitu',
            'title': 'Tetangga Masa Gitu',
        },
        'playlist_count': 46,
    }

    def parse_playlist(self, url, page_num):
        _, playlist_json = self._call_api(url, query={'page': page_num + 1})
        for slug in traverse_obj(playlist_json, ('response', 'related', 'data', ..., 'slug')):
            yield self.url_result(f'https://www.netverse.id/video/{slug}', NetverseIE)

    def _real_extract(self, url):
        _, playlist_data = self._call_api(url)
        webseries_related_info = playlist_data['response']['related']
        # TODO: get video from other season
        # The season has id and the next season video is located at api_url/<season_id>?page=<page>
        return self.playlist_result(
            InAdvancePagedList(functools.partial(self.parse_playlist, url),
                               webseries_related_info['last_page'],
                               webseries_related_info['to'] - webseries_related_info['from'] + 1),
            traverse_obj(playlist_data, ('response', 'webseries_info', 'slug')),
            traverse_obj(playlist_data, ('response', 'webseries_info', 'title')))
