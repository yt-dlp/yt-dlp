from .common import InfoExtractor
from .dailymotion import DailymotionIE
from ..utils import smuggle_url, traverse_obj


class NetverseBaseIE(InfoExtractor):
    _ENDPOINTS = {
        'watch': 'watchvideo',
        'video': 'watchvideo',
        'webseries': 'webseries',
        'season': 'webseason_videos',
    }

    def _call_api(self, slug, endpoint, query={}, season_id='', display_id=None):
        return self._download_json(
            f'https://api.netverse.id/medias/api/v2/{self._ENDPOINTS[endpoint]}/{slug}/{season_id}',
            display_id or slug, query=query)


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
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'thumbnail': r're:https?://s\d+\.dmcdn\.net/v/T7aV31Y0eGRWBbwkK/x1080',
            'episode_number': 22,
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
            'description': 'md5:8a74f70812cca267e19ee0635f0af835',
            'thumbnail': r're:https?://s\d+\.dmcdn\.net/v/Thwuy1YURicFmGu0v/x1080',
            'episode_number': 2,
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
            'description': 'md5:23fcf70e97d461d3029d25d59b2ccfb9',
            'thumbnail': r're:https?://s\d+\.dmcdn\.net/v/T3Ogm1YEnnyjVKAFF/x1080',
            'episode_number': 1,
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
            'thumbnail': r're:https?://s\d+\.dmcdn\.net/v/TfuZ_1Y6PboJ5An_s/x1080',
            'season': 'Season 1',
            'episode_number': 1,
            'description': 'md5:d4f627b3e7a3f9acdc55f6cdd5ea41d5',
            'title': 'Namaku Choi Jadoo',
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
        display_id, sites_type = self._match_valid_url(url).group('display_id', 'type')
        program_json = self._call_api(display_id, sites_type)
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
        'playlist_count': 203,
    }]

    def parse_playlist(self, json_data, playlist_id):
        slug_sample = traverse_obj(json_data, ('related', 'data', ..., 'slug'))[0]
        for season in traverse_obj(json_data, ('seasons', ..., 'id')):
            playlist_json = self._call_api(
                slug_sample, 'season', display_id=playlist_id, season_id=season)

            for current_page in range(playlist_json['response']['season_list']['last_page']):
                playlist_json = self._call_api(slug_sample, 'season', query={'page': current_page + 1},
                                               season_id=season, display_id=playlist_id)
                for slug in traverse_obj(playlist_json, ('response', ..., 'data', ..., 'slug')):
                    yield self.url_result(f'https://www.netverse.id/video/{slug}', NetverseIE)

    def _real_extract(self, url):
        playlist_id, sites_type = self._match_valid_url(url).group('display_id', 'type')
        playlist_data = self._call_api(playlist_id, sites_type)

        return self.playlist_result(
            self.parse_playlist(playlist_data['response'], playlist_id),
            traverse_obj(playlist_data, ('response', 'webseries_info', 'slug')),
            traverse_obj(playlist_data, ('response', 'webseries_info', 'title')))
