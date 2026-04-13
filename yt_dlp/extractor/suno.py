from .common import InfoExtractor
from ..utils import ExtractorError, traverse_obj


class SunoBaseIE(InfoExtractor):
    def _get_clip_data(self, nextjs_data):
        """Find the clip object anywhere in the parsed Next.js flight data."""
        for _, value in nextjs_data.items():
            clip = traverse_obj(value, 'clip')
            if clip and isinstance(clip, dict) and clip.get('audio_url'):
                return clip
        return None

class SunoIE(SunoBaseIE):
    _VALID_URL = r'https?://(?:www\.)?suno\.com/song/(?P<id>[-a-f0-9]+)'
    _TESTS = [
        {
            'url': 'https://suno.com/song/be5e15a5-f406-447e-897c-631b58c8afd5',
            'info_dict': {
                'id': 'be5e15a5-f406-447e-897c-631b58c8afd5',
                'title': 'HOMERO POP',
                'description': '和楽器を前面に出した, 祝祭感あふれる和風フュージョン・ポップ, perfect production, golden era',
                'thumbnail': 'https://cdn2.suno.ai/image_large_be5e15a5-f406-447e-897c-631b58c8afd5.jpeg',
                'ext': 'mp3',
            },
        },
        {
            'url': 'https://suno.com/song/ab39a04d-b2e6-463b-9b8e-ddea725422f5',
            'info_dict': {
                'id': 'ab39a04d-b2e6-463b-9b8e-ddea725422f5',
                'title': 'Life\'s a Soundtrack · AI Funk Factory @ YT',
                'description': 'groovy funk, melodic',
                'thumbnail': 'https://cdn2.suno.ai/image_large_903f2bd7-ccc0-4029-a76a-887f07ebc2df.jpeg',
                'ext': 'mp3',
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        nextjs_data = self._search_nextjs_v13_data(webpage, video_id)
        clip = self._get_clip_data(nextjs_data)

        if not clip:
            raise ExtractorError('Could not find clip data in page', expected=True)

        return {
            'id': video_id,
            'title': clip.get('title'),
            'description': traverse_obj(clip, ('metadata', 'tags')),
            'url': clip['audio_url'],
            'thumbnail': clip.get('image_large_url') or clip.get('image_url'),
            'ext': 'mp3',
        }
