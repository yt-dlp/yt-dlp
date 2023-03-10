from .common import InfoExtractor
from ..utils import (
    js_to_json,
    mimetype2ext,
    determine_ext,
    update_url_query,
    get_element_by_attribute,
    int_or_none,
)


class NobelPrizeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?nobelprize\.org/mediaplayer.*?\bid=(?P<id>\d+)'
    _TEST = {
        'url': 'http://www.nobelprize.org/mediaplayer/?id=2636',
        'md5': '04c81e5714bb36cc4e2232fee1d8157f',
        'info_dict': {
            'id': '2636',
            'ext': 'mp4',
            'title': 'Announcement of the 2016 Nobel Prize in Physics',
            'description': 'md5:05beba57f4f5a4bbd4cf2ef28fcff739',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        media = self._parse_json(self._search_regex(
            r'(?s)var\s*config\s*=\s*({.+?});', webpage,
            'config'), video_id, js_to_json)['media']
        title = media['title']

        formats = []
        for source in media.get('source', []):
            source_src = source.get('src')
            if not source_src:
                continue
            ext = mimetype2ext(source.get('type')) or determine_ext(source_src)
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    source_src, video_id, 'mp4', 'm3u8_native',
                    m3u8_id='hls', fatal=False))
            elif ext == 'f4m':
                formats.extend(self._extract_f4m_formats(
                    update_url_query(source_src, {'hdcore': '3.7.0'}),
                    video_id, f4m_id='hds', fatal=False))
            else:
                formats.append({
                    'url': source_src,
                })

        return {
            'id': video_id,
            'title': title,
            'description': get_element_by_attribute('itemprop', 'description', webpage),
            'duration': int_or_none(media.get('duration')),
            'formats': formats,
        }
