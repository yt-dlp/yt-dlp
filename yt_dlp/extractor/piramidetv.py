from .common import InfoExtractor, SearchInfoExtractor
from ..utils import (
    traverse_obj,
    unified_timestamp,
    url_or_none,
)


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
            'title': 'ACEPTO TENER UN BEBE CON MI NOVIA\u2026? | Parte 1',
            'description': '',
            'channel': 'ARTA GAME',
            'channel_id': 'arta_game',
        },
        'playlist_count': 4,
    }]

    def _real_extract(self, url):
        def extract_video(video_id, fatal=False):
            video_data = self._download_json(f'https://hermes.piramide.tv/video/data/{video_id}',
                                             video_id, fatal=fatal)
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                f'https://cdn.piramide.tv/video/{video_id}/manifest.m3u8', video_id, fatal=fatal)
            video_info = {**traverse_obj(video_data, {
                'id': ('video', 'id', {str}),
                'title': ('video', 'title', {str}),
                'description': ('video', 'description', {str}),
                'thumbnail': ('video', 'media', 'thumbnail', {url_or_none}),
                'channel': ('video', 'channel', 'name', {str}),
                'channel_id': ('video', 'channel', 'id', {str}),
                'timestamp': ('video', 'date', {unified_timestamp}),
            }),
                'formats': formats,
                'subtitles': subtitles,
                'webpage_url': f'https://piramide.tv/video/{video_id}',
                'webpage_url_basename': video_id,
            }
            next_video_id = traverse_obj(video_data, ('video', 'next_video', 'id', {str}))
            return video_info, next_video_id

        video_id = self._match_id(url)
        entries = []
        while video_id is not None:
            video, next_video = extract_video(video_id, (not entries))
            if video.get('formats'):
                entries.append(video)
            video_id = next_video if next_video != video_id else None

        if len(entries) == 1:
            return entries[0]
        elif len(entries) > 1:
            return self.playlist_result(entries, **traverse_obj(entries[0], {
                'id': ('id'),
                'title': ('title'),
                'description': ('description'),
                'channel': ('channel'),
                'channel_id': ('channel_id'),
            }))
        else:
            return {'id': video_id}


class PiramideTVChannelURLIE(InfoExtractor):
    _VALID_URL = r'https?://piramide\.tv/channel/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://piramide.tv/channel/thekalo',
        'playlist_count': 10,
        'info_dict': {
            'id': 'thekalo',
            'title': 'thekalo',
        },
    }]

    def _real_extract(self, url):
        if query := self._match_id(url):
            return self.url_result(url=f'piramidetvall:{query}', url_transparent=True)


class PiramideTVChannelIE(SearchInfoExtractor):
    IE_NAME = 'PiramideTV:channel'
    _SEARCH_KEY = 'piramidetv'
    _TESTS = [{
        'url': 'piramidetv5:bobicraft',
        'playlist_count': 5,
        'info_dict': {
            'id': 'bobicraft',
            'title': 'bobicraft',
        },
    }]

    def _search_results(self, query):
        videos = self._download_json(f'https://hermes.piramide.tv/channel/list/{query}/date/100000', query)
        for video in videos.get('videos'):
            if video_id := video.get('id'):
                yield self.url_result(f'https://piramide.tv/video/{video_id}')
