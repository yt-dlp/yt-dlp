import json

from .common import InfoExtractor
from ..utils import js_to_json, try_get, urljoin


class DaystarClipIE(InfoExtractor):
    IE_NAME = 'daystar:clip'
    _VALID_URL = r'https?:\/\/player\.daystar\.tv\/(?P<id>\w+)($|\W)'
    _DOMAIN = 'https://www.lightcast.com/embed/'
    _TEST = {
        'url': 'https://player.daystar.tv/0MTO2ITM',
        'info_dict': {
            'id': '0MTO2ITM',
            'ext': 'm3u8',
            'title': 'The Dark World of COVID Pt. 1 | Aaron Siri',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id=video_id)

        title = self._html_search_meta(['og:title', 'twitter:title'], webpage, fatal=True)
        description = self._html_search_meta(['og:description', 'twitter:description'], webpage, fatal=True)

        src_iframe = self._search_regex(r'\<iframe.*?src=\"(.*?)\"', webpage, 'src iframe')

        config_url = src_iframe.replace('player.php', 'config2.php')

        webpage_iframe = self._download_webpage(config_url, video_id=video_id, headers={
            'Referer': src_iframe
        })

        sources = json.loads(js_to_json(self._search_regex(r'sources\:.*?(\[.*?\])', webpage_iframe, 'm3u8 source')))

        thumbnail = self._search_regex(r'image\:.*?\"(.*?)\"', webpage_iframe, 'thumbnail')

        formats = []

        for source in sources:
            if not source:
                continue
            file = try_get(source, lambda x: x['file'])
            type_source = try_get(source, lambda x: x['type'])
            url_m3u8 = urljoin(self._DOMAIN, file)

            if type_source == 'm3u8':
                formats.extend(self._extract_m3u8_formats(url_m3u8, video_id, 'mp4', fatal=False, headers={
                    'Referer': src_iframe}))
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': formats,
        }
