from .common import InfoExtractor
from ..utils import js_to_json, urljoin


class DaystarClipIE(InfoExtractor):
    IE_NAME = 'daystar:clip'
    _VALID_URL = r'https?:\/\/player\.daystar\.tv\/(?P<id>\w+)($|\W)'
    _DOMAIN = 'https://www.lightcast.com/embed/'
    _TEST = {
        'url': 'https://player.daystar.tv/0MTO2ITM',
        'info_dict': {
            'id': '0MTO2ITM',
            'ext': 'mp4',
            'title': 'The Dark World of COVID Pt. 1 | Aaron Siri',
            'description': 'Is the fear of the pandemic being used to suppress and erode your constitutional '
                           'freedoms? Attorney Aaron Siri exposes the truth about what’s happening and how you can '
                           'join the fight to preserve your liberties. (J2167)',
            'thumbnail': r're:^https?://.+\.jpg',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id=video_id)

        title = self._html_search_meta(['og:title', 'twitter:title'], webpage, fatal=True)
        description = self._html_search_meta(['og:description', 'twitter:description'], webpage, fatal=True)

        src_iframe = self._search_regex(r'\<iframe.*?src=\"(.*?)\"', webpage, 'src iframe')

        webpage_iframe = self._download_webpage(src_iframe.replace('player.php', 'config2.php'), video_id=video_id,
                                                headers={'Referer': src_iframe})

        sources = self._parse_json(
            js_to_json(self._search_regex(r'sources\:.*?(\[.*?\])', webpage_iframe, 'm3u8 source')), video_id=video_id)

        thumbnail = self._search_regex(r'image\:.*?\"(.*?)\"', webpage_iframe, 'thumbnail')

        formats = []

        for source in sources:
            file = source.get('file')
            if source.get('type') == 'm3u8':
                formats.extend(self._extract_m3u8_formats(urljoin(self._DOMAIN, file), video_id, 'mp4', fatal=False,
                                                          headers={'Referer': src_iframe}))
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': formats,
        }
