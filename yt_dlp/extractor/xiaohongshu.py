
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
        'url': 'https://www.xiaohongshu.com/explore/640daef50000000012030b49?xsec_token=ABbVz3VBPWhHKGGuKIS5xQNS8vHjAZiY_T_ge6k9UVcFA=',
        'md5': 'a497217683a6f7b0d29f50e83a19704e',
        'info_dict': {
            'id': '640daef50000000012030b49',
            'ext': 'mp4',
            'uploader_id': '5dd7634d0000000001002c23',
            'description': '今年一直从这棵古玉兰花开看到花落\n花开惊艳，花落的谢幕也是异常华美\n500年的风雨仍旧温柔伫立\n如此这般见证了无数历史～\n一岁为期，一期一会的惊艳\n被时间的洪流裹挟的渺小的我\n能会一期是一期\n#笔记灵感[话题]#\xa0\xa0#周末去哪儿[话题]#\xa0\xa0#浪漫生活的记录者[话题]#\xa0\xa0#法喜寺[话题]#\xa0\xa0#杭州拍照[话题]#',
            'title': '杭州法喜寺500年古玉兰惊艳落幕！来年再会',
            'tags': ['笔记灵感', '周末去哪儿', '浪漫生活的记录者', '法喜寺', '杭州拍照'],
            'duration': 29.634,
            'thumbnail': r're:https?://sns-webpic-qc\.xhscdn\.com/\d+/[a-z0-9]+/[\w]+',
        },
    }, {
        'url': 'https://www.xiaohongshu.com/discovery/item/69e8c63c000000001b0206c5?xsec_token=CBCxFsFsXrsXy3MFxZWUlVsLBXGS6Hs615dlbcjYG8h4g=',
        'md5': '2d0165e34fad77647035f987de5a8843',
        'info_dict': {
            'id': '69e8c63c000000001b0206c5',
            'ext': 'mp4',
            'title': '“真正的世界 不在书和地图里 它在外面”',
            'uploader_id': '68899eae000000002802a64d',
            'duration': 23.067,
            'description': '#旅行大玩家[话题]# #旅行推荐官[话题]# #治愈系风景[话题]# #世界这本书又看了几页[话题]# #世界这本书我又多读了一页[话题]#',
            'thumbnail': r're:https?://sns-webpic-qc\.xhscdn\.com/\d+/[\da-f]+/[^/]+',
            'tags': ['旅行大玩家', '旅行推荐官', '治愈系风景', '世界这本书又看了几页', '世界这本书我又多读了一页'],
        },
    }, {
        'url': 'http://xhslink.com/o/8wvDcEylIRP',
        'md5': '7f57fe126a9baa58aad65f01cdae8af8',
        'info_dict': {
            'id': '6a9e234f00000000250363b5',
            'ext': 'mp4',
            'title': '迷你乡村火车轨道建造',
            'uploader_id': '6a9d59fa0000000013003805',
            'duration': 59.367,
            'description': '',
            'thumbnail': r're:https?://sns-webpic-qc\.xhscdn\.com/\d+/[\da-f]+/[^/]+',
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
