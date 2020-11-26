# coding: utf-8
from __future__ import unicode_literals

import itertools
import json

from .naver import NaverBaseIE
from ..compat import (
    compat_HTTPError,
    compat_str,
)
from ..utils import (
    ExtractorError,
    int_or_none,
    merge_dicts,
    str_or_none,
    strip_or_none,
    try_get,
    urlencode_postdata,
)


class VLiveBaseIE(NaverBaseIE):
    _APP_ID = '8c6cc7b45d2568fb668be6e05b6e5a3b'


class VLiveIE(VLiveBaseIE):
    IE_NAME = 'vlive'
    _VALID_URL = r'https?://(?:(?:www|m)\.)?vlive\.tv/(?:video|embed)/(?P<id>[0-9]+)'
    _NETRC_MACHINE = 'vlive'
    _TESTS = [{
        'url': 'http://www.vlive.tv/video/1326',
        'md5': 'cc7314812855ce56de70a06a27314983',
        'info_dict': {
            'id': '1326',
            'ext': 'mp4',
            'title': "Girl's Day's Broadcast",
            'creator': "Girl's Day",
            'view_count': int,
            'uploader_id': 'muploader_a',
        },
    }, {
        'url': 'http://www.vlive.tv/video/16937',
        'info_dict': {
            'id': '16937',
            'ext': 'mp4',
            'title': '첸백시 걍방',
            'creator': 'EXO',
            'view_count': int,
            'subtitles': 'mincount:12',
            'uploader_id': 'muploader_j',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.vlive.tv/video/129100',
        'md5': 'ca2569453b79d66e5b919e5d308bff6b',
        'info_dict': {
            'id': '129100',
            'ext': 'mp4',
            'title': '[V LIVE] [BTS+] Run BTS! 2019 - EP.71 :: Behind the scene',
            'creator': 'BTS+',
            'view_count': int,
            'subtitles': 'mincount:10',
        },
        'skip': 'This video is only available for CH+ subscribers',
    }, {
        'url': 'https://www.vlive.tv/embed/1326',
        'only_matching': True,
    }, {
        # works only with gcc=KR
        'url': 'https://www.vlive.tv/video/225019',
        'only_matching': True,
    }]

    def _real_initialize(self):
        self._login()

    def _login(self):
        email, password = self._get_login_info()
        if None in (email, password):
            return

        def is_logged_in():
            login_info = self._download_json(
                'https://www.vlive.tv/auth/loginInfo', None,
                note='Downloading login info',
                headers={'Referer': 'https://www.vlive.tv/home'})
            return try_get(
                login_info, lambda x: x['message']['login'], bool) or False

        LOGIN_URL = 'https://www.vlive.tv/auth/email/login'
        self._request_webpage(
            LOGIN_URL, None, note='Downloading login cookies')

        self._download_webpage(
            LOGIN_URL, None, note='Logging in',
            data=urlencode_postdata({'email': email, 'pwd': password}),
            headers={
                'Referer': LOGIN_URL,
                'Content-Type': 'application/x-www-form-urlencoded'
            })

        if not is_logged_in():
            raise ExtractorError('Unable to log in', expected=True)

    def _call_api(self, path_template, video_id, fields=None):
        query = {'appId': self._APP_ID, 'gcc': 'KR'}
        if fields:
            query['fields'] = fields
        try:
            return self._download_json(
                'https://www.vlive.tv/globalv-web/vam-web/' + path_template % video_id, video_id,
                'Downloading %s JSON metadata' % path_template.split('/')[-1].split('-')[0],
                headers={'Referer': 'https://www.vlive.tv/'}, query=query)
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 403:
                self.raise_login_required(json.loads(e.cause.read().decode())['message'])
            raise

    def _real_extract(self, url):
        video_id = self._match_id(url)

        post = self._call_api(
            'post/v1.0/officialVideoPost-%s', video_id,
            'author{nickname},channel{channelCode,channelName},officialVideo{commentCount,exposeStatus,likeCount,playCount,playTime,status,title,type,vodId}')

        video = post['officialVideo']

        def get_common_fields():
            channel = post.get('channel') or {}
            return {
                'title': video.get('title'),
                'creator': post.get('author', {}).get('nickname'),
                'channel': channel.get('channelName'),
                'channel_id': channel.get('channelCode'),
                'duration': int_or_none(video.get('playTime')),
                'view_count': int_or_none(video.get('playCount')),
                'like_count': int_or_none(video.get('likeCount')),
                'comment_count': int_or_none(video.get('commentCount')),
            }

        video_type = video.get('type')
        if video_type == 'VOD':
            inkey = self._call_api('video/v1.0/vod/%s/inkey', video_id)['inkey']
            vod_id = video['vodId']
            return merge_dicts(
                get_common_fields(),
                self._extract_video_info(video_id, vod_id, inkey))
        elif video_type == 'LIVE':
            status = video.get('status')
            if status == 'ON_AIR':
                stream_url = self._call_api(
                    'old/v3/live/%s/playInfo',
                    video_id)['result']['adaptiveStreamUrl']
                formats = self._extract_m3u8_formats(stream_url, video_id, 'mp4')
                info = get_common_fields()
                info.update({
                    'title': self._live_title(video['title']),
                    'id': video_id,
                    'formats': formats,
                    'is_live': True,
                })
                return info
            elif status == 'ENDED':
                raise ExtractorError(
                    'Uploading for replay. Please wait...', expected=True)
            elif status == 'RESERVED':
                raise ExtractorError('Coming soon!', expected=True)
            elif video.get('exposeStatus') == 'CANCEL':
                raise ExtractorError(
                    'We are sorry, but the live broadcast has been canceled.',
                    expected=True)
            else:
                raise ExtractorError('Unknown status ' + status)


class VLivePostIE(VLiveIE):
    IE_NAME = 'vlive:post'
    _VALID_URL = r'https?://(?:(?:www|m)\.)?vlive\.tv/post/(?P<id>\d-\d+)'
    _TESTS = [{
        # uploadType = SOS
        'url': 'https://www.vlive.tv/post/1-20088044',
        'info_dict': {
            'id': '1-20088044',
            'title': 'Hola estrellitas la tierra les dice hola (si era así no?) Ha...',
            'description': 'md5:fab8a1e50e6e51608907f46c7fa4b407',
        },
        'playlist_count': 3,
    }, {
        # uploadType = V
        'url': 'https://www.vlive.tv/post/1-20087926',
        'info_dict': {
            'id': '1-20087926',
            'title': 'James Corden: And so, the baby becamos the Papa💜😭💪😭',
        },
        'playlist_count': 1,
    }]
    _FVIDEO_TMPL = 'fvideo/v1.0/fvideo-%%s/%s'
    _SOS_TMPL = _FVIDEO_TMPL % 'sosPlayInfo'
    _INKEY_TMPL = _FVIDEO_TMPL % 'inKey'

    def _real_extract(self, url):
        post_id = self._match_id(url)

        post = self._call_api(
            'post/v1.0/post-%s', post_id,
            'attachments{video},officialVideo{videoSeq},plainBody,title')

        video_seq = str_or_none(try_get(
            post, lambda x: x['officialVideo']['videoSeq']))
        if video_seq:
            return self.url_result(
                'http://www.vlive.tv/video/' + video_seq,
                VLiveIE.ie_key(), video_seq)

        title = post['title']
        entries = []
        for idx, video in enumerate(post['attachments']['video'].values()):
            video_id = video.get('videoId')
            if not video_id:
                continue
            upload_type = video.get('uploadType')
            upload_info = video.get('uploadInfo') or {}
            entry = None
            if upload_type == 'SOS':
                download = self._call_api(
                    self._SOS_TMPL, video_id)['videoUrl']['download']
                formats = []
                for f_id, f_url in download.items():
                    formats.append({
                        'format_id': f_id,
                        'url': f_url,
                        'height': int_or_none(f_id[:-1]),
                    })
                self._sort_formats(formats)
                entry = {
                    'formats': formats,
                    'id': video_id,
                    'thumbnail': upload_info.get('imageUrl'),
                }
            elif upload_type == 'V':
                vod_id = upload_info.get('videoId')
                if not vod_id:
                    continue
                inkey = self._call_api(self._INKEY_TMPL, video_id)['inKey']
                entry = self._extract_video_info(video_id, vod_id, inkey)
            if entry:
                entry['title'] = '%s_part%s' % (title, idx)
                entries.append(entry)
        return self.playlist_result(
            entries, post_id, title, strip_or_none(post.get('plainBody')))


class VLiveChannelIE(VLiveBaseIE):
    IE_NAME = 'vlive:channel'
    _VALID_URL = r'https?://(?:channels\.vlive\.tv|(?:(?:www|m)\.)?vlive\.tv/channel)/(?P<id>[0-9A-Z]+)'
    _TESTS = [{
        'url': 'http://channels.vlive.tv/FCD4B',
        'info_dict': {
            'id': 'FCD4B',
            'title': 'MAMAMOO',
        },
        'playlist_mincount': 110
    }, {
        'url': 'https://www.vlive.tv/channel/FCD4B',
        'only_matching': True,
    }]

    def _call_api(self, path, channel_key_suffix, channel_value, note, query):
        q = {
            'app_id': self._APP_ID,
            'channel' + channel_key_suffix: channel_value,
        }
        q.update(query)
        return self._download_json(
            'http://api.vfan.vlive.tv/vproxy/channelplus/' + path,
            channel_value, note='Downloading ' + note, query=q)['result']

    def _real_extract(self, url):
        channel_code = self._match_id(url)

        channel_seq = self._call_api(
            'decodeChannelCode', 'Code', channel_code,
            'decode channel code', {})['channelSeq']

        channel_name = None
        entries = []

        for page_num in itertools.count(1):
            video_list = self._call_api(
                'getChannelVideoList', 'Seq', channel_seq,
                'channel list page #%d' % page_num, {
                    # Large values of maxNumOfRows (~300 or above) may cause
                    # empty responses (see [1]), e.g. this happens for [2] that
                    # has more than 300 videos.
                    # 1. https://github.com/ytdl-org/youtube-dl/issues/13830
                    # 2. http://channels.vlive.tv/EDBF.
                    'maxNumOfRows': 100,
                    'pageNo': page_num
                }
            )

            if not channel_name:
                channel_name = try_get(
                    video_list,
                    lambda x: x['channelInfo']['channelName'],
                    compat_str)

            videos = try_get(
                video_list, lambda x: x['videoList'], list)
            if not videos:
                break

            for video in videos:
                video_id = video.get('videoSeq')
                if not video_id:
                    continue
                video_id = compat_str(video_id)
                entries.append(
                    self.url_result(
                        'http://www.vlive.tv/video/%s' % video_id,
                        ie=VLiveIE.ie_key(), video_id=video_id))

        return self.playlist_result(
            entries, channel_code, channel_name)
