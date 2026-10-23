from .common import InfoExtractor
from ..utils import int_or_none, str_or_none, url_or_none
from ..utils.traversal import traverse_obj


class AlibabaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?alibaba\.com/product-detail/[\w-]+_(?P<id>\d+)\.html'
    _TESTS = [{
        'url': 'https://www.alibaba.com/product-detail/Kids-Entertainment-Bouncer-Bouncy-Castle-Waterslide_1601271126969.html',
        'info_dict': {
            'id': '6000280444270',
            'display_id': '1601271126969',
            'ext': 'mp4',
            'title': 'Kids Entertainment Bouncer Bouncy Castle Waterslide Juex Gonflables Commercial Inflatable Tropical Water Slide',
            'duration': 30,
            'thumbnail': 'https://sc04.alicdn.com/kf/Hc5bb391974454af18c7a4f91cbe4062bg.jpg_120x120.jpg',
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        product_data = self._search_json(
            r'window\.detailData\s*=', webpage, 'detail data', display_id)['globalData']['product']

        return {
            **traverse_obj(product_data, ('mediaItems', lambda _, v: v['type'] == 'video' and v['videoId'], any, {
                'id': ('videoId', {int}, {str_or_none}),
                'duration': ('duration', {int_or_none}),
                'thumbnail': ('videoCoverUrl', {url_or_none}),
                'formats': ('videoUrl', lambda _, v: url_or_none(v['videoUrl']), {
                    'url': 'videoUrl',
                    'format_id': ('definition', {str_or_none}),
                    'tbr': ('bitrate', {int_or_none}),
                    'width': ('width', {int_or_none}),
                    'height': ('height', {int_or_none}),
                    'filesize': ('length', {int_or_none}),
                }),
            })),
            'title': traverse_obj(product_data, ('subject', {str})),
            'display_id': display_id,
        }
