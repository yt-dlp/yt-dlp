# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    str_to_int,
    unified_strdate,
)


class CloudyIE(InfoExtractor):
    _IE_DESC = 'cloudy.ec'
    _VALID_URL = r'https?://(?:www\.)?cloudy\.ec/(?:v/|embed\.php\?.*?\bid=)(?P<id>[A-Za-z0-9]+)'
    _TESTS = [{
        'url': 'https://www.cloudy.ec/v/af511e2527aac',
        'md5': '29832b05028ead1b58be86bf319397ca',
        'info_dict': {
            'id': 'af511e2527aac',
            'ext': 'mp4',
            'title': 'Funny Cats and Animals Compilation june 2013',
            'upload_date': '20130913',
            'view_count': int,
        }
    }, {
        'url': 'http://www.cloudy.ec/embed.php?autoplay=1&id=af511e2527aac',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            'https://www.cloudy.ec/embed.php', video_id, query={
                'id': video_id,
                'playerPage': 1,
                'autoplay': 1,
            })

        info = self._parse_html5_media_entries(url, webpage, video_id)[0]

        webpage = self._download_webpage(
            'https://www.cloudy.ec/v/%s' % video_id, video_id, fatal=False)

        if webpage:
            info.update({
                'title': self._search_regex(
                    r'<h\d[^>]*>([^<]+)<', webpage, 'title'),
                'upload_date': unified_strdate(self._search_regex(
                    r'>Published at (\d{4}-\d{1,2}-\d{1,2})', webpage,
                    'upload date', fatal=False)),
                'view_count': str_to_int(self._search_regex(
                    r'([\d,.]+) views<', webpage, 'view count', fatal=False)),
            })

        if not info.get('title'):
            info['title'] = video_id

        info['id'] = video_id

        return info
