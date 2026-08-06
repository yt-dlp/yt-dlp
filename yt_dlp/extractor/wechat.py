import json
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    traverse_obj,
)


class WeChatIE(InfoExtractor):
    _VALID_URL = r'https?://weixin\.qq\.com/sph/(?P<id>[0-9A-Za-z]+)'
    _TESTS = [
        {
            'url': 'https://weixin.qq.com/sph/Axv548mzBF',
            'md5': '0245ac3501e8bfe6b9b8a0c057eb4cbd',
            'info_dict': {
                'id': 'Axv548mzBF',
                'ext': 'mp4',
                'title': "𓆩⁺₊⋆𝔸𝕟𝕘𝕖𝕝'𝕤 𝕎𝕒𝕟𝕕𝕖𝕣𝕚𝕟𝕘 𝕊𝕠𝕦𝕝 ⋆⁺₊ 𓆪#天使之翼 #堕天使 #变装",
                'description': "𓆩⁺₊⋆𝔸𝕟𝕘𝕖𝕝'𝕤 𝕎𝕒𝕟𝕕𝕖𝕣𝕚𝕟𝕘 𝕊𝕠𝕦𝕝 ⋆⁺₊ 𓆪#天使之翼 #堕天使 #变装",
                'uploader': '小报纸',
                'uploader_id': '小报纸',
                'timestamp': 1779545781,
                'upload_date': '20260523',
                'comment_count': int,
                'like_count': int,
                'repost_count': int,
                'thumbnail': r're:^https?://.*',
            },
        },
        {
            'url': 'https://weixin.qq.com/sph/AoSzkdlyu1',
            'md5': '6e29ad0c58026ca2c1589b3fa5808246',
            'info_dict': {
                'id': 'AoSzkdlyu1',
                'ext': 'mp4',
                'title': '天秤座本来没有心 有的就是那杆需要被捂热的秤子#天秤#天秤座#天秤女#天秤男',
                'description': '天秤座本来没有心 有的就是那杆需要被捂热的秤子#天秤#天秤座#天秤女#天秤男',
                'uploader': '花澈麟',
                'uploader_id': '花澈麟',
                'timestamp': 1785499453,
                'upload_date': '20260731',
                'comment_count': int,
                'like_count': int,
                'repost_count': int,
                'thumbnail': r're:^https?://.*',
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        yuanbao_payload = {
            'type': 'video_channel_url',
            'url': url,
            'scene': 1,
        }
        yuanbao_res = self._download_json(
            'https://yuanbao.tencent.com/api/weixin/get_parse_result',
            video_id,
            data=json.dumps(yuanbao_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            note='Extracting video information',
            fatal=False,
        )

        playable_url = traverse_obj(yuanbao_res, ('data', 'playable_url'))
        if not playable_url:
            raise ExtractorError('Video not playable or not found', expected=True)

        parsed_url = urllib.parse.urlparse(playable_url)
        qs = urllib.parse.parse_qs(parsed_url.query)
        token = qs.get('token', [None])[0]
        eid = qs.get('eid', [None])[0]
        if not token or not eid:
            raise ExtractorError('Could not extract token or eid')

        payload = {
            'baseReq': {
                'generalToken': urllib.parse.unquote(token),
            },
            'exportId': urllib.parse.unquote(eid),
        }

        feed_data = self._download_json(
            'https://channels.weixin.qq.com/finder-preview/api/feed/get_feed_info',
            video_id,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Origin': 'https://channels.weixin.qq.com',
                'Referer': f'https://channels.weixin.qq.com/finder-preview/pages/feed?entry_card_type=48&comment_scene=39&appid=0&token={token}&entry_scene=0&eid={eid}',
            },
            note='Downloading metadata',
        )

        if traverse_obj(feed_data, ('errCode')) != 0:
            raise ExtractorError(f"API returned error: {feed_data.get('errMsg')}", expected=True)
        if traverse_obj(feed_data, ('data', 'errMsg', 'type')) != 0:
            raise ExtractorError(
                f"API returned error: {traverse_obj(feed_data, ('data', 'errMsg', 'title'))}", expected=True,
            )

        feed_info = traverse_obj(feed_data, ('data', 'feedInfo')) or {}
        author_info = traverse_obj(feed_data, ('data', 'authorInfo')) or {}
        title = feed_info.get('description')

        formats = []
        for codec, key in [('h264', 'h264VideoInfo'), ('h265', 'h265VideoInfo')]:
            v_url = traverse_obj(feed_info, (key, 'videoUrl'))
            if v_url:
                formats.append(
                    {
                        'url': v_url,
                        'format_id': codec,
                        'vcodec': codec,
                        'ext': 'mp4',
                    },
                )
        if not formats:
            self.raise_no_formats('No playable video formats found')

        return {
            'id': video_id,
            'title': title,
            'description': feed_info.get('description'),
            'uploader': author_info.get('nickname'),
            'uploader_id': author_info.get('nickname'),
            'timestamp': feed_info.get('createtime'),
            'thumbnail': feed_info.get('coverUrl'),
            'like_count': int_or_none(feed_info.get('likeCountFmt')),
            'repost_count': int_or_none(feed_info.get('forwardCountFmt')),
            'comment_count': int_or_none(feed_info.get('commentCountFmt')),
            'formats': formats,
        }
