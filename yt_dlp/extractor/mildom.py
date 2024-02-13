import functools
import json
import uuid

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    determine_ext,
    dict_get,
    float_or_none,
    traverse_obj,
)


class MildomBaseIE(InfoExtractor):
    _GUEST_ID = None

    def _call_api(self, url, video_id, query=None, note='Downloading JSON metadata', body=None):
        if not self._GUEST_ID:
            self._GUEST_ID = f'pc-gp-{str(uuid.uuid4())}'

        content = self._download_json(
            url, video_id, note=note, data=json.dumps(body).encode() if body else None,
            headers={'Content-Type': 'application/json'} if body else {},
            query={
                '__guest_id': self._GUEST_ID,
                '__platform': 'web',
                **(query or {}),
            })

        if content['code'] != 0:
            raise ExtractorError(
                f'Mildom says: {content["message"]} (code {content["code"]})',
                expected=True)
        return content['body']


class MildomIE(MildomBaseIE):
    IE_NAME = 'mildom'
    IE_DESC = 'Record ongoing live by specific user in Mildom'
    _VALID_URL = r'https?://(?:(?:www|m)\.)mildom\.com/(?P<id>\d+)'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(f'https://www.mildom.com/{video_id}', video_id)

        enterstudio = self._call_api(
            'https://cloudac.mildom.com/nonolive/gappserv/live/enterstudio', video_id,
            note='Downloading live metadata', query={'user_id': video_id})
        result_video_id = enterstudio.get('log_id', video_id)

        servers = self._call_api(
            'https://cloudac.mildom.com/nonolive/gappserv/live/liveserver', result_video_id,
            note='Downloading live server list', query={
                'user_id': video_id,
                'live_server_type': 'hls',
            })

        playback_token = self._call_api(
            'https://cloudac.mildom.com/nonolive/gappserv/live/token', result_video_id,
            note='Obtaining live playback token', body={'host_id': video_id, 'type': 'hls'})
        playback_token = traverse_obj(playback_token, ('data', ..., 'token'), get_all=False)
        if not playback_token:
            raise ExtractorError('Failed to obtain live playback token')

        formats = self._extract_m3u8_formats(
            f'{servers["stream_server"]}/{video_id}_master.m3u8?{playback_token}',
            result_video_id, 'mp4', headers={
                'Referer': 'https://www.mildom.com/',
                'Origin': 'https://www.mildom.com',
            })

        for fmt in formats:
            fmt.setdefault('http_headers', {})['Referer'] = 'https://www.mildom.com/'

        return {
            'id': result_video_id,
            'title': self._html_search_meta('twitter:description', webpage, default=None) or traverse_obj(enterstudio, 'anchor_intro'),
            'description': traverse_obj(enterstudio, 'intro', 'live_intro', expected_type=str),
            'timestamp': float_or_none(enterstudio.get('live_start_ms'), scale=1000),
            'uploader': self._html_search_meta('twitter:title', webpage, default=None) or traverse_obj(enterstudio, 'loginname'),
            'uploader_id': video_id,
            'formats': formats,
            'is_live': True,
        }


class MildomVodIE(MildomBaseIE):
    IE_NAME = 'mildom:vod'
    IE_DESC = 'VOD in Mildom'
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
        user_id, video_id = self._match_valid_url(url).group('user_id', 'id')
        webpage = self._download_webpage(f'https://www.mildom.com/playback/{user_id}/{video_id}', video_id)

        autoplay = self._call_api(
            'https://cloudac.mildom.com/nonolive/videocontent/playback/getPlaybackDetail', video_id,
            note='Downloading playback metadata', query={
                'v_id': video_id,
            })['playback']

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

        return {
            'id': video_id,
            'title': self._html_search_meta(('og:description', 'description'), webpage, default=None) or autoplay.get('title'),
            'description': traverse_obj(autoplay, 'video_intro'),
            'timestamp': float_or_none(autoplay.get('publish_time'), scale=1000),
            'duration': float_or_none(autoplay.get('video_length'), scale=1000),
            'thumbnail': dict_get(autoplay, ('upload_pic', 'video_pic')),
            'uploader': traverse_obj(autoplay, ('author_info', 'login_name')),
            'uploader_id': user_id,
            'formats': formats,
        }


class MildomClipIE(MildomBaseIE):
    IE_NAME = 'mildom:clip'
    IE_DESC = 'Clip in Mildom'
    _VALID_URL = r'https?://(?:(?:www|m)\.)mildom\.com/clip/(?P<id>(?P<user_id>\d+)-[a-zA-Z0-9]+)'
    _TESTS = [{
        'url': 'https://www.mildom.com/clip/10042245-63921673e7b147ebb0806d42b5ba5ce9',
        'info_dict': {
            'id': '10042245-63921673e7b147ebb0806d42b5ba5ce9',
            'title': '全然違ったよ',
            'timestamp': 1619181890,
            'duration': 59,
            'thumbnail': r're:https?://.+',
            'uploader': 'ざきんぽ',
            'uploader_id': '10042245',
        },
    }, {
        'url': 'https://www.mildom.com/clip/10111524-ebf4036e5aa8411c99fb3a1ae0902864',
        'info_dict': {
            'id': '10111524-ebf4036e5aa8411c99fb3a1ae0902864',
            'title': 'かっこいい',
            'timestamp': 1621094003,
            'duration': 59,
            'thumbnail': r're:https?://.+',
            'uploader': '(ルーキー',
            'uploader_id': '10111524',
        },
    }, {
        'url': 'https://www.mildom.com/clip/10660174-2c539e6e277c4aaeb4b1fbe8d22cb902',
        'info_dict': {
            'id': '10660174-2c539e6e277c4aaeb4b1fbe8d22cb902',
            'title': 'あ',
            'timestamp': 1614769431,
            'duration': 31,
            'thumbnail': r're:https?://.+',
            'uploader': 'ドルゴルスレンギーン＝ダグワドルジ',
            'uploader_id': '10660174',
        },
    }]

    def _real_extract(self, url):
        user_id, video_id = self._match_valid_url(url).group('user_id', 'id')
        webpage = self._download_webpage(f'https://www.mildom.com/clip/{video_id}', video_id)

        clip_detail = self._call_api(
            'https://cloudac-cf-jp.mildom.com/nonolive/videocontent/clip/detail', video_id,
            note='Downloading playback metadata', query={
                'clip_id': video_id,
            })

        return {
            'id': video_id,
            'title': self._html_search_meta(
                ('og:description', 'description'), webpage, default=None) or clip_detail.get('title'),
            'timestamp': float_or_none(clip_detail.get('create_time')),
            'duration': float_or_none(clip_detail.get('length')),
            'thumbnail': clip_detail.get('cover'),
            'uploader': traverse_obj(clip_detail, ('user_info', 'loginname')),
            'uploader_id': user_id,

            'url': clip_detail['url'],
            'ext': determine_ext(clip_detail.get('url'), 'mp4'),
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
        'playlist_mincount': 732,
    }, {
        'url': 'https://www.mildom.com/profile/10882672',
        'info_dict': {
            'id': '10882672',
            'title': 'Uploads from kson組長(けいそん)',
        },
        'playlist_mincount': 201,
    }]

    def _fetch_page(self, user_id, page):
        page += 1
        reply = self._call_api(
            'https://cloudac.mildom.com/nonolive/videocontent/profile/playbackList',
            user_id, note=f'Downloading page {page}', query={
                'user_id': user_id,
                'page': page,
                'limit': '30',
            })
        if not reply:
            return
        for x in reply:
            v_id = x.get('v_id')
            if not v_id:
                continue
            yield self.url_result(f'https://www.mildom.com/playback/{user_id}/{v_id}')

    def _real_extract(self, url):
        user_id = self._match_id(url)
        self.to_screen('This will download all VODs belonging to user. To download ongoing live video, use "https://www.mildom.com/%s" instead' % user_id)

        profile = self._call_api(
            'https://cloudac.mildom.com/nonolive/gappserv/user/profileV2', user_id,
            query={'user_id': user_id}, note='Downloading user profile')['user_info']

        return self.playlist_result(
            OnDemandPagedList(functools.partial(self._fetch_page, user_id), 30),
            user_id, f'Uploads from {profile["loginname"]}')
