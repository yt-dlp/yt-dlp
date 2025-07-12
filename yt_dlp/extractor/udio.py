import re

from .common import InfoExtractor
from ..utils import determine_ext, urljoin


class UdioIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?udio\.com/songs/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.udio.com/songs/ehJuLz9DuCtVapQMVMcA7N',
        'info_dict':
            {
                'id': 'ehJuLz9DuCtVapQMVMcA7N',
                'title': 'Lost Love',
                'description': "Listen to Lost Love by The I Don't Knows on Udio. Discover, create, and share music with the world. Use the latest technology to create AI music in seconds.",
                'uploader': "The I Don't Knows",
                'uploader_url': "https://udio.com/artist/The I Don't Knows",
            },
        'playlist_count': 1,
    }, {
        'url': 'https://www.udio.com/songs/hGZqWy3bPMrN3tosf5QZqt',
        'info_dict':
            {
                'id': 'hGZqWy3bPMrN3tosf5QZqt',
                'title': 'Batou - What is this love thing? (feat. EchoShadow)',
                'description': 'Listen to Batou - What is this love thing? (feat. EchoShadow) by DigitalScribe on Udio. Discover, create, and share music with the world. Use the latest technology to create AI music in seconds.',
                'uploader': 'DigitalScribe',
                'uploader_url': 'https://udio.com/artist/DigitalScribe',
            },
        'playlist_count': 1,
    }, {
        'url': 'https://www.udio.com/songs/dRFAMqCzqkTAX13F4MTKCb',
        'info_dict': {
            'id': 'dRFAMqCzqkTAX13F4MTKCb',
            'title': 'Évasion en Route',
            'description': 'Listen to Évasion en Route by aveiro on Udio. Discover, create, and share music with the world. Use the latest technology to create AI music in seconds.',
            'uploader': 'aveiro',
            'uploader_url': 'https://udio.com/artist/aveiro',
        },
        'playlist_count': 1,
    }, {
        'url': 'https://www.udio.com/songs/edMsDRvAiFosixHHTVbJ1L',
        'info_dict': {
            'id': 'edMsDRvAiFosixHHTVbJ1L',
            'title': 'Charlie e la Felicità ext v2.2',
            'description': 'Listen to Charlie e la Felicità ext v2.2 by GIANI_curzioilGRANDE on Udio. Discover, create, and share music with the world. Use the latest technology to create AI music in seconds.',
            'uploader': 'GIANI_curzioilGRANDE',
            'uploader_url': 'https://udio.com/artist/GIANI_curzioilGRANDE',
        },
        'playlist_count': 1,
    }, {
        'url': 'https://www.udio.com/songs/fPoZ7yLUv8orY2sNzeYNFp',
        'info_dict': {
            'id': 'fPoZ7yLUv8orY2sNzeYNFp',
            'title': 'Nocturnal Vibes',
            'description': 'Listen to Nocturnal Vibes by RaulKong898 on Udio. Discover, create, and share music with the world. Use the latest technology to create AI music in seconds.',
            'uploader': 'RaulKong898',
            'uploader_url': 'https://udio.com/artist/RaulKong898',
        },
        'playlist_count': 1,
    }, {
        'url': 'https://www.udio.com/songs/pzGGivV6oAR76ZxsnkbVw2',
        'info_dict': {
            'id': 'pzGGivV6oAR76ZxsnkbVw2',
            'title': 'Eternal Darkness',
            'description': 'Listen to Eternal Darkness by Para$Graf0815 on Udio. Discover, create, and share music with the world. Use the latest technology to create AI music in seconds.',
            'uploader': 'Para$Graf0815',
            'uploader_url': 'https://udio.com/artist/Para$Graf0815',
        },
        'playlist_count': 1,
    }, {
        'url': 'https://www.udio.com/songs/hSzvdEyBjBXF2CdsJP4zYr',
        'info_dict': {
            'id': 'hSzvdEyBjBXF2CdsJP4zYr',
            'title': 'Revenge of the Dreamer',
            'description': 'Listen to Revenge of the Dreamer by Doc Immortal on Udio. Discover, create, and share music with the world. Use the latest technology to create AI music in seconds.',
            'uploader': 'Doc Immortal',
            'uploader_url': 'https://udio.com/artist/Doc Immortal',
        },
        'playlist_count': 1,
    },
    ]

    def _real_extract(self, url):
        song_id = self._match_id(url)
        webpage = self._download_webpage(url, song_id)
        media_url = self._og_search_video_url(webpage, default=None)
        artist_name, title = self._html_extract_title(webpage, default=None).split('-', 1)
        title = title.split('|', 1)
        lyrics = self._search_regex(
            r'<pre>\s*(.*?)\s*</pre>',
            webpage,
            'lyrics',
            default=None,
        )

        return {
            'id': song_id,
            'title': title[0].strip(),
            'description': lyrics,
            'uploader': artist_name.strip(),
            'uploader_url': urljoin('https://udio.com/artist/', artist_name.strip()),
            'formats': [{
                'url': media_url,
                'ext': determine_ext(media_url),
            }],
        }


class UdioListIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?udio\.com/(?P<list_type>(?!songs)[^/]+)/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.udio.com/tags/flute',
        'info_dict': {
            'id': 'flute',
            'title': 'tags: flute',
        },
        'playlist_mincount': 5,
    },
        {
        'url': 'https://www.udio.com/collections/trending',
        'info_dict': {
            'id': 'trending',
            'title': 'collections: trending',
        },
        'playlist_mincount': 3,
    },
        {
        'url': 'https://www.udio.com/genres/metal',
        'info_dict': {
            'id': 'metal',
            'title': 'genres: metal',
        },
        'playlist_mincount': 3,
    },
        {
        'url': 'https://www.udio.com/artists/DigitalScribe',
        'info_dict': {
            'id': 'DigitalScribe',
            'title': 'artists: DigitalScribe',
        },
        'playlist_mincount': 1,
    },
        {
        'url': 'https://www.udio.com/playlists/featured',
        'info_dict': {
            'id': 'featured',
            'title': 'playlists: featured',
        },
        'playlist_mincount': 3,
    }]

    def _find_links(self, webpage, base_url=None):
        relative_links = re.findall(r'href="(/songs/[^"?&/]+)"', webpage)

        if not base_url:
            base_url = 'https://www.udio.com'

        return [f'{base_url}{relative_link}' for relative_link in relative_links]

    def _real_extract(self, url):
        list_type, list_id = self._match_valid_url(url).group('list_type', 'id')
        webpage = self._download_webpage(url, list_id)

        song_cards = re.findall(r'<div[^>]*class="[^"]*song-card[^"]*"[^>]*>(.*?)</div>\s*</div>',
                                webpage, re.DOTALL)

        self.to_screen(f'Found {len(song_cards)} song cards')

        entries = []
        for card in song_cards:
            song_url_match = re.search(r'href="(/songs/([^"?&/]+))"', card)
            if not song_url_match:
                continue

            song_path = song_url_match.group(1)
            song_id = song_url_match.group(2)
            song_url = urljoin('https://www.udio.com/', song_path)

            song_title = self._search_regex(
                r'<div[^>]*class="[^"]*song-title[^"]*"[^>]*>(.*?)</div>',
                card, 'song title', default=None)

            artist_name = self._search_regex(
                r'<div[^>]*class="[^"]*artist-name[^"]*"[^>]*>(.*?)</div>',
                card, 'artist name', default=None)

            thumbnail = self._search_regex(
                r'<img[^>]*src="([^"]+)"[^>]*class="[^"]*song-cover[^"]*"',
                card, 'thumbnail', default=None)

            if song_title or artist_name or thumbnail:
                self.to_screen(f'Found metadata for song {song_id}: {song_title} by {artist_name}')
                entry = {
                    '_type': 'url_transparent',
                    'url': song_url,
                    'ie_key': 'Udio',
                    'id': song_id,
                }

                if song_title:
                    entry['title'] = song_title
                if artist_name:
                    entry['uploader'] = artist_name
                if thumbnail:
                    entry['thumbnail'] = thumbnail

                entries.append(entry)
            else:
                entries.append(self.url_result(song_url, 'Udio', song_id))

        if not entries:
            self.to_screen('No song cards found, trying alternative methods')
            song_urls = self._find_links(webpage)

            for song_url in song_urls:
                song_id = self._search_regex(r'/songs/([^/?#&]+)', song_url, 'song id')
                entries.append(self.url_result(song_url, 'Udio', song_id))

        self.to_screen(f'Found {len(entries)} entries')
        return self.playlist_result(entries, list_id, f'{list_type}: {list_id}')
