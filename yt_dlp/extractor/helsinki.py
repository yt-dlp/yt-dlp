from .common import InfoExtractor
from ..utils import js_to_json


class HelsinkiIE(InfoExtractor):
    IE_DESC = 'helsinki.fi'
    _VALID_URL = r'https?://video\.helsinki\.fi/Arkisto/flash\.php\?id=(?P<id>\d+)'
    _TEST = {
        'url': 'http://video.helsinki.fi/Arkisto/flash.php?id=20258',
        'info_dict': {
            'id': '20258',
            'ext': 'mp4',
            'title': 'Tietotekniikkafoorumi-iltapäivä',
            'description': 'md5:f5c904224d43c133225130fe156a5ee0',
        },
        'params': {
            'skip_download': True,  # RTMP
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        params = self._parse_json(self._html_search_regex(
            r'(?s)jwplayer\("player"\).setup\((\{.*?\})\);',
            webpage, 'player code'), video_id, transform_source=js_to_json)
        formats = [{
            'url': s['file'],
            'ext': 'mp4',
        } for s in params['sources']]
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': self._og_search_title(webpage).replace('Video: ', ''),
            'description': self._og_search_description(webpage),
            'formats': formats,
        }
