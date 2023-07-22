import random

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    str_or_none,
    url_or_none,
    mimetype2ext,
    strip_jsonp,
    urlencode_postdata,
    traverse_obj,
)


class WeiboBaseIE(InfoExtractor):
    def _safe_download_json(self, url, video_id, *args, fatal=True, note='Downloading JSON metadata', **kwargs):
        webpage, urlh = self._download_webpage_handle(url, video_id, *args, fatal=fatal, note=note, **kwargs)
        if 'passport.weibo.com' in urlh.url:
            visitor_data = self._download_json(
                'https://passport.weibo.com/visitor/genvisitor', video_id,
                note='Generating first-visit data',
                transform_source=strip_jsonp,
                data=urlencode_postdata({
                    'cb': 'gen_callback',
                    'fp': '{"os":"2","browser":"Gecko57,0,0,0","fonts":"undefined","screenInfo":"1440*900*24","plugins":""}',
                }))

            self._download_webpage(
                'https://passport.weibo.com/visitor/visitor', video_id,
                note='Running first-visit callback',
                query={
                    'a': 'incarnate',
                    't': visitor_data['data']['tid'],
                    'w': 2,
                    'c': '%03d' % visitor_data['data']['confidence'],
                    'gc': '',
                    'cb': 'cross_domain',
                    'from': 'weibo',
                    '_rand': random.random(),
                })
            webpage = self._download_webpage(url, video_id, *args, fatal=fatal, note=note, **kwargs)
        return self._parse_json(webpage, video_id, fatal=fatal)


class WeiboIE(WeiboBaseIE):
    _VALID_URL = r'https?://(?:m\.weibo\.cn/status|(?:www\.)?weibo\.com/[0-9]+)/(?P<id>[a-zA-Z0-9]+)'
    _TEST = [{
        'url': 'https://weibo.com/6275294458/Fp6RGfbff?type=comment',
        'info_dict': {
            'id': 'Fp6RGfbff',
            'ext': 'mp4',
            'title': 'You should have servants to massage you,... 来自Hosico_猫 - 微博',
        },
    }, {
        'url': 'https://m.weibo.cn/status/4189191225395228',
        'info_dict': {
            'id': '4189191225395228',
            'ext': 'mp4',
            'title': '午睡当然是要甜甜蜜蜜的啦',
            'uploader': '柴犬柴犬'
        }
    }]

    def _extract_formats(self, playback_list):
        return [{
            **traverse_obj(play_info, {
                'url': ('url', {url_or_none}),
                'format': ('quality_desc', {str_or_none}),
                'format_id': ('label', {str_or_none}),
                'ext': ('mime', {mimetype2ext}),
                'bitrate': ('bitrate', {int_or_none}, {lambda i: i if i else None}),
                'vcodec': ('video_codecs', {str_or_none}),
                'fps': ('fps', {int_or_none}),
                'width': ('width', {int_or_none}),
                'height': ('height', {int_or_none}),
                'filesize': ('size', {int_or_none}),
                'acodec': ('audio_codecs', {str_or_none}),
                'asr': ('audio_sample_rate', {int_or_none}),
                'audio_channels': ('audio_channels', {int_or_none}),
            })
        } for play_info in traverse_obj(playback_list, (..., 'play_info'))]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video_info = self._safe_download_json(
            f'https://weibo.com/ajax/statuses/show?id={video_id}', video_id)

        return {
            'id': video_id,
            'formats': self._extract_formats(traverse_obj(video_info, ('page_info', 'media_info', 'playback_list'))),
            **traverse_obj(video_info, {
                'display_id': ('mblogid', {str_or_none}),
                'title': ('page_info', 'media_info', ('video_title', 'kol_title', 'next_title'), {str_or_none}),
                'description': ('text_raw', {str_or_none}),
                'duration': ('page_info', 'media_info', 'duration', {int_or_none}),
                'timestamp': ('page_info', 'media_info', 'video_publish_time', {int_or_none}),
                'thumbnails': (
                    'page_info', 'page_pic', {url_or_none},
                    {lambda i: [{'url': i, 'http_headers': {'Referer': 'https://weibo.com/'}}] if i else None}),
                'uploader': ('user', 'screen_name', {str_or_none}),
                'uploader_id': ('user', ('id', 'id_str'), {str_or_none}),
                'uploader_url': ('user', 'profile_url', {lambda i: f'https://weibo.com{i}' if i else None}),
                'view_count': ('page_info', 'media_info', 'online_users_number', {int_or_none}),
                'like_count': ('attitudes_count', {int_or_none}),
                'repost_count': ('reposts_count', {int_or_none}),
                'tags': ('topic_struct', ..., 'topic_title', {str_or_none}),
            }, get_all=False)
        }


class WeiboVideoIE(WeiboBaseIE):
    _VALID_URL = r'https://weibo.com/tv/show/(?P<prefix>\d+):(?P<id>\d+)'
    _TEST = []

    def _real_extract(self, url):
        prefix, video_id = self._match_valid_url(url).groups()

        post_data = f'data={{"Component_Play_Playinfo":{{"oid":"{prefix}:{video_id}"}}}}'.encode()
        video_info = self._safe_download_json(
            f'https://weibo.com/tv/api/component?page=%2Ftv%2Fshow%2F{prefix}%3A{video_id}',
            video_id, headers={'Referer': url}, data=post_data)['data']['Component_Play_Playinfo']
        return self.url_result(f'https://weibo.com/0/{video_info["mid"]}', WeiboIE)
