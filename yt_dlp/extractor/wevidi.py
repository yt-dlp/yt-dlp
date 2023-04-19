import json
import re
from .common import InfoExtractor
from ..utils import clean_html, float_or_none, get_element_by_class, js_to_json


class WeVidiIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?wevidi\.net/watch/(?P<id>[0-9A-Za-z_-]{11})'
    _TESTS = [{
        'url': 'https://wevidi.net/watch/2th7UO5F4KV',
        'md5': 'b913d1ff5bbad499e2c7ef4aa6d829d7',
        'info_dict': {
            'id': '2th7UO5F4KV',
            'ext': 'mp4',
            'title': 'YouTube Alternative: WeVidi - customizable channels & more',
            'thumbnail': r're:^https?://.*\.jpg$',
            'description': 'md5:73a27d0a87d49fbcc5584566326ebeed',
            'uploader': 'eclecRC',
            'duration': 932.098,
        }
    }, {
        'url': 'https://wevidi.net/watch/ievRuuQHbPS',
        'md5': 'ce8a94989a959bff9003fa27ee572935',
        'info_dict': {
            'id': 'ievRuuQHbPS',
            'ext': 'mp4',
            'title': 'WeVidi Playlists',
            'thumbnail': r're:^https?://.*\.jpg$',
            'description': 'md5:32cdfca272687390d9bd9b0c9c6153ee',
            'uploader': 'WeVidi',
            'duration': 36.1999,
        }
    }, {
        'url': 'https://wevidi.net/watch/PcMzDWaQSWb',
        'md5': '55ee0d3434be5d9e5cc76b83f2bb57ec',
        'info_dict': {
            'id': 'PcMzDWaQSWb',
            'ext': 'mp4',
            'title': 'Cat blep',
            'thumbnail': r're:^https?://.*\.jpg$',
            'description': 'md5:e2c9e2b54b8bb424cc64937c8fdc068f',
            'uploader': 'WeVidi',
            'duration': 41.972,
        }
    }, {
        'url': 'https://wevidi.net/watch/wJnRqDHNe_u',
        'md5': 'c8f263dd47e66cc17546b3abf47b5a77',
        'info_dict': {
            'id': 'wJnRqDHNe_u',
            'ext': 'mp4',
            'title': 'Gissy Talks: YouTube Alternatives',
            'thumbnail': r're:^https?://.*\.jpg$',
            'description': 'md5:e65036f0d4af80e0af191bd11af5195e',
            'uploader': 'GissyEva',
            'duration': 630.451,
        }
    }]

    def _extract_formats(self, wvplayer_props):
        # Taken from WeVidi player JS: https://wevidi.net/layouts/default/static/player.min.js
        resolution_map = {
            1: '144p',
            2: '240p',
            3: '360p',
            4: '480p',
            5: '720p',
            6: '1080p'
        }

        srcUID = wvplayer_props.get('srcUID')
        srcVID = wvplayer_props.get('srcVID')
        srcNAME = wvplayer_props.get('srcNAME')
        resolutions = [res for res in wvplayer_props.get('resolutions') if res > 0]
        formats = []
        for res in resolutions:
            format_id = str(-(res // -2) - 1)
            formats.append({
                'acodec': 'mp4a.40.2',
                'ext': 'mp4',
                'format_id': format_id,
                'resolution': resolution_map.get(res),
                'url': f'https://www.wevidi.net/videoplayback/{srcVID}/{srcUID}/{srcNAME}/{format_id}',
                'vcodec': 'avc1.42E01E',
            })

        return formats

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = get_element_by_class('video_title', webpage)
        wvplayer_props = json.loads(js_to_json(self._search_regex(
            r'WVPlayer\(({.+?)autoplay', webpage,
            'wvplayer_props', flags=re.DOTALL) + '}'))

        return {
            'id': video_id,
            'title': title,
            'description': clean_html(get_element_by_class('descr_long', webpage)),
            'uploader': get_element_by_class('username', webpage),
            'formats': self._extract_formats(wvplayer_props),
            'thumbnail': self._og_search_thumbnail(webpage),
            'duration': float_or_none(wvplayer_props.get('duration')),
        }
