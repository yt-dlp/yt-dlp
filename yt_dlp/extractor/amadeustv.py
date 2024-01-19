from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    parse_iso8601,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class AmadeusTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?amadeus\.tv/library/(?P<id>[\da-f]+)'
    _TESTS = [{
        'url': 'http://www.amadeus.tv/library/65091a87ff85af59d9fc54c3',
        'info_dict': {
            'id': '5576678021301411311',
            'ext': 'mp4',
            'title': 'Jieon Park - 第五届珠海莫扎特国际青少年音乐周小提琴C组第三轮',
            'thumbnail': 'http://1253584441.vod2.myqcloud.com/a0046a27vodtransbj1253584441/7db4af535576678021301411311/coverBySnapshot_10_0.jpg',
            'duration': 1264.8,
            'upload_date': '20230918',
            'timestamp': 1695034800,
            'display_id': '65091a87ff85af59d9fc54c3',
            'view_count': int,
            'description': 'md5:a0357b9c215489e2067cbae0b777bb95',
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        nuxt_data = self._search_nuxt_data(webpage, display_id, traverse=('fetch', '0'))
        video_id = traverse_obj(nuxt_data, ('item', 'video', {str}))

        if not video_id:
            raise ExtractorError('Unable to extract actual video ID')

        video_data = self._download_json(
            f'http://playvideo.qcloud.com/getplayinfo/v2/1253584441/{video_id}',
            video_id, headers={'Referer': 'http://www.amadeus.tv/'})

        formats = []
        for video in traverse_obj(video_data, ('videoInfo', ('sourceVideo', ('transcodeList', ...)), {dict})):
            if not url_or_none(video.get('url')):
                continue
            formats.append({
                **traverse_obj(video, {
                    'url': 'url',
                    'format_id': ('definition', {lambda x: f'http-{x or "0"}'}),
                    'width': ('width', {int_or_none}),
                    'height': ('height', {int_or_none}),
                    'filesize': (('totalSize', 'size'), {int_or_none}),
                    'vcodec': ('videoStreamList', 0, 'codec'),
                    'acodec': ('audioStreamList', 0, 'codec'),
                    'fps': ('videoStreamList', 0, 'fps', {float_or_none}),
                }, get_all=False),
                'http_headers': {'Referer': 'http://www.amadeus.tv/'},
            })

        return {
            'id': video_id,
            'display_id': display_id,
            'formats': formats,
            **traverse_obj(video_data, {
                'title': ('videoInfo', 'basicInfo', 'name', {str}),
                'thumbnail': ('coverInfo', 'coverUrl', {url_or_none}),
                'duration': ('videoInfo', 'sourceVideo', ('floatDuration', 'duration'), {float_or_none}),
            }, get_all=False),
            **traverse_obj(nuxt_data, ('item', {
                'title': (('title', 'title_en', 'title_cn'), {str}),
                'description': (('description', 'description_en', 'description_cn'), {str}),
                'timestamp': ('date', {parse_iso8601}),
                'view_count': ('view', {int_or_none}),
            }), get_all=False),
        }
