import json
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    str_or_none,
    try_call,
    url_or_none,
)
from ..utils.traversal import find_element, traverse_obj


class ToutiaoIE(InfoExtractor):
    IE_NAME = 'toutiao'
    IE_DESC = '今日头条'

    _VALID_URL = r'https?://www\.toutiao\.com/video/(?P<id>\d+)/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://www.toutiao.com/video/7505382061495176511/',
        'info_dict': {
            'id': '7505382061495176511',
            'ext': 'mp4',
            'title': '新疆多地现不明飞行物，目击者称和月亮一样亮，几秒内突然加速消失，气象部门回应',
            'comment_count': int,
            'duration': 9.753,
            'like_count': int,
            'release_date': '20250517',
            'release_timestamp': 1747483344,
            'thumbnail': r're:https?://p\d+-sign\.toutiaoimg\.com/.+$',
            'uploader': '极目新闻',
            'uploader_id': 'MS4wLjABAAAAeateBb9Su8I3MJOZozmvyzWktmba5LMlliRDz1KffnM',
            'view_count': int,
        },
    }, {
        'url': 'https://www.toutiao.com/video/7479446610359878153/',
        'info_dict': {
            'id': '7479446610359878153',
            'ext': 'mp4',
            'title': '小伙竟然利用两块磁铁制作成磁力减震器，简直太有创意了！',
            'comment_count': int,
            'duration': 118.374,
            'like_count': int,
            'release_date': '20250308',
            'release_timestamp': 1741444368,
            'thumbnail': r're:https?://p\d+-sign\.toutiaoimg\.com/.+$',
            'uploader': '小莉创意发明',
            'uploader_id': 'MS4wLjABAAAA4f7d4mwtApALtHIiq-QM20dwXqe32NUz0DeWF7wbHKw',
            'view_count': int,
        },
    }]

    def _real_initialize(self):
        if self._get_cookies('https://www.toutiao.com').get('ttwid'):
            return

        urlh = self._request_webpage(
            'https://ttwid.bytedance.com/ttwid/union/register/', None,
            'Fetching ttwid', 'Unable to fetch ttwid', headers={
                'Content-Type': 'application/json',
            }, data=json.dumps({
                'aid': 24,
                'needFid': False,
                'region': 'cn',
                'service': 'www.toutiao.com',
                'union': True,
            }).encode(),
        )

        if ttwid := try_call(lambda: self._get_cookies(urlh.url)['ttwid'].value):
            self._set_cookie('.toutiao.com', 'ttwid', ttwid)
            return

        self.raise_login_required()

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        video_data = traverse_obj(webpage, (
            {find_element(tag='script', id='RENDER_DATA')},
            {urllib.parse.unquote}, {json.loads}, 'data', 'initialVideo',
        ))

        formats = []
        for video in traverse_obj(video_data, (
            'videoPlayInfo', 'video_list', lambda _, v: v['main_url'],
        )):
            formats.append({
                'url': video['main_url'],
                **traverse_obj(video, ('video_meta', {
                    'acodec': ('audio_profile', {str}),
                    'asr': ('audio_sample_rate', {int_or_none}),
                    'audio_channels': ('audio_channels', {float_or_none}, {int_or_none}),
                    'ext': ('vtype', {str}),
                    'filesize': ('size', {int_or_none}),
                    'format_id': ('definition', {str}),
                    'fps': ('fps', {int_or_none}),
                    'height': ('vheight', {int_or_none}),
                    'tbr': ('real_bitrate', {float_or_none(scale=1000)}),
                    'vcodec': ('codec_type', {str}),
                    'width': ('vwidth', {int_or_none}),
                })),
            })

        return {
            'id': video_id,
            'formats': formats,
            **traverse_obj(video_data, {
                'comment_count': ('commentCount', {int_or_none}),
                'duration': ('videoPlayInfo', 'video_duration', {float_or_none}),
                'like_count': ('repinCount', {int_or_none}),
                'release_timestamp': ('publishTime', {int_or_none}),
                'thumbnail': (('poster', 'coverUrl'), {url_or_none}, any),
                'title': ('title', {str}),
                'uploader': ('userInfo', 'name', {str}),
                'uploader_id': ('userInfo', 'userId', {str_or_none}),
                'view_count': ('playCount', {int_or_none}),
                'webpage_url': ('detailUrl', {url_or_none}),
            }),
        }
