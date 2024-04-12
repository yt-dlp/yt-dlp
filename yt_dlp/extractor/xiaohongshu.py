from .common import InfoExtractor
from ..utils import (
    float_or_none,
    js_to_json,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class XiaoHongShuIE(InfoExtractor):
    _VALID_URL = r'https?://www\.xiaohongshu.com/explore/(?P<id>[a-f0-9]+)'
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
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        initial_state = self._search_json(
            r'window\.__INITIAL_STATE__\s*=', webpage, 'initial state', display_id, transform_source=js_to_json)

        note_info = traverse_obj(initial_state, ('note', 'noteDetailMap', display_id, 'note'))
        video_info = traverse_obj(note_info, ('video', 'media', 'stream', ('h264', 'av1', 'h265'), ...))

        formats = []
        for info in video_info:
            format_info = traverse_obj(info, {
                'fps': 'fps',
                'width': 'width',
                'height': 'height',
                'vcodec': 'videoCodec',
                'acodec': 'audioCodec',
                'abr': 'audioBitrate',
                'vbr': 'videoBitrate',
                'audio_channels': 'audioChannels',
                'tbr': 'avgBitrate',
                'format': 'qualityType',
                'filesize': 'size',
                'duration': ('duration', {lambda x: float_or_none(x, scale=1000)})
            })

            formats.extend(traverse_obj(info, (('mediaUrl', ('backupUrls', ...)), {
                lambda url: url_or_none(url) and {'url': url, 'ext': 'mp4', **format_info}})))

        thumbnails = []
        for image_info in traverse_obj(note_info, ('imageList', ...)):
            thumbnail_info = traverse_obj(image_info, {
                'height': 'height',
                'width': 'width'
            })
            for url in traverse_obj(image_info, (('urlDefault', 'urlPre'), {url_or_none})):
                thumbnails.append({
                    'url': url,
                    **thumbnail_info
                })

        return {
            'id': display_id,
            'formats': formats or [{
                'url': self._html_search_meta(['og:video'], webpage, fatal=True),
                'ext': 'mp4'
            }],
            'thumbnails': thumbnails or [{
                'url': self._html_search_meta(['og:image'], webpage, default=None)
            }],
            'title': self._html_search_meta(['og:title'], webpage, default=None),
            **traverse_obj(note_info, {
                'title': 'title',
                'description': 'desc',
                'tags': ('tagList', ..., 'name', {str}),
                'uploader_id': ('user', 'userId'),
            }),
        }
