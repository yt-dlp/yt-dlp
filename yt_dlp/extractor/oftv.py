from .common import InfoExtractor
from .zype import ZypeIE
from ..utils import traverse_obj


class OfTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?of.tv/video/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://of.tv/video/627d7d95b353db0001dadd1a',
        'md5': 'cb9cd5db3bb9ee0d32bfd7e373d6ef0a',
        'info_dict': {
            'id': '627d7d95b353db0001dadd1a',
            'ext': 'mp4',
            'title': 'E1: Jacky vs Eric',
            'thumbnail': r're:^https?://.*\.jpg',
            'average_rating': 0,
            'description': 'md5:dd16e3e2a8d27d922e7a989f85986853',
            'display_id': '',
            'duration': 1423,
            'timestamp': 1652391300,
            'upload_date': '20220512',
            'view_count': 0,
            'creator': 'This is Fire'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        info = next(ZypeIE.extract_from_webpage(self._downloader, url, webpage))
        info['_type'] = 'url_transparent'
        info['creator'] = self._search_regex(r'<a[^>]+class=\"creator-name\"[^>]+>([^<]+)', webpage, 'creator')
        return info


class OfTVPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?of.tv/creators/(?P<id>[a-zA-Z0-9-]+)/.?'
    _TESTS = [{
        'url': 'https://of.tv/creators/this-is-fire/',
        'playlist_count': 8,
        'info_dict': {
            'id': 'this-is-fire'
        }
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)

        json_match = self._search_json(
            r'var\s*remaining_videos\s*=', webpage, 'oftv playlists', playlist_id, contains_pattern=r'\[.+\]')

        return self.playlist_from_matches(
            traverse_obj(json_match, (..., 'discovery_url')), playlist_id)
