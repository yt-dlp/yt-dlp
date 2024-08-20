from .common import InfoExtractor
from ..utils import remove_end


class EbayIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ebay\.com/itm/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.ebay.com/itm/194509326719',
        'info_dict': {
            'id': '194509326719',
            'ext': 'mp4',
            'title': 'WiFi internal antenna adhesive for wifi 2.4GHz wifi 5 wifi 6 wifi 6E full bands',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        video_json = self._search_json(r'"video":', webpage, 'video json', video_id)

        formats = []
        for key, url in video_json['playlistMap'].items():
            if key == 'HLS':
                formats.extend(self._extract_m3u8_formats(url, video_id, fatal=False))
            elif key == 'DASH':
                formats.extend(self._extract_mpd_formats(url, video_id, fatal=False))
            else:
                self.report_warning(f'Unsupported format {key}', video_id)

        return {
            'id': video_id,
            'title': remove_end(self._html_extract_title(webpage), ' | eBay'),
            'formats': formats,
        }
