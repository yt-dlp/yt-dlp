from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    parse_iso8601,
    traverse_obj,
)

class UltimediaVideo(InfoExtractor):
    _VALID_URL = r'https?://www\.ultimedia\.com/default/index/videogeneric/id/\?(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [{
        'url': 'https://www.ultimedia.com/default/index/videogeneric/id/3x5x55k',
        'info_dict': {
            'id': '3x5x55k',
            'ext': 'mp4',
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        video_url = self._html_search_regex(
            r'(https?://[^"\']+\.mp4)', webpage, 'video URL', 
            fatal=False)
        
       
        video_data = self._search_regex(
            r'var\s+videoData\s*=\s*({.+?});', webpage, 'video data', default=None)
        sources = None
        if video_data:
            try:
                video_json = self._parse_json(video_data, video_id, fatal=False)
                sources = video_json.get('sources')
            except Exception:
                pass
        



