from yt_dlp.utils._utils import qualities

from .common import InfoExtractor


class PlVideoVideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?plvideo\.ru/watch\?v=(?P<id>\w+)&?(.+)?'  # type: ignore
    _TESTS = [
        {
            'url': 'https://plvideo.ru/watch?v=lYmu2gcUKOa9',
            'md5': 'eb3e7830abb375a782d943f593d2646b',
            'info_dict': {
                'id': 'lYmu2gcUKOa9',
                'ext': 'mp4',
                'title': 'Запретная страсть. Премьера 2024. 18+Мелодрама. Триллер. 18+',
                'uploader_id': 'y__S081jJiUt',
                'uploader': 'Tvoja Mediateka',
                'duration': 6238333,
                'like_count': int,
                'description': str,
                'comment_count': int,
                'thumbnail': r're:^https?://.*\.jpg',
                'type': 'video',
                'view_count': int,
                'dislike_count': int,
            },
        },
    ]

    def _quality_to_dimensions(self, quality):
        mapped = {
            '240p': (426, 240),
            '360p': (640, 360),
            '468p': (720, 468),
            '480p': (720, 480),
            '720p': (1280, 720),
            '1080p': (1920, 1080),
        }
        return mapped.get(quality)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        api_url = f'https://api.g1.plvideo.ru/v1/videos/{video_id}?Aud=18'

        result = self._download_json(api_url, video_id, 'Downloading video JSON')
        assert result.get('code') == 200, 'Failed to download video JSON'

        item = result.get('item')
        assert item is not None, 'Bad API response'

        thumbnail = item.get('cover').get('paths').get('original').get('src')

        formats = []
        preference = qualities(['240p', '360p', '468p', '480p', '720p', '1080p'])

        for key, value in item.get('profiles').items():
            hlsurl = value.get('hls')
            dimensions = self._quality_to_dimensions(key)
            fmt = {
                'url': hlsurl,
                'ext': 'mp4',
                'quality': preference(key),
                'width': dimensions[0],
                'height': dimensions[1],
                'format_id': key,
                'protocol': 'm3u8_native',
                'aspect_ratio': float(value.get('aspectRatio')),
            }

            formats.append(fmt)

        result = {
            'id': video_id,
            'title': item.get('title'),
            'formats': formats,
            'thumbnails': [{'url': thumbnail}],
            'uploader': item.get('channel').get('name'),
            'duration': item.get('uploadFile').get('videoDuration'),
            'uploader_id': item.get('channel').get('id'),
            'view_count': item.get('stats').get('viewTotalCount'),
            'like_count': item.get('stats').get('likeCount'),
            'comment_count': item.get('stats').get('commentCount'),
            'dislike_count': item.get('stats').get('dislikeCount'),
            'type': item.get('type'),
        }

        description = item.get('description')
        if description:
            result['description'] = description

        return result
