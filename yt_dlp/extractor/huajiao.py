from .common import InfoExtractor
from ..utils import (
    parse_duration,
    parse_iso8601,
)


class HuajiaoIE(InfoExtractor):
    IE_DESC = '花椒直播'
    _VALID_URL = r'https?://(?:www\.)?huajiao\.com/l/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'http://www.huajiao.com/l/38941232',
        'md5': 'd08bf9ac98787d24d1e4c0283f2d372d',
        'info_dict': {
            'id': '38941232',
            'ext': 'mp4',
            'title': '#新人求关注#',
            'description': 're:.*',
            'duration': 2424.0,
            'thumbnail': r're:^https?://.*\.jpg$',
            'timestamp': 1475866459,
            'upload_date': '20161007',
            'uploader': 'Penny_余姿昀',
            'uploader_id': '75206005',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        feed_json = self._search_regex(
            r'var\s+feed\s*=\s*({.+})', webpage, 'feed json')
        feed = self._parse_json(feed_json, video_id)

        description = self._html_search_meta(
            'description', webpage, 'description', fatal=False)

        def get(section, field):
            return feed.get(section, {}).get(field)

        return {
            'id': video_id,
            'title': feed['feed']['formated_title'],
            'description': description,
            'duration': parse_duration(get('feed', 'duration')),
            'thumbnail': get('feed', 'image'),
            'timestamp': parse_iso8601(feed.get('creatime'), ' '),
            'uploader': get('author', 'nickname'),
            'uploader_id': get('author', 'uid'),
            'formats': self._extract_m3u8_formats(
                feed['feed']['m3u8'], video_id, 'mp4', 'm3u8_native'),
        }
