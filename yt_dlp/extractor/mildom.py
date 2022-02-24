# coding: utf-8
from __future__ import unicode_literals

import base64
from datetime import datetime
import itertools
import json

from .common import InfoExtractor
from ..utils import (
    std_headers,
    update_url_query,
    random_uuidv4,
    try_get,
    float_or_none,
    dict_get
)
from ..compat import (
    compat_str,
)


class MildomBaseIE(InfoExtractor):
    _GUEST_ID = None
    _DISPATCHER_CONFIG = None

    def _call_api(self, url, video_id, query=None, note='Downloading JSON metadata', init=False):
        query = query or {}
        if query:
            query['__platform'] = 'web'
        url = update_url_query(url, self._common_queries(query, init=init))
        content = self._download_json(url, video_id, note=note)
        if content['code'] == 0:
            return content['body']
        else:
            self.raise_no_formats(
                f'Video not found or premium content. {content["code"]} - {content["message"]}',
                expected=True)

    def _common_queries(self, query={}, init=False):
        dc = self._fetch_dispatcher_config()
        r = {
            'timestamp': self.iso_timestamp(),
            '__guest_id': '' if init else self.guest_id(),
            '__location': dc['location'],
            '__country': dc['country'],
            '__cluster': dc['cluster'],
            '__platform': 'web',
            '__la': self.lang_code(),
            '__pcv': 'v2.9.44',
            'sfr': 'pc',
            'accessToken': '',
        }
        r.update(query)
        return r

    def _fetch_dispatcher_config(self):
        if not self._DISPATCHER_CONFIG:
            tmp = self._download_json(
                'https://disp.mildom.com/serverListV2', 'initialization',
                note='Downloading dispatcher_config', data=json.dumps({
                    'protover': 0,
                    'data': base64.b64encode(json.dumps({
                        'fr': 'web',
                        'sfr': 'pc',
                        'devi': 'Windows',
                        'la': 'ja',
                        'gid': None,
                        'loc': '',
                        'clu': '',
                        'wh': '1919*810',
                        'rtm': self.iso_timestamp(),
                        'ua': std_headers['User-Agent'],
                    }).encode('utf8')).decode('utf8').replace('\n', ''),
                }).encode('utf8'))
            self._DISPATCHER_CONFIG = self._parse_json(base64.b64decode(tmp['data']), 'initialization')
        return self._DISPATCHER_CONFIG

    @staticmethod
    def iso_timestamp():
        'new Date().toISOString()'
        return datetime.utcnow().isoformat()[0:-3] + 'Z'

    def guest_id(self):
        'getGuestId'
        if self._GUEST_ID:
            return self._GUEST_ID
        self._GUEST_ID = try_get(
            self, (
                lambda x: x._call_api(
                    'https://cloudac.mildom.com/nonolive/gappserv/guest/h5init', 'initialization',
                    note='Downloading guest token', init=True)['guest_id'] or None,
                lambda x: x._get_cookies('https://www.mildom.com').get('gid').value,
                lambda x: x._get_cookies('https://m.mildom.com').get('gid').value,
            ), compat_str) or ''
        return self._GUEST_ID

    def lang_code(self):
        'getCurrentLangCode'
        return 'ja'


class MildomIE(MildomBaseIE):
    IE_NAME = 'mildom'
    IE_DESC = 'Record ongoing live by specific user in Mildom'
    _VALID_URL = r'https?://(?:(?:www|m)\.)mildom\.com/(?P<id>\d+)'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        url = 'https://www.mildom.com/%s' % video_id

        webpage = self._download_webpage(url, video_id)

        enterstudio = self._call_api(
            'https://cloudac.mildom.com/nonolive/gappserv/live/enterstudio', video_id,
            note='Downloading live metadata', query={'user_id': video_id})
        result_video_id = enterstudio.get('log_id', video_id)

        title = try_get(
            enterstudio, (
                lambda x: self._html_search_meta('twitter:description', webpage),
                lambda x: x['anchor_intro'],
            ), compat_str)
        description = try_get(
            enterstudio, (
                lambda x: x['intro'],
                lambda x: x['live_intro'],
            ), compat_str)
        uploader = try_get(
            enterstudio, (
                lambda x: self._html_search_meta('twitter:title', webpage),
                lambda x: x['loginname'],
            ), compat_str)

        servers = self._call_api(
            'https://cloudac.mildom.com/nonolive/gappserv/live/liveserver', result_video_id,
            note='Downloading live server list', query={
                'user_id': video_id,
                'live_server_type': 'hls',
            })

        stream_query = self._common_queries({
            'streamReqId': random_uuidv4(),
            'is_lhls': '0',
        })
        m3u8_url = update_url_query(servers['stream_server'] + '/%s_master.m3u8' % video_id, stream_query)
        formats = self._extract_m3u8_formats(m3u8_url, result_video_id, 'mp4', headers={
            'Referer': 'https://www.mildom.com/',
            'Origin': 'https://www.mildom.com',
        }, note='Downloading m3u8 information')

        del stream_query['streamReqId'], stream_query['timestamp']
        for fmt in formats:
            fmt.setdefault('http_headers', {})['Referer'] = 'https://www.mildom.com/'

        self._sort_formats(formats)

        return {
            'id': result_video_id,
            'title': title,
            'description': description,
            'timestamp': float_or_none(enterstudio.get('live_start_ms'), scale=1000),
            'uploader': uploader,
            'uploader_id': video_id,
            'formats': formats,
            'is_live': True,
        }


class MildomVodIE(MildomBaseIE):
    IE_NAME = 'mildom:vod'
    IE_DESC = 'Download a VOD in Mildom'
    _VALID_URL = r'https?://(?:(?:www|m)\.)mildom\.com/playback/(?P<user_id>\d+)/(?P<id>(?P=user_id)-[a-zA-Z0-9]+-?[0-9]*)'
    _TESTS = [{
        'url': 'https://www.mildom.com/playback/10882672/10882672-1597662269',
        'info_dict': {
            'id': '10882672-1597662269',
            'ext': 'mp4',
            'title': '始めてのミルダム配信じゃぃ！',
            'thumbnail': r're:^https?://.*\.(png|jpg)$',
            'upload_date': '20200817',
            'duration': 4138.37,
            'description': 'ゲームをしたくて！',
            'timestamp': 1597662269.0,
            'uploader_id': '10882672',
            'uploader': 'kson組長(けいそん)',
        },
    }, {
        'url': 'https://www.mildom.com/playback/10882672/10882672-1597758589870-477',
        'info_dict': {
            'id': '10882672-1597758589870-477',
            'ext': 'mp4',
            'title': '【kson】感染メイズ！麻酔銃で無双する',
            'thumbnail': r're:^https?://.*\.(png|jpg)$',
            'timestamp': 1597759093.0,
            'uploader': 'kson組長(けいそん)',
            'duration': 4302.58,
            'uploader_id': '10882672',
            'description': 'このステージ絶対乗り越えたい',
            'upload_date': '20200818',
        },
    }, {
        'url': 'https://www.mildom.com/playback/10882672/10882672-buha9td2lrn97fk2jme0',
        'info_dict': {
            'id': '10882672-buha9td2lrn97fk2jme0',
            'ext': 'mp4',
            'title': '【kson組長】CART RACER!!!',
            'thumbnail': r're:^https?://.*\.(png|jpg)$',
            'uploader_id': '10882672',
            'uploader': 'kson組長(けいそん)',
            'upload_date': '20201104',
            'timestamp': 1604494797.0,
            'duration': 4657.25,
            'description': 'WTF',
        },
    }]

    def _real_extract(self, url):
        m = self._match_valid_url(url)
        user_id, video_id = m.group('user_id'), m.group('id')
        url = 'https://www.mildom.com/playback/%s/%s' % (user_id, video_id)

        webpage = self._download_webpage(url, video_id)

        autoplay = self._call_api(
            'https://cloudac.mildom.com/nonolive/videocontent/playback/getPlaybackDetail', video_id,
            note='Downloading playback metadata', query={
                'v_id': video_id,
            })['playback']

        title = try_get(
            autoplay, (
                lambda x: self._html_search_meta('og:description', webpage),
                lambda x: x['title'],
            ), compat_str)
        description = try_get(
            autoplay, (
                lambda x: x['video_intro'],
            ), compat_str)
        uploader = try_get(
            autoplay, (
                lambda x: x['author_info']['login_name'],
            ), compat_str)

        formats = [{
            'url': autoplay['audio_url'],
            'format_id': 'audio',
            'protocol': 'm3u8_native',
            'vcodec': 'none',
            'acodec': 'aac',
            'ext': 'm4a'
        }]
        for fmt in autoplay['video_link']:
            formats.append({
                'format_id': 'video-%s' % fmt['name'],
                'url': fmt['url'],
                'protocol': 'm3u8_native',
                'width': fmt['level'] * autoplay['video_width'] // autoplay['video_height'],
                'height': fmt['level'],
                'vcodec': 'h264',
                'acodec': 'aac',
                'ext': 'mp4'
            })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'timestamp': float_or_none(autoplay['publish_time'], scale=1000),
            'duration': float_or_none(autoplay['video_length'], scale=1000),
            'thumbnail': dict_get(autoplay, ('upload_pic', 'video_pic')),
            'uploader': uploader,
            'uploader_id': user_id,
            'formats': formats,
        }


class MildomUserVodIE(MildomBaseIE):
    IE_NAME = 'mildom:user:vod'
    IE_DESC = 'Download all VODs from specific user in Mildom'
    _VALID_URL = r'https?://(?:(?:www|m)\.)mildom\.com/profile/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.mildom.com/profile/10093333',
        'info_dict': {
            'id': '10093333',
            'title': 'Uploads from ねこばたけ',
        },
        'playlist_mincount': 351,
    }, {
        'url': 'https://www.mildom.com/profile/10882672',
        'info_dict': {
            'id': '10882672',
            'title': 'Uploads from kson組長(けいそん)',
        },
        'playlist_mincount': 191,
    }]

    def _entries(self, user_id):
        for page in itertools.count(1):
            reply = self._call_api(
                'https://cloudac.mildom.com/nonolive/videocontent/profile/playbackList',
                user_id, note='Downloading page %d' % page, query={
                    'user_id': user_id,
                    'page': page,
                    'limit': '30',
                })
            if not reply:
                break
            for x in reply:
                yield self.url_result('https://www.mildom.com/playback/%s/%s' % (user_id, x['v_id']))

    def _real_extract(self, url):
        user_id = self._match_id(url)
        self.to_screen('This will download all VODs belonging to user. To download ongoing live video, use "https://www.mildom.com/%s" instead' % user_id)

        profile = self._call_api(
            'https://cloudac.mildom.com/nonolive/gappserv/user/profileV2', user_id,
            query={'user_id': user_id}, note='Downloading user profile')['user_info']

        return self.playlist_result(
            self._entries(user_id), user_id, 'Uploads from %s' % profile['loginname'])
