from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    int_or_none,
    unified_timestamp,
)


class PopcornTVIE(InfoExtractor):
    _VALID_URL = r'https?://[^/]+\.popcorntv\.it/guarda/(?P<display_id>[^/]+)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://animemanga.popcorntv.it/guarda/food-wars-battaglie-culinarie-episodio-01/9183',
        'md5': '47d65a48d147caf692ab8562fe630b45',
        'info_dict': {
            'id': '9183',
            'display_id': 'food-wars-battaglie-culinarie-episodio-01',
            'ext': 'mp4',
            'title': 'Food Wars, Battaglie Culinarie | Episodio 01',
            'description': 'md5:b8bea378faae4651d3b34c6e112463d0',
            'thumbnail': r're:^https?://.*\.jpg$',
            'timestamp': 1497610857,
            'upload_date': '20170616',
            'duration': 1440,
            'view_count': int,
        },
    }, {
        'url': 'https://cinema.popcorntv.it/guarda/smash-cut/10433',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id, video_id = mobj.group('display_id', 'id')

        webpage = self._download_webpage(url, display_id)

        m3u8_url = extract_attributes(
            self._search_regex(
                r'(<link[^>]+itemprop=["\'](?:content|embed)Url[^>]*>)',
                webpage, 'content'
            ))['href']

        formats = self._extract_m3u8_formats(
            m3u8_url, display_id, 'mp4', entry_protocol='m3u8_native',
            m3u8_id='hls')

        title = self._search_regex(
            r'<h1[^>]+itemprop=["\']name[^>]*>([^<]+)', webpage,
            'title', default=None) or self._og_search_title(webpage)

        description = self._html_search_regex(
            r'(?s)<article[^>]+itemprop=["\']description[^>]*>(.+?)</article>',
            webpage, 'description', fatal=False)
        thumbnail = self._og_search_thumbnail(webpage)
        timestamp = unified_timestamp(self._html_search_meta(
            'uploadDate', webpage, 'timestamp'))
        duration = int_or_none(self._html_search_meta(
            'duration', webpage), invscale=60)
        view_count = int_or_none(self._html_search_meta(
            'interactionCount', webpage, 'view count'))

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
            'duration': duration,
            'view_count': view_count,
            'formats': formats,
        }
