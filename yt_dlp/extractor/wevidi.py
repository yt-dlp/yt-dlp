from .common import InfoExtractor
from ..utils import clean_html, float_or_none, get_element_by_class, js_to_json, traverse_obj


class WeVidiIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?wevidi\.net/watch/(?P<id>[\w-]{11})'
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
        },
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
        },
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
        },
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
        },
    }, {
        'url': 'https://wevidi.net/watch/4m1c4yJR_yc',
        'md5': 'c63ce5ca6990dce86855fc02ca5bc1ed',
        'info_dict': {
            'id': '4m1c4yJR_yc',
            'ext': 'mp4',
            'title': 'Enough of that! - Awesome Exilez Podcast',
            'thumbnail': r're:^https?://.*\.jpg$',
            'description': 'md5:96af99dd63468b2dfab3020560e3e9b2',
            'uploader': 'eclecRC',
            'duration': 6.804,
        },
    }]

    def _extract_formats(self, wvplayer_props):
        # Taken from WeVidi player JS: https://wevidi.net/layouts/default/static/player.min.js
        resolution_map = {
            1: 144,
            2: 240,
            3: 360,
            4: 480,
            5: 720,
            6: 1080,
        }

        src_path = f'{wvplayer_props["srcVID"]}/{wvplayer_props["srcUID"]}/{wvplayer_props["srcNAME"]}'
        for res in traverse_obj(wvplayer_props, ('resolutions', ..., {int}, {lambda x: x or None})):
            format_id = str(-(res // -2) - 1)
            yield {
                'acodec': 'mp4a.40.2',
                'ext': 'mp4',
                'format_id': format_id,
                'height': resolution_map.get(res),
                'url': f'https://www.wevidi.net/videoplayback/{src_path}/{format_id}',
                'vcodec': 'avc1.42E01E',
            }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        wvplayer_props = self._search_json(
            r'WVPlayer\(', webpage, 'player', video_id,
            transform_source=lambda x: js_to_json(x.replace('||', '}')))

        return {
            'id': video_id,
            'title': clean_html(get_element_by_class('video_title', webpage)),
            'description': clean_html(get_element_by_class('descr_long', webpage)),
            'uploader': clean_html(get_element_by_class('username', webpage)),
            'formats': list(self._extract_formats(wvplayer_props)),
            'thumbnail': self._og_search_thumbnail(webpage),
            'duration': float_or_none(wvplayer_props.get('duration')),
        }
