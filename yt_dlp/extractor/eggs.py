import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    url_or_none,
    unescapeHTML,
)


class EggsBaseIE(InfoExtractor):
    def _parse_artist_name(self, webpage):
        artist = self._search_regex(
            r'<div[^>]+class=(["\'])artist_name\1[^>]*>([^<]+)</div>',
            webpage, 'artist name', fatal=False, default=None, group=2
        )
        if artist:
            return artist.strip()

        og_title = self._html_search_meta(['og:title'], webpage, 'og:title', default=None)
        if og_title:
            artist_match = re.search(r'(?P<artist>[^()]+)(?:\([^)]*\))?のEggsページ', og_title)
            if artist_match:
                return artist_match.group('artist').strip()

        return 'Unknown Artist'

    def _parse_single_song(self, url, webpage, default_artist='Unknown Artist'):
        song_id = self._search_regex(
            r'/song/(?P<id>[^/?#&]+)',
            url, 'song id', fatal=False, default=None, group='id'
        )

        track_title = self._search_regex(
            r'<div[^>]+class=(["\'])product_name\1[^>]*>\s*<p>([^<]+)</p>',
            webpage, 'track title', fatal=False, default=None, group=2
        )

        if not track_title:
            page_title = self._search_regex(
                r'<title>(?P<title>[^<]+)</title>',
                webpage, 'page title', fatal=False, default=None, group='title'
            )
            if page_title:
                inner_match = re.search(r'「(?P<inner>[^」]+)」', page_title)
                if inner_match:
                    track_title = inner_match.group('inner').strip()

        if not track_title:
            track_title = 'Unknown Title'

        artist = default_artist
        if not artist or artist == 'Unknown Artist':
            artist_regex = r'<span[^>]+class=(["\'])artist_name\1[^>]*>\s*<a[^>]*>([^<]+)</a>'
            fallback_artist = self._search_regex(
                artist_regex, webpage, 'artist name',
                fatal=False, default=None, group=2
            )
            if fallback_artist:
                artist = fallback_artist.strip()

        audio_url = self._search_regex(
            r'<div[^>]+class=(["\'])[^"\']*player[^"\']*\1[^>]+data-src=(["\'])(?P<audio_url>[^"\']+)\2',
            webpage, 'audio url', fatal=True, group='audio_url'
        )
        audio_url = url_or_none(unescapeHTML(audio_url))
        if not audio_url:
            raise ExtractorError('Invalid audio URL.', expected=True)

        thumbnail = (
            self._html_search_meta(['og:image'], webpage, 'thumbnail', default=None)
            or self._search_regex(
                r'<span[^>]*>\s*<img[^>]+src=(["\'])(?P<thumb>[^"\']+)\1',
                webpage, 'thumbnail', fatal=False, default=None, group='thumb'
            )
        )

        return {
            'id': song_id,
            'url': audio_url,
            'title': track_title,
            'uploader': artist,
            'vcodec': 'none',
            'thumbnail': thumbnail,
        }

    def _parse_artist_page(self, webpage, artist_id, artist_name):
        song_blocks = re.findall(r'(?s)<li[^>]+id="songs\d+"[^>]*>.*?</li>', webpage)
        entries = []

        for block in song_blocks:
            audio_url = self._search_regex(
                r'data-src=(["\'])(?P<url>https?://.*?\.(?:mp3|m4a).*?)\1',
                block, 'audio url', fatal=False, default=None, group='url'
            )
            audio_url = url_or_none(unescapeHTML(audio_url))
            if not audio_url:
                continue

            track_id = self._search_regex(
                r'data-srcid=(["\'])(?P<id>[^"\'<>]+)\1',
                block, 'track id', fatal=False, default=None, group='id'
            )
            if not track_id:
                continue

            title = self._search_regex(
                r'data-srcname=(["\'])(?P<title>[^"\']+)\1',
                block, 'track title', fatal=False, default=None, group='title'
            )
            if not title:
                title = 'Unknown Title'

            thumbnail = self._search_regex(
                r'<img[^>]+src=(["\'])(?P<th>[^"\']+)\1',
                block, 'thumbnail', fatal=False, default=None, group='th'
            )

            entries.append({
                'id': track_id,
                'url': audio_url,
                'title': title,
                'uploader': artist_name,
                'vcodec': 'none',
                'thumbnail': thumbnail,
            })

        return entries

class EggsIE(EggsBaseIE):
    IE_NAME = 'eggs:single'
    _VALID_URL = (
        r'https?://(?:www\.)?eggs\.mu/artist/(?P<artist_id>[^/]+)/song/(?P<song_id>[^/]+)'
    )
    _TESTS = [{
        'url': 'https://eggs.mu/artist/32_sunny_girl/song/0e95fd1d-4d61-4d5b-8b18-6092c551da90',
        'info_dict': {
            'id': '0e95fd1d-4d61-4d5b-8b18-6092c551da90',
            'ext': 'm4a',
            'title': 'シネマと信号',
            'uploader': 'Sunny Girl',
            'thumbnail': r're:^https?://.*\.jpg(?:\?.*)?$',
        },
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        song_id = mobj.group('song_id')
        webpage = self._download_webpage(url, song_id)
        artist_name = self._parse_artist_name(webpage)
        info = self._parse_single_song(url, webpage, artist_name)
        return info

class EggsArtistIE(EggsBaseIE):
    IE_NAME = 'eggs:artist'
    _VALID_URL = (
        r'https?://(?:www\.)?eggs\.mu/artist/(?P<artist_id>[^/]+)'
    )
    _TESTS = [{
        'url': 'https://eggs.mu/artist/32_sunny_girl',
        'info_dict': {
            'id': '32_sunny_girl',
            'title': 'Sunny Girl',
        },
        'playlist_count': 18,
    }]

    def _real_extract(self, url):
        artist_id = self._match_valid_url(url).group('artist_id')
        webpage = self._download_webpage(url, artist_id)
        artist_name = self._parse_artist_name(webpage)
        entries = self._parse_artist_page(webpage, artist_id, artist_name)
        return self.playlist_result(
            entries,
            playlist_id=artist_id,
            playlist_title=artist_name
        )