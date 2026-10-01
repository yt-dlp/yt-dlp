
from .common import InfoExtractor
from ..utils import (
    UnsupportedError,
    float_or_none,
    int_or_none,
    js_to_json,
    url_or_none,
    urlhandle_detect_ext,
)
from ..utils.traversal import traverse_obj


class XiaoHongShuIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.xiaohongshu\.com/(?:explore|discovery/item)|xhslink\.com/o)/(?P<id>[\da-zA-Z]+)'
    IE_DESC = '小红书'
    _TESTS = [{
        'url': 'https://www.xiaohongshu.com/explore/6411cf99000000001300b6d9',
        'md5': '2a87a77ddbedcaeeda8d7eae61b61228',
        'info_dict': {
            'id': '6411cf99000000001300b6d9',
            'ext': 'mp4',
            'uploader_id': '5c31698d0000000007018a31',
            'description': '#今日快乐今日发[话题]# #吃货薯看这里[话题]# #香妃蛋糕[话题]# #小五卷蛋糕[话题]# #新手蛋糕卷[话题]#',
            'title': '香妃蛋糕也太香了吧🔥不需要卷❗️绝对的友好',
            'tags': ['今日快乐今日发', '吃货薯看这里', '香妃蛋糕', '小五卷蛋糕', '新手蛋糕卷'],
            'duration': 101.726,
            'thumbnail': r're:https?://sns-webpic-qc\.xhscdn\.com/\d+/[a-z0-9]+/[\w]+',
        },
    }, {
        'url': 'https://www.xiaohongshu.com/discovery/item/674051740000000007027a15?xsec_token=CBgeL8Dxd1ZWBhwqRd568gAZ_iwG-9JIf9tnApNmteU2E=',
        'info_dict': {
            'id': '674051740000000007027a15',
            'ext': 'mp4',
            'title': '相互喜欢就可以了',
            'uploader_id': '63439913000000001901f49a',
            'duration': 28.073,
            'description': '#广州[话题]# #深圳[话题]# #香港[话题]# #街头采访[话题]# #是你喜欢的类型[话题]#',
            'thumbnail': r're:https?://sns-webpic-qc\.xhscdn\.com/\d+/[\da-f]+/[^/]+',
            'tags': ['广州', '深圳', '香港', '街头采访', '是你喜欢的类型'],
        },
    }]

    def _real_extract(self, url):
        webpage, urlh = self._download_webpage_handle(url, self._match_id(url))
        if not self.suitable(urlh.url):
            raise UnsupportedError(urlh.url)

        display_id = self._match_id(urlh.url)
        initial_state = self._search_json(
            r'window\.__INITIAL_STATE__\s*=', webpage, 'initial state', display_id, transform_source=js_to_json)

        note_info = traverse_obj(initial_state, ('note', 'noteDetailMap', display_id, 'note'))
        video_info = traverse_obj(note_info, ('video', 'media', 'stream', ..., ...))

        formats = []
        for info in video_info:
            format_info = traverse_obj(info, {
                'fps': ('fps', {int_or_none}),
                'width': ('width', {int_or_none}),
                'height': ('height', {int_or_none}),
                'vcodec': ('videoCodec', {str}),
                'acodec': ('audioCodec', {str}),
                'abr': ('audioBitrate', {int_or_none(scale=1000)}),
                'vbr': ('videoBitrate', {int_or_none(scale=1000)}),
                'audio_channels': ('audioChannels', {int_or_none}),
                'tbr': ('avgBitrate', {int_or_none(scale=1000)}),
                'format': ('qualityType', {str}),
                'filesize': ('size', {int_or_none}),
                'duration': ('duration', {float_or_none(scale=1000)}),
            })

            formats.extend(traverse_obj(info, (('masterUrl', ('backupUrls', ...)), {
                lambda u: url_or_none(u) and {'url': u, **format_info}})))

        if origin_key := traverse_obj(note_info, ('video', 'consumer', 'originVideoKey', {str})):
            # Not using a head request because of false negatives
            urlh = self._request_webpage(
                f'https://sns-video-bd.xhscdn.com/{origin_key}', display_id,
                'Checking original video availability', 'Original video is not available', fatal=False)
            if urlh:
                formats.append({
                    'format_id': 'direct',
                    'ext': urlhandle_detect_ext(urlh, default='mp4'),
                    'filesize': int_or_none(urlh.get_header('Content-Length')),
                    'url': urlh.url,
                    'quality': 1,
                })

        thumbnails = []
        for image_info in traverse_obj(note_info, ('imageList', ...)):
            thumbnail_info = traverse_obj(image_info, {
                'height': ('height', {int_or_none}),
                'width': ('width', {int_or_none}),
            })
            for thumb_url in traverse_obj(image_info, (('urlDefault', 'urlPre'), {url_or_none})):
                thumbnails.append({
                    'url': thumb_url,
                    **thumbnail_info,
                })

        return {
            'id': display_id,
            'formats': formats,
            'thumbnails': thumbnails,
            'title': self._html_search_meta(['og:title'], webpage, default=None),
            **traverse_obj(note_info, {
                'title': ('title', {str}),
                'description': ('desc', {str}),
                'tags': ('tagList', ..., 'name', {str}),
                'uploader_id': ('user', 'userId', {str}),
            }),
        }
