from .common import InfoExtractor
from ..utils import (
    traverse_obj,
    ExtractorError,
)


class NetverseBaseIE(InfoExtractor):
    def get_required_json(self, url, data=None):
        match = self._match_valid_url(url).groupdict()
        display_id, sites_type = match['display_id'], match['type']

        if sites_type == 'watch' or sites_type == 'video':
            media_api_url = f'https://api.netverse.id/medias/api/v2/watchvideo/{display_id}'
        elif sites_type == 'webseries':
            media_api_url = f'https://api.netverse.id/medias/api/v2/webseries/{display_id}'

        json_data = self._download_json(media_api_url, display_id, data=data)

        if json_data.get('error'):
            raise ExtractorError(json_data.get('message'))

        return json_data

    def get_access_id(self, dailymotion_url):
        return dailymotion_url.split('/')[-1]

    def _call_metadata_api_from_video_url(self, dailymotion_url):
        access_id = self.get_access_id(dailymotion_url)
        metadata_json = self._call_metadata_api(access_id)
        return access_id, metadata_json

    def _call_metadata_api(self, access_id, req_file_type='video', query=None):
        video_metadata_api_url = f'https://www.dailymotion.com/player/metadata/{req_file_type}/{access_id}'

        if query is None:
            required_query = {
                'embedder': 'https://www.netverse.id'
            }
        else:
            required_query = query

        return self._download_json(video_metadata_api_url, access_id, query=required_query)


class NetverseIE(NetverseBaseIE):
    _VALID_URL = r'https?://(?:\w+\.)?netverse\.id/(?P<type>watch|video)/(?P<display_id>[^/?#&]+)'
    # Netverse Watch
    _TESTS = [{
        'url': 'https://www.netverse.id/watch/waktu-indonesia-bercanda-edisi-spesial-lebaran-2016',
        # 'only_matching' : True,
        'info_dict': {
            'access_id': 'k4yhqUwINAGtmHx3NkL',
            'id': 'x82urb7',
            'title': 'Waktu Indonesia Bercanda - Edisi Spesial Lebaran 2016',
            'ext': 'mp4',
            'season': 'Season 2016',
            'description': 'md5:fc27747c0aa85067b6967c816f01617c',
            'thumbnail': 'https://vplayed-uat.s3-ap-southeast-1.amazonaws.com/images/webseries/thumbnails/2021/11/619cfce45c827.jpeg',
            'episode_number': 22,
            'series': 'Waktu Indonesia Bercanda',
            'episode': 'Episode 22',
        }}, { # noqa
        # series
        'url': 'https://www.netverse.id/watch/jadoo-seorang-model',
        'info_dict': {
            'id': 'x88izwc',
            'access_id': 'x88izwc',
            'title': 'Jadoo Seorang Model',
            'ext': 'mp4',
            'season': 'Season 2',
            'description': 'md5:c616e8e59d3edf2d3d506e3736120d99',
            'thumbnail': 'https://storage.googleapis.com/netprime-live/images/webseries/thumbnails/2021/11/619cf63f105d3.jpeg',
            'episode_number': 2,
            'series': 'Hello Jadoo',
            'episode': 'Episode 2', }
        }, {  # noqa
        # non www host
        'url': 'https://netverse.id/watch/tetangga-baru',
        'info_dict': {
            'id': 'x8278vk',
            'ext': 'mp4',
            'access_id': 'k4CNGz7V0HJ7vfwZbXy',
            'title': 'Tetangga Baru',
            'season': 'Season 1',
            'description': 'md5:ed6dd355bed84d139b1154c3d8d65957',
            'thumbnail': 'https://vplayed-uat.s3-ap-southeast-1.amazonaws.com/images/webseries/thumbnails/2021/11/619cfd9d32c5f.jpeg',
            'episode_number': 1,
            'series': 'Tetangga Masa Gitu',
            'episode': 'Episode 1',
        }}, { # noqa
        # /video url
        'url': 'https://www.netverse.id/video/pg067482-hellojadoo-season1',
        'title': 'Namaku Choi Jadoo',
        'info_dict': {
            'id': 'x887jzz',
            'ext': 'mp4',
            } # noqa
        }]  # noqa

    def _real_extract(self, url):
        program_json = self.get_required_json(url=url)

        videos = traverse_obj(program_json, ('response', 'videos'))

        video_url = videos.get('dailymotion_url')
        episode_order = videos.get('episode_order')

        program_detail = videos.get('program_detail')

        # actually the video itself in daily motion, but in private
        # Maybe need to refactor
        access_id, real_video_json = self._call_metadata_api_from_video_url(video_url)

        video_id = real_video_json.get('id')

        # For m3u8
        m3u8_file = traverse_obj(real_video_json, ('qualities', 'auto'))

        for format in m3u8_file:
            video_url = format.get('url')
            if video_url is None:
                continue
            self.video_format = self._extract_m3u8_formats(video_url, video_id=video_id)
       
        episode = f'Episode {episode_order}'

        self._sort_formats(self.video_format)
        return {
            'id': video_id,
            'access_id': access_id,
            'formats': self.video_format,
            'title': videos.get('title'),
            'season': videos.get('season_name'),
            'thumbnail': program_detail.get('thumbnail_image'),
            'description': program_detail.get('description'),
            'episode_number': videos.get('episode_order'),
            'series': program_detail.get('title'),
            'episode': episode,

        }


class NetversePlaylistIE(NetverseBaseIE):
    _VALID_URL = r'https?://(?:\w+\.)?netverse\.id/(?P<type>webseries)/(?P<display_id>[^/?#&]+)'
    _TEST = {
        'url': 'https://netverse.id/webseries/tetangga-masa-gitu',
        'title': 'Tetangga Masa Gitu',
        'info_dict': {
            '_type': 'playlist',  # expected playlist, got None
            'id': '16',
            'ext': 'mp4',
        }
    }

    def _real_extract(self, url):
        playlist_data = self.get_required_json(url)

        webseries_info = traverse_obj(playlist_data, ('response', 'webseries_info'))

        videos = traverse_obj(playlist_data, ('response', 'related', 'data'))

        entries = []
        for video in videos:
            video_url = f'https://www.netverse.id/video/{video.get("slug")}'

            entry = self.url_result(video_url, NetverseIE)
            entries.append(entry)

        return {
            '_type': 'playlist',
            'title': webseries_info.get('title'),
            'id': webseries_info.get('video_webseries_detail_id'),
            'entries': entries,
        }
