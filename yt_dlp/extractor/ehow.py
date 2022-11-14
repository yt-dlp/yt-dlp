from .common import InfoExtractor
from ..compat import compat_urllib_parse_unquote


class EHowIE(InfoExtractor):
    IE_NAME = 'eHow'
    _VALID_URL = r'https?://(?:www\.)?ehow\.com/[^/_?]*_(?P<id>[0-9]+)'
    _TEST = {
        'url': 'http://www.ehow.com/video_12245069_hardwood-flooring-basics.html',
        'md5': '9809b4e3f115ae2088440bcb4efbf371',
        'info_dict': {
            'id': '12245069',
            'ext': 'flv',
            'title': 'Hardwood Flooring Basics',
            'description': 'Hardwood flooring may be time consuming, but its ultimately a pretty straightforward concept. Learn about hardwood flooring basics with help from a hardware flooring business owner in this free video...',
            'uploader': 'Erick Nathan',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        video_url = self._search_regex(
            r'(?:file|source)=(http[^\'"&]*)', webpage, 'video URL')
        final_url = compat_urllib_parse_unquote(video_url)
        uploader = self._html_search_meta('uploader', webpage)
        title = self._og_search_title(webpage).replace(' | eHow', '')

        return {
            'id': video_id,
            'url': final_url,
            'title': title,
            'thumbnail': self._og_search_thumbnail(webpage),
            'description': self._og_search_description(webpage),
            'uploader': uploader,
        }
