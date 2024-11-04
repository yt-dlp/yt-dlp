from .common import InfoExtractor


class SunoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?suno\.com/song/(?P<id>[-a-f0-9]+)'
    _TESTS = [
        {
            'url': 'https://suno.com/song/ab39a04d-b2e6-463b-9b8e-ddea725422f5',
            'md5': 'ef850763b175d8a3c7fba5e2dbdc6bc5',
            'info_dict': {
                'id': 'ab39a04d-b2e6-463b-9b8e-ddea725422f5',
                'title': 'Life\'s a Soundtrack · AI Funk Factory @ YT by @funk | Suno',
                'description': 'groovy funk, melodic song. Listen and make your own with Suno.',
                'thumbnail': 'https://cdn2.suno.ai/image_903f2bd7-ccc0-4029-a76a-887f07ebc2df.jpeg',
                'ext': 'mp3',
            },
        },
        {
            'url': 'https://suno.com/song/9cbcb5f4-f367-4f1c-8a32-23ec62bdc47e',
            'md5': '2f038badef88d189891d5f8cd8d8804d',
            'info_dict': {
                'id': '9cbcb5f4-f367-4f1c-8a32-23ec62bdc47e',
                'title': 'Pequenos Prazeres da Vida by @groovebot | Suno',
                'description': 'pop bossa nova song. Listen and make your own with Suno.',
                'thumbnail': 'https://cdn2.suno.ai/image_9cbcb5f4-f367-4f1c-8a32-23ec62bdc47e.jpeg',
                'ext': 'mp3',
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        return {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
            'url': self._og_search_property('audio', webpage),
        }
