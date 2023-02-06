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
            'skip_download': 'm3u8',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        video_json = self._search_json(r'"video":', webpage, "video json", video_id)

        playlist_map = video_json.get('playlistMap')
        if not playlist_map:
            raise ExtractorError('Unable to extract video urls')

        formats = []
        for key, url in video_json['playlistMap'].items():
            if key == 'HLS':
                formats.extend(self._extract_m3u8_formats(url, video_id, fatal=False))
            elif key == 'DASH':
                formats.extend(self._extract_mpd_formats(url, video_id, fatal=False))
            else:
                self.report_warning('unsupported format found: %s' % key, video_id)

        return {
            'id': video_id,
            'title': video_json.get('title'),
            'formats': formats
        }
