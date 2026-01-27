import json

from .common import InfoExtractor
from ..utils import (
    traverse_obj,
    url_or_none,
)


class MatreshkaIE(InfoExtractor):
    _VALID_URL = r'https?://matreshka\.tv/video/(?P<id>[\w]+)(?:\?playlistID=(?P<playlist_id>[\w]+))?'
    _TESTS = [{
        'url': 'https://matreshka.tv/video/HwKAY4Id5QA',
        'md5': '1e528392822120c5740a5cfab5483dbc',
        'info_dict': {
            'id': 'HwKAY4Id5QA',
            'title': '2025.11.04  Диалог об алкоголе с Джеком Лондоном (МЕТРО) - Стас васильев',
            'thumbnail': 'https://c2-images.cmtv.ru/video/wgKgXz6-xvY/HwKAY4Id5QA/frame/5/1280x720.png',
            'description': '',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://matreshka.tv/video/KgBAzC_u0gA?playlistID=YwKA4Zq50gA',
        'info_dict': {
            'id': 'YwKA4Zq50gA',
            'title': 'Андор - Пучков и Жуков',
        },
        'playlist_count': 9,
    }]

    def _playlist_entries(self, playlist_info):
        video_ids: list[str] = traverse_obj(
            playlist_info,
            ('data', 0, 'videos', ..., 'id'),
            expected_type=str,
        )

        for video_id in video_ids:
            yield self.url_result(
                f'https://matreshka.tv/video/{video_id}',
                ie=MatreshkaIE,
                video_id=video_id,
            )

    def get_playlist_info(self, playlist_id):
        post_request_data = json.dumps({
            'field_mask': ['id',
                           'name',
                           'description',
                           'videos.id',
                           'videos'],
            'filter': [{
                'is': '=',
                'field': 'id',
                'value': playlist_id,
            }],
        }).encode('utf-8')

        playlist_info = self._download_json('https://matreshka.tv/api/v2/playlist', playlist_id,
                                            note='Downloading playlist info', data=post_request_data,
                                            headers={'accept': 'application/json, text/plain, */*',
                                                     'content-type': 'application/json'})
        if playlist_info:
            playlist_name = traverse_obj(playlist_info, ('data', 0, 'name', {str}), expected_type=str)
            playlist_desc = traverse_obj(playlist_info, ('data', 0, 'description', {str}), expected_type=str)
            return self.playlist_result(self._playlist_entries(playlist_info), playlist_id,
                                        playlist_title=playlist_name,
                                        playlist_description=playlist_desc)

    def get_video_info(self, video_id):
        video_info = self._download_json(f'https://matreshka.tv/api/video-service/v1/video/{video_id}',
                                         video_id, note='Downloading video info')
        if video_info:
            video_dict = traverse_obj(video_info, ('data', {
                'id': ('id', {str}),
                'title': ('name', {str}),
                'description': ('description', {str}),
                'thumbnails': (
                    'cover', 'png',
                    {dict},
                    {lambda d: [
                        {
                            'url': url,
                            'width': int(size.split('x')[0]),
                            'height': int(size.split('x')[1]),
                        }
                        for size, url in d.items()
                    ]},
                ),
            }))
            formats, subtitles = traverse_obj(video_info,
                                              ('data', 'video_url', 'h264',
                                               'src', 'hls', {url_or_none},
                                                  {lambda video_url: self._extract_m3u8_formats_and_subtitles(video_url, video_id, m3u8_id='hls')},
                                               ))
            video_dict['formats'] = formats
            video_dict['subtitles'] = subtitles
            return video_dict

    def _real_extract(self, url):
        video_id = self._match_id(url)
        playlist_id = self._match_valid_url(url).group('playlist_id')
        if playlist_id:
            return self.get_playlist_info(playlist_id)
        else:
            return self.get_video_info(video_id)
