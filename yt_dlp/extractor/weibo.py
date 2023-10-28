import random
import itertools
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    make_archive_id,
    mimetype2ext,
    parse_resolution,
    str_or_none,
    strip_jsonp,
    traverse_obj,
    url_or_none,
    urlencode_postdata,
    urljoin,
)


class WeiboBaseIE(InfoExtractor):
    def _update_visitor_cookies(self, video_id):
        visitor_data = self._download_json(
            'https://passport.weibo.com/visitor/genvisitor', video_id,
            note='Generating first-visit guest request',
            transform_source=strip_jsonp,
            data=urlencode_postdata({
                'cb': 'gen_callback',
                'fp': '{"os":"2","browser":"Gecko57,0,0,0","fonts":"undefined","screenInfo":"1440*900*24","plugins":""}',
            }))

        self._download_webpage(
            'https://passport.weibo.com/visitor/visitor', video_id,
            note='Running first-visit callback to get guest cookies',
            query={
                'a': 'incarnate',
                't': visitor_data['data']['tid'],
                'w': 2,
                'c': '%03d' % visitor_data['data']['confidence'],
                'cb': 'cross_domain',
                'from': 'weibo',
                '_rand': random.random(),
            })

    def _weibo_download_json(self, url, video_id, *args, fatal=True, note='Downloading JSON metadata', **kwargs):
        webpage, urlh = self._download_webpage_handle(url, video_id, *args, fatal=fatal, note=note, **kwargs)
        if urllib.parse.urlparse(urlh.url).netloc == 'passport.weibo.com':
            self._update_visitor_cookies(video_id)
            webpage = self._download_webpage(url, video_id, *args, fatal=fatal, note=note, **kwargs)
        return self._parse_json(webpage, video_id, fatal=fatal)

    def _extract_formats(self, video_info):
        media_info = traverse_obj(video_info, ('page_info', 'media_info'))
        formats = traverse_obj(media_info, (
            'playback_list', lambda _, v: url_or_none(v['play_info']['url']), 'play_info', {
                'url': 'url',
                'format': ('quality_desc', {str}),
                'format_id': ('label', {str}),
                'ext': ('mime', {mimetype2ext}),
                'tbr': ('bitrate', {int_or_none}, {lambda x: x or None}),
                'vcodec': ('video_codecs', {str}),
                'fps': ('fps', {int_or_none}),
                'width': ('width', {int_or_none}),
                'height': ('height', {int_or_none}),
                'filesize': ('size', {int_or_none}),
                'acodec': ('audio_codecs', {str}),
                'asr': ('audio_sample_rate', {int_or_none}),
                'audio_channels': ('audio_channels', {int_or_none}),
            }))
        if not formats:  # fallback, should be barely used
            for url in set(traverse_obj(media_info, (..., {url_or_none}))):
                if 'label=' in url:  # filter out non-video urls
                    format_id, resolution = self._search_regex(
                        r'label=(\w+)&template=(\d+x\d+)', url, 'format info',
                        group=(1, 2), default=(None, None))
                    formats.append({
                        'url': url,
                        'format_id': format_id,
                        **parse_resolution(resolution),
                        **traverse_obj(media_info, (
                            'video_details', lambda _, v: v['label'].startswith(format_id), {
                                'size': ('size', {int_or_none}),
                                'tbr': ('bitrate', {int_or_none}),
                            }
                        ), get_all=False),
                    })
        return formats

    def _parse_video_info(self, video_info, video_id=None):
        return {
            'id': video_id,
            'extractor_key': WeiboIE.ie_key(),
            'extractor': WeiboIE.IE_NAME,
            'formats': self._extract_formats(video_info),
            'http_headers': {'Referer': 'https://weibo.com/'},
            '_old_archive_ids': [make_archive_id('WeiboMobile', video_id)],
            **traverse_obj(video_info, {
                'id': (('id', 'id_str', 'mid'), {str_or_none}),
                'display_id': ('mblogid', {str_or_none}),
                'title': ('page_info', 'media_info', ('video_title', 'kol_title', 'name'), {str}, {lambda x: x or None}),
                'description': ('text_raw', {str}),
                'duration': ('page_info', 'media_info', 'duration', {int_or_none}),
                'timestamp': ('page_info', 'media_info', 'video_publish_time', {int_or_none}),
                'thumbnail': ('page_info', 'page_pic', {url_or_none}),
                'uploader': ('user', 'screen_name', {str}),
                'uploader_id': ('user', ('id', 'id_str'), {str_or_none}),
                'uploader_url': ('user', 'profile_url', {lambda x: urljoin('https://weibo.com/', x)}),
                'view_count': ('page_info', 'media_info', 'online_users_number', {int_or_none}),
                'like_count': ('attitudes_count', {int_or_none}),
                'repost_count': ('reposts_count', {int_or_none}),
            }, get_all=False),
            'tags': traverse_obj(video_info, ('topic_struct', ..., 'topic_title', {str})) or None,
        }


class WeiboIE(WeiboBaseIE):
    _VALID_URL = r'https?://(?:m\.weibo\.cn/status|(?:www\.)?weibo\.com/\d+)/(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [{
        'url': 'https://weibo.com/7827771738/N4xlMvjhI',
        'info_dict': {
            'id': '4910815147462302',
            'ext': 'mp4',
            'display_id': 'N4xlMvjhI',
            'title': '【睡前消息暑假版第一期：拉泰国一把  对中国有好处】',
            'description': 'md5:e2637a7673980d68694ea7c43cf12a5f',
            'duration': 918,
            'timestamp': 1686312819,
            'upload_date': '20230609',
            'thumbnail': r're:https://.*\.jpg',
            'uploader': '睡前视频基地',
            'uploader_id': '7827771738',
            'uploader_url': 'https://weibo.com/u/7827771738',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'tags': ['泰国大选远进党获胜', '睡前消息', '暑期版'],
        },
    }, {
        'url': 'https://m.weibo.cn/status/4189191225395228',
        'info_dict': {
            'id': '4189191225395228',
            'ext': 'mp4',
            'display_id': 'FBqgOmDxO',
            'title': '柴犬柴犬的秒拍视频',
            'description': 'md5:80f461ab5cdae6bbdb70efbf5a1db24f',
            'duration': 53,
            'timestamp': 1514264429,
            'upload_date': '20171226',
            'thumbnail': r're:https://.*\.jpg',
            'uploader': '柴犬柴犬',
            'uploader_id': '5926682210',
            'uploader_url': 'https://weibo.com/u/5926682210',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
        }
    }, {
        'url': 'https://weibo.com/0/4224132150961381',
        'note': 'no playback_list example',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        return self._parse_video_info(self._weibo_download_json(
            f'https://weibo.com/ajax/statuses/show?id={video_id}', video_id))


class WeiboVideoIE(WeiboBaseIE):
    _VALID_URL = r'https?://(?:www\.)?weibo\.com/tv/show/(?P<id>\d+:\d+)'
    _TESTS = [{
        'url': 'https://weibo.com/tv/show/1034:4797699866951785?from=old_pc_videoshow',
        'info_dict': {
            'id': '4797700463137878',
            'ext': 'mp4',
            'display_id': 'LEZDodaiW',
            'title': '呃，稍微了解了一下靡烟miya，感觉这东西也太二了',
            'description': '呃，稍微了解了一下靡烟miya，感觉这东西也太二了 http://t.cn/A6aerGsM ​​​',
            'duration': 76,
            'timestamp': 1659344278,
            'upload_date': '20220801',
            'thumbnail': r're:https://.*\.jpg',
            'uploader': '君子爱财陈平安',
            'uploader_id': '3905382233',
            'uploader_url': 'https://weibo.com/u/3905382233',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        post_data = f'data={{"Component_Play_Playinfo":{{"oid":"{video_id}"}}}}'.encode()
        video_info = self._weibo_download_json(
            f'https://weibo.com/tv/api/component?page=%2Ftv%2Fshow%2F{video_id.replace(":", "%3A")}',
            video_id, headers={'Referer': url}, data=post_data)['data']['Component_Play_Playinfo']
        return self.url_result(f'https://weibo.com/0/{video_info["mid"]}', WeiboIE)


class WeiboUserIE(WeiboBaseIE):
    _VALID_URL = r'https?://(?:www\.)?weibo\.com/u/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://weibo.com/u/2066652961?tabtype=video',
        'info_dict': {
            'id': '2066652961',
            'title': '萧影殿下的视频',
            'description': '萧影殿下的全部视频',
            'uploader': '萧影殿下',
        },
        'playlist_mincount': 195,
    }]

    def _fetch_page(self, uid, cursor=0, page=1):
        return self._weibo_download_json(
            'https://weibo.com/ajax/profile/getWaterFallContent',
            uid, note=f'Downloading videos page {page}',
            query={'uid': uid, 'cursor': cursor})['data']

    def _entries(self, uid, first_page):
        cursor = 0
        for page in itertools.count(1):
            response = first_page if page == 1 else self._fetch_page(uid, cursor, page)
            for video_info in traverse_obj(response, ('list', ..., {dict})):
                yield self._parse_video_info(video_info)
            cursor = response.get('next_cursor')
            if (int_or_none(cursor) or -1) < 0:
                break

    def _real_extract(self, url):
        uid = self._match_id(url)
        first_page = self._fetch_page(uid)
        uploader = traverse_obj(first_page, ('list', ..., 'user', 'screen_name', {str}), get_all=False)
        metainfo = {
            'title': f'{uploader}的视频',
            'description': f'{uploader}的全部视频',
            'uploader': uploader,
        } if uploader else {}

        return self.playlist_result(self._entries(uid, first_page), uid, **metainfo)
