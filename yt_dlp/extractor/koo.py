from .common import InfoExtractor
from ..utils import (
    clean_html,
    try_get,
)


class KooIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://(?:www\.)?kooapp\.com/koo/[^/]+/(?P<id>[^/&#$?]+)'
    _TESTS = [{  # Test for video in the comments
        'url': 'https://www.kooapp.com/koo/ytdlpTestAccount/946c4189-bc2d-4524-b95b-43f641e2adde',
        'info_dict': {
            'id': '946c4189-bc2d-4524-b95b-43f641e2adde',
            'ext': 'mp4',
            'title': 'test for video in comment',
            'description': 'md5:daa77dc214add4da8b6ea7d2226776e7',
            'timestamp': 1632215195,
            'uploader_id': 'ytdlpTestAccount',
            'uploader': 'yt-dlpTestAccount',
            'duration': 7000,
            'upload_date': '20210921'
        },
        'params': {'skip_download': True}
    }, {  # Test for koo with long title
        'url': 'https://www.kooapp.com/koo/laxman_kumarDBFEC/33decbf7-5e1e-4bb8-bfd7-04744a064361',
        'info_dict': {
            'id': '33decbf7-5e1e-4bb8-bfd7-04744a064361',
            'ext': 'mp4',
            'title': 'md5:47a71c2337295330c5a19a8af1bbf450',
            'description': 'md5:06a6a84e9321499486dab541693d8425',
            'timestamp': 1632106884,
            'uploader_id': 'laxman_kumarDBFEC',
            'uploader': 'Laxman Kumar 🇮🇳',
            'duration': 46000,
            'upload_date': '20210920'
        },
        'params': {'skip_download': True}
    }, {  # Test for audio
        'url': 'https://www.kooapp.com/koo/ytdlpTestAccount/a2a9c88e-ce4b-4d2d-952f-d06361c5b602',
        'info_dict': {
            'id': 'a2a9c88e-ce4b-4d2d-952f-d06361c5b602',
            'ext': 'mp4',
            'title': 'Test for audio',
            'description': 'md5:ecb9a2b6a5d34b736cecb53788cb11e8',
            'timestamp': 1632211634,
            'uploader_id': 'ytdlpTestAccount',
            'uploader': 'yt-dlpTestAccount',
            'duration': 214000,
            'upload_date': '20210921'
        },
        'params': {'skip_download': True}
    }, {  # Test for video
        'url': 'https://www.kooapp.com/koo/ytdlpTestAccount/a3e56c53-c1ed-4ac9-ac02-ed1630e6b1d1',
        'info_dict': {
            'id': 'a3e56c53-c1ed-4ac9-ac02-ed1630e6b1d1',
            'ext': 'mp4',
            'title': 'Test for video',
            'description': 'md5:7afc4eb839074ddeb2beea5dd6fe9500',
            'timestamp': 1632211468,
            'uploader_id': 'ytdlpTestAccount',
            'uploader': 'yt-dlpTestAccount',
            'duration': 14000,
            'upload_date': '20210921'
        },
        'params': {'skip_download': True}
    }, {  # Test for link
        'url': 'https://www.kooapp.com/koo/ytdlpTestAccount/01bf5b94-81a5-4d8e-a387-5f732022e15a',
        'skip': 'No video/audio found at the provided url.',
        'info_dict': {
            'id': '01bf5b94-81a5-4d8e-a387-5f732022e15a',
            'title': 'Test for link',
            'ext': 'none',
        },
    }, {  # Test for images
        'url': 'https://www.kooapp.com/koo/ytdlpTestAccount/dc05d9cd-a61d-45fd-bb07-e8019d8ca8cb',
        'skip': 'No video/audio found at the provided url.',
        'info_dict': {
            'id': 'dc05d9cd-a61d-45fd-bb07-e8019d8ca8cb',
            'title': 'Test for images',
            'ext': 'none',
        },
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        data_json = self._download_json(f'https://www.kooapp.com/apiV1/ku/{id}?limit=20&offset=0&showSimilarKoos=true', id)['parentContent']
        item_json = next(content['items'][0] for content in data_json
                         if try_get(content, lambda x: x['items'][0]['id']) == id)
        media_json = item_json['mediaMap']
        formats = []

        mp4_url = media_json.get('videoMp4')
        video_m3u8_url = media_json.get('videoHls')
        if mp4_url:
            formats.append({
                'url': mp4_url,
                'ext': 'mp4',
            })
        if video_m3u8_url:
            formats.extend(self._extract_m3u8_formats(video_m3u8_url, id, fatal=False, ext='mp4'))
        if not formats:
            self.raise_no_formats('No video/audio found at the provided url.', expected=True)

        return {
            'id': id,
            'title': clean_html(item_json.get('title')),
            'description': f'{clean_html(item_json.get("title"))}\n\n{clean_html(item_json.get("enTransliteration"))}',
            'timestamp': item_json.get('createdAt'),
            'uploader_id': item_json.get('handle'),
            'uploader': item_json.get('name'),
            'duration': media_json.get('duration'),
            'formats': formats,
        }
