# coding: utf-8

from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    int_or_none,
    strip_or_none,
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
            'uploader_id': 2671005,
            'uploader': '그랑그랑이',
            'timestamp': 1488160199,
            'upload_date': '20170227',
        }
    }, {
        'url': 'http://tv.kakao.com/channel/2653210/cliplink/300103180',
        'md5': 'a8917742069a4dd442516b86e7d66529',
        'info_dict': {
            'id': '300103180',
            'ext': 'mp4',
            'description': '러블리즈 - Destiny (나의 지구) (Lovelyz - Destiny)\r\n\r\n[쇼! 음악중심] 20160611, 507회',
            'title': '러블리즈 - Destiny (나의 지구) (Lovelyz - Destiny)',
            'uploader_id': 2653210,
            'uploader': '쇼! 음악중심',
            'timestamp': 1485684628,
            'upload_date': '20170129',
        }
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
        for fmt in clip.get('videoOutputList', []):
            try:
                profile_name = fmt['profile']
                if profile_name == 'AUDIO':
                    continue
                query.update({
                    'profile': profile_name,
                    'fields': '-*,url',
                })

                fmt_url_json = self._download_json(
                    cdn_api_base, video_id,
                    'Downloading video URL for profile %s' % profile_name,
                    query=query, fatal=False)

                if fmt_url_json is None:
                    continue

                fmt_vidLocation = fmt_url_json['videoLocation']
                fmt_url = fmt_vidLocation['url']
                formats.append({
                    'url': fmt_url,
                    'format_id': profile_name,
                    'width': int_or_none(fmt.get('width')),
                    'height': int_or_none(fmt.get('height')),
                    'format_note': fmt.get('label'),
                    'filesize': int_or_none(fmt.get('filesize')),
                    'tbr': int_or_none(fmt.get('kbps')),
                })
            except KeyError:
                pass
        self._sort_formats(formats)

        thumbs = []
        for thumb in clip.get('clipChapterThumbnailList', []):
            thumbs.append({
                'url': thumb.get('thumbnailUrl'),
                'id': compat_str(thumb.get('timeInSec')),
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
            'uploader': clip_link.get('channel', {}).get('name'),
            'uploader_id': clip_link.get('channelId'),
            'thumbnails': thumbs,
            'timestamp': unified_timestamp(clip_link.get('createTime')),
            'duration': int_or_none(clip.get('duration')),
            'view_count': int_or_none(clip.get('playCount')),
            'like_count': int_or_none(clip.get('likeCount')),
            'comment_count': int_or_none(clip.get('commentCount')),
            'formats': formats,
            'tags': clip.get('tagList'),
        }
