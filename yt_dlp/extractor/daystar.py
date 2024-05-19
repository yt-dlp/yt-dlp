from .common import InfoExtractor
from ..utils import js_to_json, urljoin


class DaystarClipIE(InfoExtractor):
    IE_NAME = 'daystar:clip'
    _VALID_URL = r'https?://player\.daystar\.tv/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://player.daystar.tv/0MTO2ITM',
        'info_dict': {
            'id': '0MTO2ITM',
            'ext': 'mp4',
            'title': 'The Dark World of COVID Pt. 1 | Aaron Siri',
            'description': 'a420d320dda734e5f29458df3606c5f4',
            'thumbnail': r're:^https?://.+\.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        src_iframe = self._search_regex(r'\<iframe[^>]+src="([^"]+)"', webpage, 'src iframe')
        webpage_iframe = self._download_webpage(
            src_iframe.replace('player.php', 'config2.php'), video_id, headers={'Referer': src_iframe})

        sources = self._parse_json(self._search_regex(
            r'sources\:\s*(\[.*?\])', webpage_iframe, 'm3u8 source'), video_id, transform_source=js_to_json)

        formats, subtitles = [], {}
        for source in sources:
            file = source.get('file')
            if file and source.get('type') == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    urljoin('https://www.lightcast.com/embed/', file),
                    video_id, 'mp4', fatal=False, headers={'Referer': src_iframe})
                formats.extend(fmts)
                subtitles = self._merge_subtitles(subtitles, subs)

        return {
            'id': video_id,
            'title': self._html_search_meta(['og:title', 'twitter:title'], webpage),
            'description': self._html_search_meta(['og:description', 'twitter:description'], webpage),
            'thumbnail': self._search_regex(r'image:\s*"([^"]+)', webpage_iframe, 'thumbnail'),
            'formats': formats,
            'subtitles': subtitles,
        }
