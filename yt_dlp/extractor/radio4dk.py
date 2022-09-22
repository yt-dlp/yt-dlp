import re

from .common import InfoExtractor
from ..utils import (
    unescapeHTML,
    unified_strdate,
)


class Radio4DkIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?radio4\.dk/program/[^/]+/\?.*\bgid=(?P<id>\d+)\b'

    _TEST = {
        'url': 'https://www.radio4.dk/program/morgen-r4dio/?gid=37214&title=radio4-morgen-13-juni-kl-6-7',
        'md5': '6b1a0dcade1be0955117a8963987c6ef',
        'info_dict': {
            'id': '37214',
            'title': 'Radio4 Morgen - 13. juni kl. 6-7',
            'ext': 'mp3',
            'release_date': '20220613',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        url, title = self._search_regex(
            r'''href=([\"\'])(?P<media_url>(?:(?!\1).)+)\1.*data-gid=\"%s\".*data-title=\"(?P<title>[^\"]+)\"''' % video_id,
            webpage, 'media url', group=['media_url', 'title'])
        episode_date = self._search_regex(
            r'<div\s+class="date_title">.*<span\s+class="programDate\s+ep_date_js">([^<]+)</span>.*<span\s+class="gid".*>%s</span>' % video_id,
            webpage, 'episode date', fatal=False, flags=re.DOTALL)
        return {
            'url': url,
            'id': video_id,
            'title': unescapeHTML(title),
            'release_date': unified_strdate(episode_date)
        }
