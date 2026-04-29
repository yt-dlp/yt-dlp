import itertools
import json
import random
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    make_archive_id,
    mimetype2ext,
    parse_qs,
    parse_resolution,
    str_or_none,
    strip_jsonp,
    traverse_obj,
    truncate_string,
    url_or_none,
    urlencode_postdata,
    urljoin,
)


class WeiboBaseIE(InfoExtractor):
    def _update_visitor_cookies(self, visitor_url, video_id):
        headers = {'Referer': visitor_url}
        chrome_ver = self._search_regex(
            r'Chrome/(\d+)', self.get_param('http_headers')['User-Agent'], 'user agent version', default='90')
        visitor_data = self._download_json(
            'https://passport.weibo.com/visitor/genvisitor', video_id,
            note='Generating first-visit guest request',
            headers=headers, transform_source=strip_jsonp,
            data=urlencode_postdata({
                'cb': 'gen_callback',
                'fp': json.dumps({
                    'os': '1',
                    'browser': f'Chrome{chrome_ver},0,0,0',
                    'fonts': 'undefined',
                    'screenInfo': '1920*1080*24',
                    'plugins': '',
                }, separators=(',', ':'))}))['data']

        self._download_webpage(
            'https://passport.weibo.com/visitor/visitor', video_id,
            note='Running first-visit callback to get guest cookies',
            headers=headers, query={
                'a': 'incarnate',
                't': visitor_data['tid'],
                'w': 3 if visitor_data.get('new_tid') else 2,
                'c': f'{visitor_data.get("confidence", 100):03d}',
                'gc': '',
                'cb': 'cross_domain',
                'from': 'weibo',
                '_rand': random.random(),
            })

    def _weibo_download_json(self, url, video_id, note='Downloading JSON metadata', data=None, headers=None, query=None):
        headers = {
            'Referer': 'https://weibo.com/',
            **(headers or {}),
        }
        webpage, urlh = self._download_webpage_handle(url, video_id, note=note, data=data, headers=headers, query=query)
        if urllib.parse.urlparse(urlh.url).netloc == 'passport.weibo.com':
            self._update_visitor_cookies(urlh.url, video_id)
            webpage = self._download_webpage(url, video_id, note=note, data=data, headers=headers, query=query)
        return self._parse_json(webpage, video_id)

    def _extract_formats(self, video_info):
        media_info = traverse_obj(video_info, ('page_info', 'media_info'))
        formats = traverse_obj(media_info, (
            'playback_list', lambda _, v: url_or_none(v['play_info']['url']), 'play_info', {
                'url': 'url',
                'format': ('quality_desc', {str}),
                'format_id': ('label', {str}),
                'ext': ('mime', {mimetype2ext}),
                'tbr': ('bitrate', {int_or_none}, filter),
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
                            },
                        ), get_all=False),
                    })
        return formats

    def _parse_video_info(self, video_info):
        video_id = traverse_obj(video_info, (('id', 'id_str', 'mid'), {str_or_none}, any))
        return {
            'id': video_id,
            'extractor_key': WeiboIE.ie_key(),
            'extractor': WeiboIE.IE_NAME,
            'formats': self._extract_formats(video_info),
            'http_headers': {'Referer': 'https://weibo.com/'},
            '_old_archive_ids': [make_archive_id('WeiboMobile', video_id)],
            **traverse_obj(video_info, {
                'display_id': ('mblogid', {str_or_none}),
                'title': ('page_info', 'media_info', ('video_title', 'kol_title', 'name'),
                          {lambda x: x.replace('\n', ' ')}, {truncate_string(left=72)}, filter),
                'alt_title': ('page_info', 'media_info', ('video_title', 'kol_title', 'name'), {str}, filter),
                'description': ('text_raw', {str}),
                'duration': ('page_info', 'media_info', 'duration', {int_or_none}),
                'timestamp': ('page_info', 'media_info', 'video_publish_time', {int_or_none}),
                'thumbnail': ('page_info', 'page_pic', {url_or_none}),
                'uploader': ('user', 'screen_name', {str}),
                'uploader_id': ('user', ('id', 'id_str'), {str_or_none}),
                'uploader_url': ('user', 'profile_url', {urljoin('https://weibo.com/')}),
                'view_count': ('page_info', 'media_info', 'online_users_number', {int_or_none}),
                'like_count': ('attitudes_count', {int_or_none}),
                'repost_count': ('reposts_count', {int_or_none}),
            }, get_all=False),
            'tags': traverse_obj(video_info, ('topic_struct', ..., 'topic_title', {str})) or None,
        }


class WeiboIE(WeiboBaseIE):
    _VALID_URL = r'https?://(?:m\.weibo\.cn/(?:status|detail)|(?:www\.)?weibo\.com/\d+)/(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [{
        'url': 'https://weibo.com/7827771738/N4xlMvjhI',
        'info_dict': {
            'id': '4910815147462302',
            '_old_archive_ids': ['weibomobile 4910815147462302'],
            'ext': 'mp4',
            'display_id': 'N4xlMvjhI',
            'title': '【睡前消息暑假版第一期：拉泰国一把  对中国有好处】',
            'alt_title': '【睡前消息暑假版第一期：拉泰国一把  对中国有好处】',
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
            '_old_archive_ids': ['weibomobile 4189191225395228'],
            'ext': 'mp4',
            'display_id': 'FBqgOmDxO',
            'title': '柴犬柴犬的秒拍视频',
            'alt_title': '柴犬柴犬的秒拍视频',
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
        },
    }, {
        'url': 'https://m.weibo.cn/detail/4189191225395228',
        'only_matching': True,
    }, {
        'url': 'https://weibo.com/0/4224132150961381',
        'note': 'no playback_list example',
        'only_matching': True,
    }, {
        'url': 'https://m.weibo.cn/detail/5120561132606436',
        'info_dict': {
            'id': '5120561132606436',
        },
        'playlist_count': 9,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        meta = self._weibo_download_json(
            'https://weibo.com/ajax/statuses/show', video_id, query={'id': video_id})
        mix_media_info = traverse_obj(meta, ('mix_media_info', 'items', ...))
        if not mix_media_info:
            return self._parse_video_info(meta)

        return self.playlist_result(self._entries(mix_media_info), video_id)

    def _entries(self, mix_media_info):
        for media_info in traverse_obj(mix_media_info, lambda _, v: v['type'] != 'pic'):
            yield self._parse_video_info(traverse_obj(media_info, {
                'id': ('data', 'object_id'),
                'page_info': {'media_info': ('data', 'media_info', {dict})},
            }))


class WeiboVideoIE(WeiboBaseIE):
    _VIDEO_ID_RE = r'\d+:(?:[\da-f]{32}|\d{16,})'
    _VALID_URL = [
        fr'https?://(?:www\.)?weibo\.com/tv/show/(?P<id>{_VIDEO_ID_RE})',
        fr'https?://video\.weibo\.com/show/?\?(?:[^#]+&)?fid=(?P<id>{_VIDEO_ID_RE})',
    ]
    _TESTS = [{
        'url': 'https://weibo.com/tv/show/1034:4797699866951785?from=old_pc_videoshow',
        'info_dict': {
            'id': '4797700463137878',
            'ext': 'mp4',
            'display_id': 'LEZDodaiW',
            'title': '呃，稍微了解了一下靡烟miya，感觉这东西也太二了',
            'alt_title': '呃，稍微了解了一下靡烟miya，感觉这东西也太二了',
            'description': '呃，稍微了解了一下靡烟miya，感觉这东西也太二了 http://t.cn/A6aerGsM \u200b\u200b\u200b',
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
            '_old_archive_ids': ['weibomobile 4797700463137878'],
        },
    }, {
        'url': 'https://weibo.com/tv/show/1034:633c288cc043d0ca7808030f1157da64',
        'info_dict': {
            'id': '4189191225395228',
            'ext': 'mp4',
            'display_id': 'FBqgOmDxO',
            'title': '柴犬柴犬的秒拍视频',
            'alt_title': '柴犬柴犬的秒拍视频',
            'description': '午睡当然是要甜甜蜜蜜的啦！[坏笑]     Instagram：shibainu.gaku http://t.cn/RHbmjzW \u200B\u200B\u200B',
            'uploader': '柴犬柴犬',
            'uploader_id': '5926682210',
            'uploader_url': 'https://weibo.com/u/5926682210',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'duration': 53,
            'thumbnail': 'https://wx1.sinaimg.cn/large/006t5KMygy1fmu31fsqbej30hs0hstav.jpg',
            'timestamp': 1514264429,
            'upload_date': '20171226',
            '_old_archive_ids': ['weibomobile 4189191225395228'],
        },
    }, {
        'url': 'https://video.weibo.com/show?fid=1034:4967272104787984',
        'info_dict': {
            'id': '4967273022359838',
            'ext': 'mp4',
            'display_id': 'Nse4S9TTU',
            'title': '#张婧仪[超话]#📸#婧仪的相册集#  早收工的一天，小张@张婧仪 变身可可爱爱小导游，来次说走就走的泉州City Walk[举手]',
            'alt_title': '#张婧仪[超话]#📸#婧仪的相册集# \n早收工的一天，小张@张婧仪 变身可可爱爱小导游，来次说走就走的泉州City Walk[举手]',
            'description': '#张婧仪[超话]#📸#婧仪的相册集# \n早收工的一天，小张@张婧仪 变身可可爱爱小导游，来次说走就走的泉州City Walk[举手] http://t.cn/A6WTpbEu \u200B\u200B\u200B',
            'uploader': '张婧仪工作室',
            'uploader_id': '7610808848',
            'uploader_url': 'https://weibo.com/u/7610808848',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'duration': 85,
            'thumbnail': 'https://wx2.sinaimg.cn/orj480/008j4b3qly1hjsce01gnqj30u00gvwf8.jpg',
            'tags': ['婧仪的相册集'],
            'timestamp': 1699773545,
            'upload_date': '20231112',
            '_old_archive_ids': ['weibomobile 4967273022359838'],
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        post_data = f'data={{"Component_Play_Playinfo":{{"oid":"{video_id}"}}}}'.encode()
        video_info = self._weibo_download_json(
            'https://weibo.com/tv/api/component', video_id, data=post_data, headers={'Referer': url},
            query={'page': f'/tv/show/{video_id}'})['data']['Component_Play_Playinfo']
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
    }, {
        'url': 'https://weibo.com/u/7610808848?tabtype=newVideo&layerid=4967273022359838',
        'info_dict': {
            'id': '7610808848',
            'title': '张婧仪工作室的视频',
            'description': '张婧仪工作室的全部视频',
            'uploader': '张婧仪工作室',
        },
        'playlist_mincount': 61,
    }, {
        'url': 'https://weibo.com/u/7610808848?tabtype=newVideo&layerid=4967273022359838',
        'info_dict': {
            'id': '4967273022359838',
            'ext': 'mp4',
            'display_id': 'Nse4S9TTU',
            'title': '#张婧仪[超话]#📸#婧仪的相册集#  早收工的一天，小张@张婧仪 变身可可爱爱小导游，来次说走就走的泉州City Walk[举手]',
            'alt_title': '#张婧仪[超话]#📸#婧仪的相册集# \n早收工的一天，小张@张婧仪 变身可可爱爱小导游，来次说走就走的泉州City Walk[举手]',
            'description': '#张婧仪[超话]#📸#婧仪的相册集# \n早收工的一天，小张@张婧仪 变身可可爱爱小导游，来次说走就走的泉州City Walk[举手] http://t.cn/A6WTpbEu \u200B\u200B\u200B',
            'uploader': '张婧仪工作室',
            'uploader_id': '7610808848',
            'uploader_url': 'https://weibo.com/u/7610808848',
            'view_count': int,
            'like_count': int,
            'repost_count': int,
            'duration': 85,
            'thumbnail': 'https://wx2.sinaimg.cn/orj480/008j4b3qly1hjsce01gnqj30u00gvwf8.jpg',
            'tags': ['婧仪的相册集'],
            'timestamp': 1699773545,
            'upload_date': '20231112',
            '_old_archive_ids': ['weibomobile 4967273022359838'],
        },
        'params': {'noplaylist': True},
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
        params = {k: v[-1] for k, v in parse_qs(url).items()}
        video_id = params.get('layerid') if params.get('tabtype') == 'newVideo' else None
        if not self._yes_playlist(uid, video_id):
            return self.url_result(f'https://weibo.com/{uid}/{video_id}', WeiboIE, video_id)

        first_page = self._fetch_page(uid)
        uploader = traverse_obj(first_page, ('list', ..., 'user', 'screen_name', {str}), get_all=False)
        metainfo = {
            'title': f'{uploader}的视频',
            'description': f'{uploader}的全部视频',
            'uploader': uploader,
        } if uploader else {}

        return self.playlist_result(self._entries(uid, first_page), uid, **metainfo)
