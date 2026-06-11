import json
import re

from .common import InfoExtractor
from ..utils import ExtractorError, determine_ext, int_or_none, orderedSet, urljoin


class UdioIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?udio\.com/songs/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.udio.com/songs/ehJuLz9DuCtVapQMVMcA7N',
        'info_dict':
            {
                'id': 'ehJuLz9DuCtVapQMVMcA7N',
                'ext': 'mp3',
                'title': 'Lost Love',
                'description': "Listen to Lost Love by The I Don't Knows on Udio. Discover, create, and share music with the world. Use the latest technology to create AI music in seconds.",
                'uploader': "The I Don't Knows",
                'uploader_url': "https://udio.com/artist/The I Don't Knows",
            },
    }, {
        'url': 'https://www.udio.com/songs/hGZqWy3bPMrN3tosf5QZqt',
        'info_dict':
            {
                'id': 'hGZqWy3bPMrN3tosf5QZqt',
                'ext': 'mp3',
                'title': 'Batou - What is this love thing? (feat. EchoShadow)',
                'description': 'Listen to Batou - What is this love thing? (feat. EchoShadow) by DigitalScribe on Udio. Discover, create, and share music with the world. Use the latest technology to create AI music in seconds.',
                'uploader': 'DigitalScribe',
                'uploader_url': 'https://udio.com/artist/DigitalScribe',
            },
    }, {
        'url': 'https://www.udio.com/songs/dRFAMqCzqkTAX13F4MTKCb',
        'info_dict': {
            'id': 'dRFAMqCzqkTAX13F4MTKCb',
            'ext': 'mp3',
            'title': 'Évasion en Route',
            'description': 'Listen to Évasion en Route by aveiro on Udio. Discover, create, and share music with the world. Use the latest technology to create AI music in seconds.',
            'uploader': 'aveiro',
            'uploader_url': 'https://udio.com/artist/aveiro',
        },
    }, {
        'url': 'https://www.udio.com/songs/edMsDRvAiFosixHHTVbJ1L',
        'info_dict': {
            'id': 'edMsDRvAiFosixHHTVbJ1L',
            'ext': 'mp3',
            'title': 'Charlie e la Felicità ext v2.2',
            'description': 'Listen to Charlie e la Felicità ext v2.2 by GIANI_curzioilGRANDE on Udio. Discover, create, and share music with the world. Use the latest technology to create AI music in seconds.',
            'uploader': 'GIANI_curzioilGRANDE',
            'uploader_url': 'https://udio.com/artist/GIANI_curzioilGRANDE',
        },
    }, {
        'url': 'https://www.udio.com/songs/fPoZ7yLUv8orY2sNzeYNFp',
        'info_dict': {
            'id': 'fPoZ7yLUv8orY2sNzeYNFp',
            'ext': 'mp3',
            'title': 'Nocturnal Vibes',
            'description': 'Listen to Nocturnal Vibes by RaulKong898 on Udio. Discover, create, and share music with the world. Use the latest technology to create AI music in seconds.',
            'uploader': 'RaulKong898',
            'uploader_url': 'https://udio.com/artist/RaulKong898',
        },
    }, {
        'url': 'https://www.udio.com/songs/pzGGivV6oAR76ZxsnkbVw2',
        'info_dict': {
            'id': 'pzGGivV6oAR76ZxsnkbVw2',
            'ext': 'mp3',
            'title': 'Eternal Darkness',
            'description': 'Listen to Eternal Darkness by Para$Graf0815 on Udio. Discover, create, and share music with the world. Use the latest technology to create AI music in seconds.',
            'uploader': 'Para$Graf0815',
            'uploader_url': 'https://udio.com/artist/Para$Graf0815',
        },
    }, {
        'url': 'https://www.udio.com/songs/hSzvdEyBjBXF2CdsJP4zYr',
        'info_dict': {
            'id': 'hSzvdEyBjBXF2CdsJP4zYr',
            'ext': 'mp3',
            'title': 'Revenge of the Dreamer',
            'description': 'Listen to Revenge of the Dreamer by Doc Immortal on Udio. Discover, create, and share music with the world. Use the latest technology to create AI music in seconds.',
            'uploader': 'Doc Immortal',
            'uploader_url': 'https://udio.com/artist/Doc Immortal',
        },
    },
    ]

    def _format_from_og_video(self, url, webpage):
        fmt = {
            'url': url,
            'ext': determine_ext(url),
        }
        width = int_or_none(self._html_search_meta('og:video:width', webpage, default=None))
        height = int_or_none(self._html_search_meta('og:video:height', webpage, default=None))
        if width:
            fmt['width'] = width
        if height:
            fmt['height'] = height
        video_type = self._html_search_meta('og:video:type', webpage, default=None)
        if video_type and video_type.startswith('audio/'):
            fmt['vcodec'] = 'none'
        return fmt

    def _extract_formats(self, webpage):
        formats = []
        seen_urls = set()
        for prop in ('video:secure_url', 'video:url', 'video'):
            media_url = self._og_search_property(prop, webpage, default=None)
            if media_url and media_url not in seen_urls:
                seen_urls.add(media_url)
                formats.append(self._format_from_og_video(media_url, webpage))

        if not formats:
            for media_url in orderedSet(re.findall(
                    r'https://storage\.googleapis\.com/udio-artifacts[^\s"\'<>\\]+\.mp3', webpage)):
                if media_url not in seen_urls:
                    seen_urls.add(media_url)
                    formats.append({
                        'url': media_url,
                        'ext': 'mp3',
                        'vcodec': 'none',
                    })

        return formats

    def _real_extract(self, url):
        song_id = self._match_id(url)
        webpage = self._download_webpage(url, song_id)
        artist_name, title = self._html_extract_title(webpage, default=None).split('-', 1)
        title = title.split('|', 1)

        return {
            'id': song_id,
            'title': title[0].strip(),
            'description': self._og_search_description(webpage, default=None),
            'uploader': artist_name.strip(),
            'uploader_url': urljoin('https://udio.com/artist/', artist_name.strip()),
            'formats': self._extract_formats(webpage),
        }


class UdioListIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?udio\.com/(?P<list_type>(?!songs)[^/]+)/(?P<id>[^/?#&]+)'
    _FALLBACK_SEARCH = {
        'tags': lambda list_id: {'searchTerm': list_id},
        'genres': lambda list_id: {'searchTerm': list_id},
        'collections': lambda list_id: {'searchTerm': list_id},
        'artists': lambda list_id: {'searchTerm': list_id},
    }
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
    }, {
        'url': 'https://www.udio.com/playlists/5neZf7yJ2xXBHh12GUDM2w',
        'info_dict': {
            'id': '5neZf7yJ2xXBHh12GUDM2w',
            'title': '02_80s Secret Songs',
        },
        'playlist_count': 6,
    }]

    def _search_songs(self, search_query, list_id, page_size=100, max_count=None):
        songs = []
        page_param = 0
        while True:
            response = self._download_json(
                'https://www.udio.com/api/songs/search', list_id,
                data=json.dumps({
                    'searchQuery': search_query,
                    'pageSize': page_size,
                    'pageParam': page_param,
                    'readOnly': True,
                }).encode(),
                headers={'Content-Type': 'application/json'},
                note=f'Downloading songs page {page_param // page_size + 1}',
            )
            data = response.get('data') or []
            songs.extend(data)
            if max_count and len(songs) >= max_count:
                return songs[:max_count]
            if not data or len(data) < page_size:
                break
            page_param += page_size
        return songs

    def _fetch_playlist(self, playlist_id):
        response = self._download_json(
            'https://www.udio.com/api/playlists', playlist_id,
            query={'id': playlist_id},
            note='Downloading playlist metadata',
        )
        playlists = response.get('playlists') or []
        if not playlists:
            raise ExtractorError('Playlist not found', expected=True)
        return playlists[0]

    def _fetch_playlist_songs(self, playlist):
        playlist_id = playlist['id']
        song_list = playlist.get('song_list')
        if song_list:
            songs = []
            for idx in range(0, len(song_list), 20):
                batch = song_list[idx:idx + 20]
                response = self._download_json(
                    'https://www.udio.com/api/songs', playlist_id,
                    query={'songIds': ','.join(batch), 'readOnly': 'true'},
                    note=f'Downloading songs {idx + 1}-{idx + len(batch)}',
                )
                songs.extend(response.get('songs') or [])
            return songs

        track_count = int_or_none(playlist.get('track_count'))
        page_size = min(track_count or 100, 100)
        return self._search_songs(
            {'sort': 'playlist', 'playlistId': playlist_id},
            playlist_id, page_size=page_size, max_count=track_count)

    def _song_to_entry(self, song):
        song_id = song['id']
        entry = {
            '_type': 'url_transparent',
            'url': urljoin('https://www.udio.com/', f'songs/{song_id}'),
            'ie_key': 'Udio',
            'id': song_id,
        }
        if title := song.get('title'):
            entry['title'] = title
        if artist := song.get('artist'):
            entry['uploader'] = artist
        if thumbnail := song.get('image_path'):
            entry['thumbnail'] = thumbnail
        return entry

    def _find_links(self, webpage, base_url=None):
        relative_links = re.findall(r'href="(/songs/[^"?&/]+)"', webpage)

        if not base_url:
            base_url = 'https://www.udio.com'

        return [urljoin(base_url, relative_link) for relative_link in relative_links]

    def _entries_from_webpage(self, webpage):
        entries = []
        for song_url in orderedSet(self._find_links(webpage)):
            song_id = self._search_regex(r'/songs/([^/?#&]+)', song_url, 'song id')
            entries.append(self.url_result(song_url, 'Udio', song_id))
        return entries

    def _real_extract(self, url):
        list_type, list_id = self._match_valid_url(url).group('list_type', 'id')

        if list_type == 'playlists':
            try:
                playlist = self._fetch_playlist(list_id)
            except ExtractorError:
                pass
            else:
                entries = [self._song_to_entry(song) for song in self._fetch_playlist_songs(playlist)]
                title = playlist.get('name') or f'{list_type}: {list_id}'
                return self.playlist_result(entries, list_id, title)

        webpage = self._download_webpage(url, list_id)
        entries = self._entries_from_webpage(webpage)
        if not entries:
            search_builder = self._FALLBACK_SEARCH.get(list_type)
            if search_builder:
                entries = [
                    self._song_to_entry(song)
                    for song in self._search_songs(search_builder(list_id), list_id, page_size=50)
                ]
            elif list_type == 'playlists':
                raise ExtractorError('Playlist not found', expected=True)

        return self.playlist_result(entries, list_id, f'{list_type}: {list_id}')
