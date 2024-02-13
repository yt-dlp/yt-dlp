from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    int_or_none,
    str_or_none,
    strip_or_none,
    traverse_obj,
    unified_timestamp,
)


class KakaoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:play-)?tv\.kakao\.com/(?:channel/\d+|embed/player)/cliplink/(?P<id>\d+|[^?#&]+@my)'
    _API_BASE_TMPL = 'http://tv.kakao.com/api/v1/ft/playmeta/cliplink/%s/'
    _CDN_API = 'https://tv.kakao.com/katz/v1/ft/cliplink/%s/readyNplay?'

    _TESTS = [{
        'url': 'http://tv.kakao.com/channel/2671005/cliplink/301965083',
        'md5': '702b2fbdeb51ad82f5c904e8c0766340',
        'info_dict': {
            'id': '301965083',
            'ext': 'mp4',
            'title': '乃木坂46 バナナマン 「3期生紹介コーナーが始動！顔高低差GPも！」 『乃木坂工事中』',
            'description': '',
            'uploader_id': '2671005',
            'uploader': '그랑그랑이',
            'timestamp': 1488160199,
            'upload_date': '20170227',
            'like_count': int,
            'thumbnail': r're:http://.+/thumb\.png',
            'tags': ['乃木坂'],
            'view_count': int,
            'duration': 1503,
            'comment_count': int,
        }
    }, {
        'url': 'http://tv.kakao.com/channel/2653210/cliplink/300103180',
        'md5': 'a8917742069a4dd442516b86e7d66529',
        'info_dict': {
            'id': '300103180',
            'ext': 'mp4',
            'description': '러블리즈 - Destiny (나의 지구) (Lovelyz - Destiny)\r\n\r\n[쇼! 음악중심] 20160611, 507회',
            'title': '러블리즈 - Destiny (나의 지구) (Lovelyz - Destiny)',
            'uploader_id': '2653210',
            'uploader': '쇼! 음악중심',
            'timestamp': 1485684628,
            'upload_date': '20170129',
            'like_count': int,
            'thumbnail': r're:http://.+/thumb\.png',
            'tags': 'count:28',
            'view_count': int,
            'duration': 184,
            'comment_count': int,
        }
    }, {
        # geo restricted
        'url': 'https://tv.kakao.com/channel/3643855/cliplink/412069491',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        api_base = self._API_BASE_TMPL % video_id
        cdn_api_base = self._CDN_API % video_id

        query = {
            'player': 'monet_html5',
            'referer': url,
            'uuid': '',
            'service': 'kakao_tv',
            'section': '',
            'dteType': 'PC',
            'fields': ','.join([
                '-*', 'tid', 'clipLink', 'displayTitle', 'clip', 'title',
                'description', 'channelId', 'createTime', 'duration', 'playCount',
                'likeCount', 'commentCount', 'tagList', 'channel', 'name',
                'clipChapterThumbnailList', 'thumbnailUrl', 'timeInSec', 'isDefault',
                'videoOutputList', 'width', 'height', 'kbps', 'profile', 'label'])
        }

        api_json = self._download_json(
            api_base, video_id, 'Downloading video info')

        clip_link = api_json['clipLink']
        clip = clip_link['clip']

        title = clip.get('title') or clip_link.get('displayTitle')

        formats = []
        for fmt in clip.get('videoOutputList') or []:
            profile_name = fmt.get('profile')
            if not profile_name or profile_name == 'AUDIO':
                continue
            query.update({
                'profile': profile_name,
                'fields': '-*,code,message,url',
            })
            try:
                fmt_url_json = self._download_json(
                    cdn_api_base, video_id, query=query,
                    note='Downloading video URL for profile %s' % profile_name)
            except ExtractorError as e:
                if isinstance(e.cause, HTTPError) and e.cause.status == 403:
                    resp = self._parse_json(e.cause.response.read().decode(), video_id)
                    if resp.get('code') == 'GeoBlocked':
                        self.raise_geo_restricted()
                raise

            fmt_url = traverse_obj(fmt_url_json, ('videoLocation', 'url'))
            if not fmt_url:
                continue

            formats.append({
                'url': fmt_url,
                'format_id': profile_name,
                'width': int_or_none(fmt.get('width')),
                'height': int_or_none(fmt.get('height')),
                'format_note': fmt.get('label'),
                'filesize': int_or_none(fmt.get('filesize')),
                'tbr': int_or_none(fmt.get('kbps')),
            })

        thumbs = []
        for thumb in clip.get('clipChapterThumbnailList') or []:
            thumbs.append({
                'url': thumb.get('thumbnailUrl'),
                'id': str(thumb.get('timeInSec')),
                'preference': -1 if thumb.get('isDefault') else 0
            })
        top_thumbnail = clip.get('thumbnailUrl')
        if top_thumbnail:
            thumbs.append({
                'url': top_thumbnail,
                'preference': 10,
            })

        return {
            'id': video_id,
            'title': title,
            'description': strip_or_none(clip.get('description')),
            'uploader': traverse_obj(clip_link, ('channel', 'name')),
            'uploader_id': str_or_none(clip_link.get('channelId')),
            'thumbnails': thumbs,
            'timestamp': unified_timestamp(clip_link.get('createTime')),
            'duration': int_or_none(clip.get('duration')),
            'view_count': int_or_none(clip.get('playCount')),
            'like_count': int_or_none(clip.get('likeCount')),
            'comment_count': int_or_none(clip.get('commentCount')),
            'formats': formats,
            'tags': clip.get('tagList'),
        }
