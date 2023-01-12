from .common import InfoExtractor
from ..utils import (
    smuggle_url,
    float_or_none,
    parse_iso8601,
    update_url_query,
)


class MovieClipsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?movieclips\.com/videos/.+-(?P<id>\d+)(?:\?|$)'
    _TEST = {
        'url': 'http://www.movieclips.com/videos/warcraft-trailer-1-561180739597',
        'md5': '42b5a0352d4933a7bd54f2104f481244',
        'info_dict': {
            'id': 'pKIGmG83AqD9',
            'ext': 'mp4',
            'title': 'Warcraft Trailer 1',
            'description': 'Watch Trailer 1 from Warcraft (2016). Legendary’s WARCRAFT is a 3D epic adventure of world-colliding conflict based.',
            'thumbnail': r're:^https?://.*\.jpg$',
            'timestamp': 1446843055,
            'upload_date': '20151106',
            'uploader': 'Movieclips',
        },
        'add_ie': ['ThePlatform'],
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        video = next(v for v in self._parse_json(self._search_regex(
            r'var\s+__REACT_ENGINE__\s*=\s*({.+});',
            webpage, 'react engine'), video_id)['playlist']['videos'] if v['id'] == video_id)

        return {
            '_type': 'url_transparent',
            'ie_key': 'ThePlatform',
            'url': smuggle_url(update_url_query(
                video['contentUrl'], {'mbr': 'true'}), {'force_smil_url': True}),
            'title': self._og_search_title(webpage),
            'description': self._html_search_meta('description', webpage),
            'duration': float_or_none(video.get('duration')),
            'timestamp': parse_iso8601(video.get('dateCreated')),
            'thumbnail': video.get('defaultImage'),
            'uploader': video.get('provider'),
        }
