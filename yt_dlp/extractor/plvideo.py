from .common import InfoExtractor


class PlVideoVideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?plvideo\.ru/watch\?v=(?P<id>\w+)&?(.+)?'  # type: ignore
    _TESTS = [
        {
            'url': 'https://plvideo.ru/watch?v=lYmu2gcUKOa9',
            'info_dict': {
                'id': 'lYmu2gcUKOa9',
                'ext': 'mp4',
                'title': 'test',
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        api_url = f'https://api.g1.plvideo.ru/v1/videos/{video_id}?Aud=18'

        result = self._download_json(api_url, video_id, 'Downloading video JSON')
        assert result.get('code') == 200, 'Failed to download video JSON'

        item = result.get('item')
        assert item is not None, 'Bad API response'

        thumbnail = item.get('cover').get('paths').get('original').get('src')

        formats = []

        for key, value in item.get('profiles').items():
            hlsurl = value.get('hls')
            fmt = {
                'url': hlsurl,
                'ext': 'mp4',
                'quality': 0 if len(formats) == 0 else 0 - len(formats),
                'format_id': key,
                'protocol': 'm3u8_native',
            }

            formats.append(fmt)

        return {
            'id': video_id,
            'title': item.get('title'),
            'formats': formats,
            'thumbnails': [{'url': thumbnail}],
        }
