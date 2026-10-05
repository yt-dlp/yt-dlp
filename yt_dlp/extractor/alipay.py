import re
import urllib.parse

from .common import InfoExtractor
from ..utils import ExtractorError, int_or_none, url_or_none
from ..utils.traversal import traverse_obj


class AlipayIE(InfoExtractor):
    IE_NAME = 'alipay'
    IE_DESC = '支付宝'
    _VALID_URL = [
        r'https?://ur\.lepudding\.com/(?P<short_id>[\w-]+)',
        r'https?://render\.alipay\.com/p/yuyan/\d+/video-share\.html\?(?:[^#]*&)?scheme=[^#&]+',
        r'https?://(?:www\.)?alipay\.com/video/(?P<id>\w+)',
    ]
    _TESTS = [{
        'url': 'https://ur.lepudding.com/_3Je3KhPExzQMlHZRvuBgcd',
        'info_dict': {
            'id': '20260913OB020010038324417829',
            'ext': 'mp4',
            'title': '当老登逼我拿下全班第一时',
            'duration': float,
            'thumbnail': r're:https?://.+',
            'timestamp': 1789305382,
            'upload_date': '20260913',
            'uploader': '小秋猫meme剧场',
            'uploader_id': '2030052960175833',
            'view_count': int,
            'like_count': int,
            'comment_count': int,
        },
    }]

    _API_URL = 'https://webgw-internet.alipay.com/contentservice/com.alipay.sofa.function.SOFAFunction/apply/myjf.yuyan.contentservice.default.ContentWebGWController.list'
    _CLARITIES = (
        ('1080P_h265_EH', 1080, 'h265', 3),
        ('1080P_h265', 1080, 'h265', 2),
        ('1080P_h264', 1080, 'h264', 1),
        ('720P_h265', 720, 'h265', 0),
        ('720P_h264', 720, 'h264', -1),
        ('540P_h264', 540, 'h264', -2),
    )

    @staticmethod
    def _find_content_id(text):
        for _ in range(3):
            if mobj := re.search(r'contentId=([A-Za-z0-9]+)', text):
                return mobj.group(1)
            text = urllib.parse.unquote(text)

    def _real_extract(self, url):
        video_id = self._match_valid_url(url).groupdict().get('id')
        if not video_id:
            urlh = self._request_webpage(url, 'share link', 'Resolving share link')
            video_id = self._find_content_id(urlh.url)
            if not video_id:
                raise ExtractorError('Unable to find the content ID in the share link')

        data = self._download_json(
            self._API_URL, video_id, data=b'{"contentId":"%s"}' % video_id.encode(),
            headers={
                'Content-Type': 'application/json',
                'x-webgw-appId': '180020010001266490',
                'x-webgw-version': '2.0',
            })
        if not data.get('success'):
            raise ExtractorError(
                f'Alipay said: {data.get("errorMessage") or "unknown error"}', expected=True)

        item = traverse_obj(data, ('resultObj', 'data', 0, {dict})) or {}
        video = traverse_obj(item, ('video', {dict})) or {}
        vid = url_or_none(video.get('vid'))
        if not vid or '?t=' not in vid:
            raise ExtractorError('No video stream found', expected=True)

        base, token = vid.split('?t=', 1)
        prefix = base.rpartition('/')[0]
        ratio = (traverse_obj(video, ('heightRatio', {int_or_none}))
                 or 1) / (traverse_obj(video, ('widthRatio', {int_or_none})) or 1)

        formats = [{
            'url': f'{prefix}/{clarity}?t={token}',
            'format_id': clarity,
            'ext': 'mp4',
            'width': width,
            'height': round(width * ratio),
            'vcodec': 'hevc' if codec == 'h265' else 'h264',
            'acodec': 'unknown',
            'quality': quality,
        } for clarity, width, codec, quality in self._CLARITIES]

        return {
            'id': video_id,
            'formats': formats,
            **traverse_obj(item, {
                'title': ('title', {str}),
                'description': ('content', {str}, filter),
                'timestamp': ('publishDate', {int_or_none(scale=1000)}),
                'uploader': ('author', 'nickName', {str}),
                'uploader_id': ('author', 'publicId', {str}),
                'view_count': ('pv', {int_or_none}),
                'like_count': ('praiseCount', {int_or_none}),
                'comment_count': ('replyCount', {int_or_none}),
                'thumbnail': ('coverPic', 'url', {url_or_none}),
            }),
            'duration': traverse_obj(video, ('duration', {float})),
        }
