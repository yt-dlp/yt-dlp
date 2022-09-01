import re

from .common import InfoExtractor
from ..utils import ExtractorError


class NewsPicksIE(InfoExtractor):
    _VALID_URL = r'https://newspicks\.com/movie-series/(?P<channel_id>\d+)\?movieId=(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://newspicks.com/movie-series/11?movieId=1813',
        'info_dict': {
            'id': '1813',
            'title': '日本の課題を破壊せよ【ゲスト：成田悠輔】',
            'description': 'md5:09397aad46d6ded6487ff13f138acadf',
            'channel': 'HORIE ONE',
            'channel_id': '11',
            'release_date': '20220117',
            'thumbnail': r're:https://.+jpg',
            'ext': 'mp4',
        },
    }]

    def _real_extract(self, url):
        video_id, channel_id = self._match_valid_url(url).group('id', 'channel_id')
        webpage = self._download_webpage(url, video_id)
        entries = self._parse_html5_media_entries(
            url, webpage.replace('movie-for-pc', 'movie'), video_id, 'hls')
        if not entries:
            raise ExtractorError('No HTML5 media elements found')
        info = entries[0]
        self._sort_formats(info['formats'])

        title = self._html_search_meta('og:title', webpage, fatal=False)
        description = self._html_search_meta(
            ('og:description', 'twitter:title'), webpage, fatal=False)
        channel = self._html_search_regex(
            r'value="11".+?<div\s+class="title">(.+?)</div', webpage, 'channel name', fatal=False)
        if not title or not channel:
            title, channel = re.split(r'\s*|\s*', self._html_extract_title(webpage))

        release_date = self._search_regex(
            r'<span\s+class="on-air-date">\s*(\d+)年(\d+)月(\d+)日\s*</span>',
            webpage, 'release date', fatal=False, group=(1, 2, 3))

        info.update({
            'id': video_id,
            'title': title,
            'description': description,
            'channel': channel,
            'channel_id': channel_id,
            'release_date': ('%04d%02d%02d' % tuple(map(int, release_date))) if release_date else None,
        })
        return info
