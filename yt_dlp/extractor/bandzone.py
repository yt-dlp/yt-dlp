from .common import InfoExtractor
from ..utils import (
    js_to_json,
)


class BandzoneIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?bandzone\.cz/(?P<id>[^/\?%#]+).*'
    _TESTS = [{
        'url': 'https://bandzone.cz/neplatnaidentita',
        'info_dict': {
            'id': 'neplatnaidentita',
            'title': 'Neplatná Identita',
            'uploader': 'Neplatná Identita',
            'description': 'md5:ef2869f1c4049f90cd241a15a167c7fa',
            'thumbnail': 'https://bzmedia.cz/band/ne/neplatnaidentita/gallery/profile.default/208613_p.jpg',
        },
        'playlist_count': 5,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(f'https://bandzone.cz/{playlist_id}?at=info', playlist_id)
        artist_name = self._html_search_meta('og:title', webpage)
        playlist = self._parse_json(
            self._search_regex(r'const\s+loadedPlaylist\s*=\s*(\[.+\]);', webpage, 'playlist'),
            playlist_id, transform_source=js_to_json)
        trackRepositoryUrl = self._search_regex(r'const\s+trackRepositoryUrl\s*=\s*\'(.+)\';', webpage, 'trackRepositoryUrl')
        profile_info = self._html_search_regex(r'(?s)<span class="profile__city">\s*(.*?)\n\s*</span>', webpage, 'profile')
        band_bio = self._html_search_regex(r'(?s)<section class="tabs__section" id="bandBio">(.*?)</section>', webpage, 'band_bio')
        band_info = self._html_search_regex(r'(?s)<section class="tabs__section" id="bandInfo">(.*?)</section>', webpage, 'band_info')

        def entry(entry):
            return {
                '_type': 'video',
                'id': entry.get('trackId'),
                'url': '/'.join([trackRepositoryUrl, entry.get('homePath'), entry.get('storagePath'), entry.get('fileName')]),
                'title': entry.get('title'),
                'track': entry.get('title'),
                'album': entry.get('albumTitle'),
                'artists': [artist_name],
                'release_year': entry.get('albumReleasedYear'),
            }

        return {
            '_type': 'playlist',
            'id': playlist_id,
            'title': artist_name,
            'description': ' - '.join([artist_name, profile_info, band_info, band_bio]),
            'thumbnail': self._html_search_meta('og:image', webpage),
            'uploader': artist_name,
            'entries': list(map(entry, playlist)),
        }
