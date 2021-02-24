# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import compat_parse_qs
from ..utils import (
    int_or_none,
    parse_duration,
    parse_iso8601,
    xpath_text,
)


class FolketingetIE(InfoExtractor):
    IE_DESC = 'Folketinget (ft.dk; Danish parliament)'
    _VALID_URL = r'https?://(?:www\.)?ft\.dk/webtv/video/[^?#]*?\.(?P<id>[0-9]+)\.aspx'
    _TEST = {
        'url': 'http://www.ft.dk/webtv/video/20141/eru/td.1165642.aspx?as=1#player',
        'md5': '6269e8626fa1a891bf5369b386ae996a',
        'info_dict': {
            'id': '1165642',
            'ext': 'mp4',
            'title': 'Åbent samråd i Erhvervsudvalget',
            'description': 'Åbent samråd med erhvervs- og vækstministeren om regeringens politik på teleområdet',
            'view_count': int,
            'width': 768,
            'height': 432,
            'tbr': 928000,
            'timestamp': 1416493800,
            'upload_date': '20141120',
            'duration': 3960,
        },
        'params': {
            # rtmp download
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._og_search_title(webpage)
        description = self._html_search_regex(
            r'(?s)<div class="video-item-agenda"[^>]*>(.*?)<',
            webpage, 'description', fatal=False)

        player_params = compat_parse_qs(self._search_regex(
            r'<embed src="http://ft\.arkena\.tv/flash/ftplayer\.swf\?([^"]+)"',
            webpage, 'player params'))
        xml_url = player_params['xml'][0]
        doc = self._download_xml(xml_url, video_id)

        timestamp = parse_iso8601(xpath_text(doc, './/date'))
        duration = parse_duration(xpath_text(doc, './/duration'))
        width = int_or_none(xpath_text(doc, './/width'))
        height = int_or_none(xpath_text(doc, './/height'))
        view_count = int_or_none(xpath_text(doc, './/views'))

        formats = [{
            'format_id': n.attrib['bitrate'],
            'url': xpath_text(n, './url', fatal=True),
            'tbr': int_or_none(n.attrib['bitrate']),
        } for n in doc.findall('.//streams/stream')]
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'description': description,
            'timestamp': timestamp,
            'width': width,
            'height': height,
            'duration': duration,
            'view_count': view_count,
        }
