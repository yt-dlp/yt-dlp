import re

from .common import InfoExtractor
from ..utils import ExtractorError, unescapeHTML


class SunoBaseIE(InfoExtractor):
    def _get_title(self, webpage):
        return self._html_search_meta(
            ['og:title', 'twitter:title'], webpage, 'title',
            default=None) or self._html_extract_title(webpage)

    def _get_description(self, webpage):
        return self._html_search_meta(
            ['og:description', 'description', 'twitter:description'],
            webpage, 'description', default=None)

    def _get_thumbnail(self, webpage):
        return self._html_search_meta(
            ['og:image', 'twitter:image'], webpage, 'thumbnail', default=None)


class SunoIE(SunoBaseIE):
    _VALID_URL = r'https?://(?:www\.)?suno\.com/song/(?P<id>[-a-f0-9]+)'
    _TESTS = [
        {
            'url': 'https://suno.com/song/ab39a04d-b2e6-463b-9b8e-ddea725422f5',
            'md5': 'ef850763b175d8a3c7fba5e2dbdc6bc5',
            'info_dict': {
                'id': 'ab39a04d-b2e6-463b-9b8e-ddea725422f5',
                'title': 'Life\'s a Soundtrack · AI Funk Factory @ YT by @funk | Suno',
                'description': 'groovy funk, melodic song. Listen and make your own with Suno.',
                'thumbnail': r're:https?://.*903f2bd7-ccc0-4029-a76a-887f07ebc2df.*\.jpeg$',
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
                'thumbnail': r're:https?://.*9cbcb5f4-f367-4f1c-8a32-23ec62bdc47e.*\.jpeg$',
                'ext': 'mp3',
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        url = self._html_search_meta(
            ['og:audio', 'twitter:player:stream'], webpage, 'url', default=None)

        return {
            'id': video_id,
            'title': self._get_title(webpage),
            'description': self._get_description(webpage),
            'thumbnail': self._get_thumbnail(webpage),
            'url': url,
        }


class SunoPlaylistIE(SunoBaseIE):
    _VALID_URL = r'https?://(?:www\.)?suno\.com/playlist/(?P<id>[-a-f0-9]+)'
    _TESTS = [
        {
            'url': 'https://suno.com/playlist/01f2ac32-c32e-4d26-b10c-221107c02946',
            'info_dict': {
                'id': '01f2ac32-c32e-4d26-b10c-221107c02946',
                'title': 'Main 0 by @contemplativetranspositions367 | Suno',
                'description': 'Hopefully the test case passed',
                'thumbnail': r're:https?://.*19d6d518-1b87-43b3-90b9-2a476ca5824a.*\.jpeg$',
            },
            'playlist': [{
                'info_dict': {
                    'id': '19d6d518-1b87-43b3-90b9-2a476ca5824a',
                    'title': 'Ceaseless <Echoes>',
                    'ext': 'mp3',
                },
            }],
            'playlist_count': 1,
        },
        {
            'url': 'https://www.suno.com/playlist/568eeaab-dfbf-4da6-aa0a-0fb1a32330de',
            'info_dict': {
                'id': '568eeaab-dfbf-4da6-aa0a-0fb1a32330de',
                'title': 'Piano by @kunal | Suno',
                'description': 'Here are some good piano',
                'thumbnail': r're:https?://.*0ecc0956-3b17-4d4b-8504-55849dd75e22.*\.jpeg$',
            },
            'playlist': [
                {
                    'info_dict': {
                        'id': '0ecc0956-3b17-4d4b-8504-55849dd75e22',
                        'title': 'ST',
                        'ext': 'mp3',
                    },
                },
                {
                    'info_dict': {
                        'id': '3fef7d44-c5a3-4181-9de3-d81542af23ef',
                        'title': 'ST',
                        'ext': 'mp3',
                    },
                },
                {
                    'info_dict': {
                        'id': '15e797fa-06c0-4e11-8cc0-3b2580476039',
                        'title': 'ST - 2',
                        'ext': 'mp3',
                    },
                },
            ],
            'playlist_count': 3,
        },
    ]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)

        # There are <a>s whose href is a song/ID path. The <span>s directly
        # within them have the respective song title as their innerHTML.
        # Alternatively, this info can be extracted through parsing an escaped
        # JSON object inside a <script> array, though that seems even less stable
        # than this HTML.
        songs_regex = r'/song/(?P<id>[-a-f0-9]+)["\'][^>]*>\s*<span[^>]*>\s*(?P<title>[^<]+)</span>'
        songs = re.findall(songs_regex, webpage)

        og_audio_regex = self._og_regexes('audio')[0]
        audio_urls = [matches[0] for matches in re.findall(og_audio_regex, webpage)]

        if len(songs) != len(audio_urls):
            raise ExtractorError('Unexpected mismatch between song HTML list and og audio URLs')

        return {
            '_type': 'playlist',
            'id': playlist_id,
            'title': self._get_title(webpage),
            'description': self._get_description(webpage),
            'thumbnail': self._get_thumbnail(webpage),

            'entries': [{
                'id': song_tuple[0],
                'title': unescapeHTML(song_tuple[1]),
                'url': audio_urls[i],

            } for i, song_tuple in enumerate(songs)],
        }
