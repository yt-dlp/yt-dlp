from .common import InfoExtractor
from ..utils import ExtractorError


class EbayIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ebay\.com/itm/(?P<id>\d+)'
    _TEST = {
        'url': 'https://www.ebay.com/itm/194509326719',
        'info_dict': {
            'id': '194509326719',
            'ext': 'mp4',
            'title': 'HELIX upload [AN_Master_A04B.mp4] - 1666069406072',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        video_json = self._search_json(r'"video":\s*', webpage, "video_json", video_id)

        playlist_map = video_json.get('playlistMap')
        if not playlist_map:
            raise ExtractorError('Unable to extract video urls')

        formats = []
        for key in playlist_map:
            if key == "HLS":
                formats.extend(self._extract_m3u8_formats(
                    playlist_map.get(key), video_id, m3u8_id='hls', fatal=False))
            if key == "DASH":
                formats.extend(self._extract_mpd_formats(
                    playlist_map.get(key), video_id, fatal=False))

        return {
            'id': video_id,
            'title': video_json.get('title'),
            'formats': formats
        }
