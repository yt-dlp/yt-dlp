from .common import InfoExtractor
from ..utils import parse_iso8601, smuggle_url, unsmuggle_url, url_or_none
from ..utils.traversal import traverse_obj


class PiramideTVIE(InfoExtractor):
    _VALID_URL = r'https?://piramide\.tv/video/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://piramide.tv/video/wWtBAORdJUTh',
        'info_dict': {
            'id': 'wWtBAORdJUTh',
            'ext': 'mp4',
            'title': 'md5:79f9c8183ea6a35c836923142cf0abcc',
            'description': '',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/W86PgQDn/thumbnails/B9gpIxkH.jpg',
            'channel': 'León Picarón',
            'channel_id': 'leonpicaron',
            'timestamp': 1696460362,
            'upload_date': '20231004',
        },
    }, {
        'url': 'https://piramide.tv/video/wcYn6li79NgN',
        'info_dict': {
            'id': 'wcYn6li79NgN',
            'ext': 'mp4',
            'title': 'ACEPTO TENER UN BEBE CON MI NOVIA\u2026? | Parte 1',
            'description': '',
            'channel': 'ARTA GAME',
            'channel_id': 'arta_game',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/cnEdGp5X/thumbnails/rHAaWfP7.jpg',
            'timestamp': 1703434976,
            'upload_date': '20231224',
        },
    }]

    def _extract_video(self, video_id):
        video_data = self._download_json(
            f'https://hermes.piramide.tv/video/data/{video_id}', video_id, fatal=False)
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            f'https://cdn.piramide.tv/video/{video_id}/manifest.m3u8', video_id, fatal=False)
        next_video = traverse_obj(video_data, ('video', 'next_video', 'id', {str}))
        return next_video, {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(video_data, ('video', {
                'id': ('id', {str}),
                'title': ('title', {str}),
                'description': ('description', {str}),
                'thumbnail': ('media', 'thumbnail', {url_or_none}),
                'channel': ('channel', 'name', {str}),
                'channel_id': ('channel', 'id', {str}),
                'timestamp': ('date', {parse_iso8601}),
            })),
        }

    def _entries(self, video_id):
        visited = set()
        while True:
            visited.add(video_id)
            next_video, info = self._extract_video(video_id)
            yield info
            if not next_video or next_video in visited:
                break
            video_id = next_video

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        video_id = self._match_id(url)
        if self._yes_playlist(video_id, video_id, smuggled_data):
            return self.playlist_result(self._entries(video_id), video_id)
        return self._extract_video(video_id)[1]


class PiramideTVChannelIE(InfoExtractor):
    _VALID_URL = r'https?://piramide\.tv/channel/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://piramide.tv/channel/thekalo',
        'playlist_mincount': 10,
        'info_dict': {
            'id': 'thekalo',
        },
    }]

    def _entries(self, channel_name):
        videos = self._download_json(
            f'https://hermes.piramide.tv/channel/list/{channel_name}/date/100000', channel_name)
        for video in traverse_obj(videos, ('videos', lambda _, v: v['id'])):
            yield self.url_result(smuggle_url(
                f'https://piramide.tv/video/{video["id"]}', {'force_noplaylist': True}),
                **traverse_obj(video, {
                    'id': ('id', {str}),
                    'title': ('title', {str}),
                    'description': ('description', {str}),
                }))

    def _real_extract(self, url):
        channel_name = self._match_id(url)
        return self.playlist_result(self._entries(channel_name), channel_name)
