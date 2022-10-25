from .common import InfoExtractor
import re


class ListenNotesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?listennotes\.com/podcasts/[^/]+/[^/]+-(?P<id>.+)/'
    _TESTS = [{
        'url': 'https://www.listennotes.com/podcasts/thriving-on-overload/tim-oreilly-on-noticing-KrDgvNb_u1n/',
        'md5': '5b91a32f841e5788fb82b72a1a8af7f7',
        'info_dict': {
            'id': 'KrDgvNb_u1n',
            'ext': 'mp3',
            'title': 'Tim O’Reilly on noticing things other people don’t notice, the value of soft focus, framing open source and Web 2.0, and patience in building narratives (Ep1)',
            'description': '00:35:48 - ‘’We shape reality by what we notice and choose to pa…'
        }
    }, {
        'url': 'https://www.listennotes.com/podcasts/ask-noah-show/episode-177-wireguard-with-lwEA3154JzG/',
        'md5': '62fb4ffe7fc525632a1138bf72a5ce53',
        'info_dict': {
            'id': 'lwEA3154JzG',
            'ext': 'mp3',
            'title': 'Episode 177: WireGuard with Jason Donenfeld - Ask Noah Show (podcast)',
            'description': '01:04:21 - Jason Donenfeld lead developer joins us this hour to discuss WireGuard, an extremely simple yet fast and modern VPN that utilizes state-of-the-art c…'
        }
    }]

    def _real_extract(self, url):
        audio_id = self._match_id(url)
        webpage = self._download_webpage(url, audio_id)
        title = self._html_search_regex(r'<h1\s*class=".+?">\s*<a\s*href=".+?"\s*title="(.+?)"\s*class=".+?">\s*.+\s*</a>\s*</h1>', webpage, 'title')
        json_data = self._search_json(
            r'<script id="original-content" type="application/json">\s*', webpage, 'content', audio_id)
        description = self._html_search_meta(
            ['og:description', 'description', 'twitter:description'], webpage, 'description', default=None)
        if description is not None:
            description = re.sub(r'\s{2,}', ' ', description)
        title = (self._html_search_meta(['og:title', 'title', 'twitter:title'], webpage, 'title', default=None)
                 or self._html_search_regex(
                     r'<h1\s*class=".+?">\s*<a\s*href=".+?"\s*title="(.+?)"\s*class=".+?">\s*.+\s*</a>\s*</h1>',
                     webpage, 'title'))

        return {
            'id': audio_id,
            'title': title,
            'description': description,
            'url': json_data['audio'],
        }
