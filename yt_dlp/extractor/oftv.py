from .common import InfoExtractor
from .zype import ZypeIE
from ..utils import traverse_obj


class OfTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?of.tv/video/(?P<id>[0-9a-zA-Z]+)'
    _TESTS = [{
        'url': 'https://of.tv/video/627d7d95b353db0001dadd1a',
        'md5': 'cb9cd5db3bb9ee0d32bfd7e373d6ef0a',
        'info_dict': {
            'id': '627d7d95b353db0001dadd1a',
            'ext': 'mp4',
            'title': 'E1: Jacky vs Eric',
            'thumbnail': r're:^https?://.*\.jpg',
            'average_rating': 0,
            'description': 'Singer Jacky Romero and actor Eric Guilmette must step out of their comfort zones in order to take on the ultimate comfort food: the Monte Cristo sandwich. With only 30 minutes to deliver the perfect blend of sweet and savory,\xa0Jacky and Eric need all the help they can get to impress Chef JoJo and move on to the next round.\xa0\r\n\r\nSubscribe to the cast on OF:\r\nof.com/jackyromero \r\nof.com/eric_g \r\nof.com/grandmasterchefjojo',
            'display_id': '',
            'duration': 1423,
            'timestamp': 1652391300,
            'upload_date': '20220512',
            'view_count': 0,
            'md5': None
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        return next(ZypeIE.extract_from_webpage(self._downloader, url, webpage))


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

        remaining_videos = self._search_json(
            r'var\s*remaining_videos\s*=', webpage, 'oftv playlists', playlist_id, end_pattern=r';', contains_pattern=r'\[.+?\]')

        return self.playlist_from_matches(
            traverse_obj(remaining_videos, (..., 'discovery_url')), playlist_id)
