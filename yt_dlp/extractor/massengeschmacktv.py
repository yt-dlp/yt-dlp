import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    determine_ext,
    int_or_none,
    js_to_json,
    mimetype2ext,
    parse_filesize,
)


class MassengeschmackTVIE(InfoExtractor):
    IE_NAME = 'massengeschmack.tv'
    _VALID_URL = r'https?://(?:www\.)?massengeschmack\.tv/play/(?P<id>[^?&#]+)'

    _TEST = {
        'url': 'https://massengeschmack.tv/play/fktv202',
        'md5': 'a9e054db9c2b5a08f0a0527cc201e8d3',
        'info_dict': {
            'id': 'fktv202',
            'ext': 'mp4',
            'title': 'Fernsehkritik-TV - Folge 202',
        },
    }

    def _real_extract(self, url):
        episode = self._match_id(url)

        webpage = self._download_webpage(url, episode)
        title = clean_html(self._html_search_regex(
            '<h3>([^<]+)</h3>', webpage, 'title'))
        thumbnail = self._search_regex(r'POSTER\s*=\s*"([^"]+)', webpage, 'thumbnail', fatal=False)
        sources = self._parse_json(self._search_regex(r'(?s)MEDIA\s*=\s*(\[.+?\]);', webpage, 'media'), episode, js_to_json)

        formats = []
        for source in sources:
            furl = source.get('src')
            if not furl:
                continue
            furl = self._proto_relative_url(furl)
            ext = determine_ext(furl) or mimetype2ext(source.get('type'))
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    furl, episode, 'mp4', 'm3u8_native',
                    m3u8_id='hls', fatal=False))
            else:
                formats.append({
                    'url': furl,
                    'format_id': determine_ext(furl),
                })

        for (durl, format_id, width, height, filesize) in re.findall(r'''(?x)
                                   <a[^>]+?href="(?P<url>(?:https:)?//[^"]+)".*?
                                   <strong>(?P<format_id>.+?)</strong>.*?
                                   <small>(?:(?P<width>\d+)x(?P<height>\d+))?\s+?\((?P<filesize>[\d,]+\s*[GM]iB)\)</small>
                                ''', webpage):
            formats.append({
                'url': durl,
                'format_id': format_id,
                'width': int_or_none(width),
                'height': int_or_none(height),
                'filesize': parse_filesize(filesize),
                'vcodec': 'none' if format_id.startswith('Audio') else None,
            })

        self._sort_formats(formats)

        return {
            'id': episode,
            'title': title,
            'formats': formats,
            'thumbnail': thumbnail,
        }
