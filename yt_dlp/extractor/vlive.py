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
    LazyList,
    merge_dicts,
    str_or_none,
    strip_or_none,
    try_get,
    urlencode_postdata,
    url_or_none,
)


class VLiveBaseIE(NaverBaseIE):
    _NETRC_MACHINE = 'vlive'
    _logged_in = False

    def _perform_login(self, username, password):
        if self._logged_in:
            return
        LOGIN_URL = 'https://www.vlive.tv/auth/email/login'
        self._request_webpage(
            LOGIN_URL, None, note='Downloading login cookies')

        self._download_webpage(
            LOGIN_URL, None, note='Logging in',
            data=urlencode_postdata({'email': username, 'pwd': password}),
            headers={
                'Referer': LOGIN_URL,
                'Content-Type': 'application/x-www-form-urlencoded'
            })

        login_info = self._download_json(
            'https://www.vlive.tv/auth/loginInfo', None,
            note='Checking login status',
            headers={'Referer': 'https://www.vlive.tv/home'})

        if not try_get(login_info, lambda x: x['message']['login'], bool):
            raise ExtractorError('Unable to log in', expected=True)
        VLiveBaseIE._logged_in = True

    def _call_api(self, path_template, video_id, fields=None, query_add={}, note=None):
        if note is None:
            note = 'Downloading %s JSON metadata' % path_template.split('/')[-1].split('-')[0]
        query = {'appId': '8c6cc7b45d2568fb668be6e05b6e5a3b', 'gcc': 'KR', 'platformType': 'PC'}
        if fields:
            query['fields'] = fields
        if query_add:
            query.update(query_add)
        try:
            return self._download_json(
                'https://www.vlive.tv/globalv-web/vam-web/' + path_template % video_id, video_id,
                note, headers={'Referer': 'https://www.vlive.tv/'}, query=query)
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 403:
                self.raise_login_required(json.loads(e.cause.read().decode('utf-8'))['message'])
            raise


class VLiveIE(VLiveBaseIE):
    IE_NAME = 'vlive'
    _VALID_URL = r'https?://(?:(?:www|m)\.)?vlive\.tv/(?:video|embed)/(?P<id>[0-9]+)'
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
            'upload_date': '20150817',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)$',
            'timestamp': 1439816449,
        },
        'params': {
            'skip_download': True,
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
            'upload_date': '20161112',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)$',
            'timestamp': 1478923074,
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
    }, {
        'url': 'https://www.vlive.tv/video/223906',
        'info_dict': {
            'id': '58',
            'title': 'RUN BTS!'
        },
        'playlist_mincount': 120
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        post = self._call_api(
            'post/v1.0/officialVideoPost-%s', video_id,
            'author{nickname},channel{channelCode,channelName},officialVideo{commentCount,exposeStatus,likeCount,playCount,playTime,status,title,type,vodId},playlist{playlistSeq,totalCount,name}')

        playlist_id = str_or_none(try_get(post, lambda x: x['playlist']['playlistSeq']))
        if not self._yes_playlist(playlist_id, video_id):
            video = post['officialVideo']
            return self._get_vlive_info(post, video, video_id)

        playlist_name = str_or_none(try_get(post, lambda x: x['playlist']['name']))
        playlist_count = str_or_none(try_get(post, lambda x: x['playlist']['totalCount']))

        playlist = self._call_api(
            'playlist/v1.0/playlist-%s/posts', playlist_id, 'data', {'limit': playlist_count})

        entries = []
        for video_data in playlist['data']:
            video = video_data.get('officialVideo')
            video_id = str_or_none(video.get('videoSeq'))
            entries.append(self._get_vlive_info(video_data, video, video_id))

        return self.playlist_result(entries, playlist_id, playlist_name)

    def _get_vlive_info(self, post, video, video_id):
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
                'timestamp': int_or_none(video.get('createdAt'), scale=1000),
                'thumbnail': video.get('thumb'),
            }

        video_type = video.get('type')
        if video_type == 'VOD':
            inkey = self._call_api('video/v1.0/vod/%s/inkey', video_id)['inkey']
            vod_id = video['vodId']
            info_dict = merge_dicts(
                get_common_fields(),
                self._extract_video_info(video_id, vod_id, inkey))
            thumbnail = video.get('thumb')
            if thumbnail:
                if not info_dict.get('thumbnails') and info_dict.get('thumbnail'):
                    info_dict['thumbnails'] = [{'url': info_dict.pop('thumbnail')}]
                info_dict.setdefault('thumbnails', []).append({'url': thumbnail, 'preference': 1})
            return info_dict
        elif video_type == 'LIVE':
            status = video.get('status')
            if status == 'ON_AIR':
                stream_url = self._call_api(
                    'old/v3/live/%s/playInfo',
                    video_id)['result']['adaptiveStreamUrl']
                formats = self._extract_m3u8_formats(stream_url, video_id, 'mp4')
                self._sort_formats(formats)
                info = get_common_fields()
                info.update({
                    'title': video['title'],
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


class VLivePostIE(VLiveBaseIE):
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
                    self._FVIDEO_TMPL % 'sosPlayInfo', video_id)['videoUrl']['download']
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
                inkey = self._call_api(self._FVIDEO_TMPL % 'inKey', video_id)['inKey']
                entry = self._extract_video_info(video_id, vod_id, inkey)
            if entry:
                entry['title'] = '%s_part%s' % (title, idx)
                entries.append(entry)
        return self.playlist_result(
            entries, post_id, title, strip_or_none(post.get('plainBody')))


class VLiveChannelIE(VLiveBaseIE):
    IE_NAME = 'vlive:channel'
    _VALID_URL = r'https?://(?:channels\.vlive\.tv|(?:(?:www|m)\.)?vlive\.tv/channel)/(?P<channel_id>[0-9A-Z]+)(?:/board/(?P<posts_id>\d+))?'
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
    }, {
        'url': 'https://www.vlive.tv/channel/FCD4B/board/3546',
        'info_dict': {
            'id': 'FCD4B-3546',
            'title': 'MAMAMOO - Star Board',
        },
        'playlist_mincount': 880
    }]

    def _entries(self, posts_id, board_name):
        if board_name:
            posts_path = 'post/v1.0/board-%s/posts'
            query_add = {'limit': 100, 'sortType': 'LATEST'}
        else:
            posts_path = 'post/v1.0/channel-%s/starPosts'
            query_add = {'limit': 100}

        for page_num in itertools.count(1):
            video_list = self._call_api(
                posts_path, posts_id, 'channel{channelName},contentType,postId,title,url', query_add,
                note=f'Downloading playlist page {page_num}')

            for video in try_get(video_list, lambda x: x['data'], list) or []:
                video_id = str(video.get('postId'))
                video_title = str_or_none(video.get('title'))
                video_url = url_or_none(video.get('url'))
                if not all((video_id, video_title, video_url)) or video.get('contentType') != 'VIDEO':
                    continue
                channel_name = try_get(video, lambda x: x['channel']['channelName'], compat_str)
                yield self.url_result(video_url, VLivePostIE.ie_key(), video_id, video_title, channel=channel_name)

            after = try_get(video_list, lambda x: x['paging']['nextParams']['after'], compat_str)
            if not after:
                break
            query_add['after'] = after

    def _real_extract(self, url):
        channel_id, posts_id = self._match_valid_url(url).groups()

        board_name = None
        if posts_id:
            board = self._call_api(
                'board/v1.0/board-%s', posts_id, 'title,boardType')
            board_name = board.get('title') or 'Unknown'
            if board.get('boardType') not in ('STAR', 'VLIVE_PLUS'):
                raise ExtractorError(f'Board {board_name!r} is not supported', expected=True)

        entries = LazyList(self._entries(posts_id or channel_id, board_name))
        channel_name = entries[0]['channel']

        return self.playlist_result(
            entries,
            f'{channel_id}-{posts_id}' if posts_id else channel_id,
            f'{channel_name} - {board_name}' if channel_name and board_name else channel_name)
