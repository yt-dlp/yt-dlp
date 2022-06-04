import functools
from .common import InfoExtractor
from ..utils import (
    traverse_obj,
    ExtractorError,
    GeoRestrictedError,
    OnDemandPagedList,
)
from urllib.parse import urlsplit


class NetverseBaseIE(InfoExtractor):
    _ENDPOINTS = {
        'watch': 'watchvideo',
        'video': 'watchvideo',
        'webseries': 'webseries',
    }

    def get_required_json(self, url, data=None, query={}):
        display_id, sites_type = self._match_valid_url(url).group('display_id', 'type')

        json_data = self._download_json(
            f'https://api.netverse.id/medias/api/v2/{self._ENDPOINTS[sites_type]}/{display_id}',
            display_id, data=data, query=query)

        # adapted from dailymotion.py
        error = json_data.get('error')
        if error:
            # See https://developer.dailymotion.com/api#access-error
            if error.get('code') == "DM007":
                raise GeoRestrictedError(error.get("title") or error.get("raw_message"))
            raise ExtractorError(f'{self.IE_NAME} said: {error.get("title") or error.get("raw_message")}')

        return display_id, json_data

    def _call_metadata_api_from_video_url(self, dailymotion_url, display_id, req_file_type='video', query={}):
        access_id = urlsplit(dailymotion_url).path.split('/')[-1]
        required_query = {
            'embedder': 'https://www.netverse.id',
            **query,
        }
        metadata_json = self._download_json(
            f'https://www.dailymotion.com/player/metadata/{req_file_type}/{access_id}',
            display_id, query=required_query)
        return access_id, metadata_json


class NetverseIE(NetverseBaseIE):
    _VALID_URL = r'https?://(?:\w+\.)?netverse\.id/(?P<type>watch|video)/(?P<display_id>[^/?#&]+)'
    _TESTS = [{
        # Watch video
        'url': 'https://www.netverse.id/watch/waktu-indonesia-bercanda-edisi-spesial-lebaran-2016',
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
        }}, {
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
            'episode': 'Episode 2'},
        'skip' : 'video get Geo-blocked for some country'
        }, {
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
            'episode': 'Episode 1', },
        'params': {
            'noplaylist': True,
        }
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
            'access_id': 'x887jzz',
            'episode': 'Episode 1',
            },
        'skip': 'This video get Geo-blocked for some country'
        }]

    def _real_extract(self, url):
        display_id, program_json = self.get_required_json(url=url)

        videos = traverse_obj(program_json, ('response', 'videos'))
        video_url = videos.get('dailymotion_url')
        episode_order = videos.get('episode_order')
        playlist_id = traverse_obj(videos, ('program_detail', 'slug'))

        # actually the video itself in dailymotion, but in private
        # Maybe need to refactor
        access_id, real_video_json = self._call_metadata_api_from_video_url(video_url, display_id)
        video_id = real_video_json.get('id')

        # For m3u8
        m3u8_file = traverse_obj(real_video_json, ('qualities', 'auto'))

        video_format, subtitles = [], {}
        for format in m3u8_file:
            video_url = format.get('url')
            if video_url is None:
                continue
            fmt, sub = self._extract_m3u8_formats_and_subtitles(video_url, video_id=display_id)
            video_format.extend(fmt)
            self._merge_subtitles(sub, target=subtitles)

        episode = f'Episode {episode_order}'
        self._sort_formats(video_format)

        if playlist_id:
            if self._yes_playlist(playlist_id, display_id):
                return self.url_result(
                    f'https://netverse.id/webseries/{playlist_id}',
                    NetversePlaylistIE, playlist_id)

        return {
            'id': video_id,
            'access_id': access_id,
            'formats': video_format,
            'title': videos.get('title'),
            'season': videos.get('season_name'),
            'thumbnail': traverse_obj(videos, ('program_detail', 'thumbnail_image')),
            'description': traverse_obj(videos, ('program_detail', 'description')),
            'episode_number': videos.get('episode_order'),
            'series': traverse_obj(videos, ("program_detail", "title")),
            'episode': episode,  # the test always complain about episode if it didn't exists
        }


class NetversePlaylistIE(NetverseBaseIE):
    _VALID_URL = r'https?://(?:\w+\.)?netverse\.id/(?P<type>webseries)/(?P<display_id>[^/?#&]+)'
    _TEST = {
        'url': 'https://netverse.id/webseries/tetangga-masa-gitu',
        'info_dict': {
            'id': 'tetangga-masa-gitu',
            'title': 'Tetangga Masa Gitu',
        },
        'playlist_mincount': 10,
        'playlist_maxcount': 46,
        'params': {
            'skip_download': True,
        }
    }

    def parse_playlist(self, url, playlist_page):
        display_id, playlist_json = self.get_required_json(url, query={'page': playlist_page})
        videos = traverse_obj(playlist_json, ('response', 'related', 'data'))

        for video in videos:
            vid_url = video.get('slug')

            if vid_url is not None:
                video_url = f'https://www.netverse.id/video/{vid_url}'

                yield self.url_result(video_url, NetverseIE)

    def parse_playlist_old(self, playlist_json):
        videos = traverse_obj(playlist_json, ('response', 'related', 'data'))

        for video in videos:
            vid_url = video.get('slug')

            if vid_url is not None:
                video_url = f'https://www.netverse.id/video/{vid_url}'

                yield self.url_result(video_url, NetverseIE)

    def _real_extract(self, url):
        display_id, playlist_data = self.get_required_json(url)
        webseries_info = traverse_obj(playlist_data, ('response', 'webseries_info'))
        # TODO: get video from other season
        # The season has id and the next season video is located at api_url/<season_id>?page=<page>
        # still not not sure about number in OnDemandPagedList
        entries = OnDemandPagedList(functools.partial(self.parse_playlist, url), 8)

        return self.playlist_result(
            entries, webseries_info.get('slug'), webseries_info.get('title')
        )
