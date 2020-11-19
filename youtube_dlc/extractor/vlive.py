# coding: utf-8
from __future__ import unicode_literals

import re
import time
import itertools
import json

from .common import InfoExtractor
from .naver import NaverBaseIE
from ..compat import (
    compat_HTTPError,
    compat_str,
)
from ..utils import (
    ExtractorError,
    int_or_none,
    merge_dicts,
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
        query = {'appId': self._APP_ID}
        if fields:
            query['fields'] = fields
        return self._download_json(
            'https://www.vlive.tv/globalv-web/vam-web/' + path_template % video_id, video_id,
            'Downloading %s JSON metadata' % path_template.split('/')[-1].split('-')[0],
            headers={'Referer': 'https://www.vlive.tv/'}, query=query)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        try:
            post = self._call_api(
                'post/v1.0/officialVideoPost-%s', video_id,
                'author{nickname},channel{channelCode,channelName},officialVideo{commentCount,exposeStatus,likeCount,playCount,playTime,status,title,type,vodId}')
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 403:
                self.raise_login_required(json.loads(e.cause.read().decode())['message'])
            raise

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


# old extractor. Rewrite?

class VLivePlaylistIE(VLiveBaseIE):
    IE_NAME = 'vlive:playlist'
    _VALID_URL = r'https?://(?:(?:www|m)\.)?vlive\.tv/video/(?P<video_id>[0-9]+)/playlist/(?P<id>[0-9]+)'
    _VIDEO_URL_TEMPLATE = 'http://www.vlive.tv/video/%s'
    _TESTS = [{
        # regular working playlist
        'url': 'https://www.vlive.tv/video/117956/playlist/117963',
        'info_dict': {
            'id': '117963',
            'title': '아이돌룸(IDOL ROOM) 41회 - (여자)아이들'
        },
        'playlist_mincount': 10
    }, {
        # playlist with no playlistVideoSeqs
        'url': 'http://www.vlive.tv/video/22867/playlist/22912',
        'info_dict': {
            'id': '22867',
            'ext': 'mp4',
            'title': '[V LIVE] Valentine Day Message from MINA',
            'creator': 'TWICE',
            'view_count': int
        },
        'params': {
            'skip_download': True,
        }
    }]

    def _build_video_result(self, video_id, message):
        self.to_screen(message)
        return self.url_result(
            self._VIDEO_URL_TEMPLATE % video_id,
            ie=VLiveIE.ie_key(), video_id=video_id)

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id, playlist_id = mobj.group('video_id', 'id')

        if self._downloader.params.get('noplaylist'):
            return self._build_video_result(
                video_id,
                'Downloading just video %s because of --no-playlist'
                % video_id)

        self.to_screen(
            'Downloading playlist %s - add --no-playlist to just download video'
            % playlist_id)

        webpage = self._download_webpage(
            'http://www.vlive.tv/video/%s/playlist/%s'
            % (video_id, playlist_id), playlist_id)

        raw_item_ids = self._search_regex(
            r'playlistVideoSeqs\s*=\s*(\[[^]]+\])', webpage,
            'playlist video seqs', default=None, fatal=False)

        if not raw_item_ids:
            return self._build_video_result(
                video_id,
                'Downloading just video %s because no playlist was found'
                % video_id)

        item_ids = self._parse_json(raw_item_ids, playlist_id)

        entries = [
            self.url_result(
                self._VIDEO_URL_TEMPLATE % item_id, ie=VLiveIE.ie_key(),
                video_id=compat_str(item_id))
            for item_id in item_ids]

        playlist_name = self._html_search_regex(
            r'<div[^>]+class="[^"]*multicam_playlist[^>]*>\s*<h3[^>]+>([^<]+)',
            webpage, 'playlist title', fatal=False)

        return self.playlist_result(entries, playlist_id, playlist_name)
