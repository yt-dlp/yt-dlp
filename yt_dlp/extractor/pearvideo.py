import re

from .common import InfoExtractor
from ..utils import (
    qualities,
    unified_timestamp,
    traverse_obj,
)


class PearVideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pearvideo\.com/video_(?P<id>\d+)'
    _TEST = {
        'url': 'http://www.pearvideo.com/video_1076290',
        'info_dict': {
            'id': '1076290',
            'ext': 'mp4',
            'title': '小浣熊在主人家玻璃上滚石头：没砸',
            'description': 'md5:01d576b747de71be0ee85eb7cac25f9d',
            'timestamp': 1494275280,
            'upload_date': '20170508',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        quality = qualities(
            ('ldflv', 'ld', 'sdflv', 'sd', 'hdflv', 'hd', 'src'))

        formats = [{
            'url': mobj.group('url'),
            'format_id': mobj.group('id'),
            'quality': quality(mobj.group('id')),
        } for mobj in re.finditer(
            r'(?P<id>[a-zA-Z]+)Url\s*=\s*(["\'])(?P<url>(?:https?:)?//.+?)\2',
            webpage)]
        if not formats:
            info = self._download_json(
                'https://www.pearvideo.com/videoStatus.jsp', video_id=video_id,
                query={'contId': video_id}, headers={'Referer': url})
            formats = [{
                'format_id': k,
                'url': v.replace(info['systemTime'], f'cont-{video_id}') if k == 'srcUrl' else v
            } for k, v in traverse_obj(info, ('videoInfo', 'videos'), default={}).items() if v]

        title = self._search_regex(
            (r'<h1[^>]+\bclass=(["\'])video-tt\1[^>]*>(?P<value>[^<]+)',
             r'<[^>]+\bdata-title=(["\'])(?P<value>(?:(?!\1).)+)\1'),
            webpage, 'title', group='value')
        description = self._search_regex(
            (r'<div[^>]+\bclass=(["\'])summary\1[^>]*>(?P<value>[^<]+)',
             r'<[^>]+\bdata-summary=(["\'])(?P<value>(?:(?!\1).)+)\1'),
            webpage, 'description', default=None,
            group='value') or self._html_search_meta('Description', webpage)
        timestamp = unified_timestamp(self._search_regex(
            r'<div[^>]+\bclass=["\']date["\'][^>]*>([^<]+)',
            webpage, 'timestamp', fatal=False))

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'timestamp': timestamp,
            'formats': formats,
        }
