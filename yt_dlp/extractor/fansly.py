import json
import re

from .common import InfoExtractor
from ..utils import ExtractorError
from ..utils.traversal import traverse_obj


class FanslyLiveIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?fansly\.com/live/(?P<id>[0-9a-zA-Z_]+)'
    _TESTS = [{
        'url': 'https://fansly.com/live/YuukoVT',
        'info_dict': {
            'channel_id': '713619348626874370',
            'ext': 'mp4',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Channel is not live',
    }, {
        'url': 'https://fansly.com/live/284824898138812416',
        'info_dict': {
            'id': '563252644517257217',
            'channel_id': '284824898138812416',
            'ext': 'mp4',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Channel is not live',
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        if not video_id.isdigit():
            # get the channel ID from the API
            user = self._download_json(
                f'https://apiv3.fansly.com/api/v1/account?usernames={video_id}&ngsw-bypass=true',
                video_id)
            if not user.get('success') or len(user.get('response')) == 0:
                raise ExtractorError('Failed to get channel ID')
            video_id = user.get('response')[0].get('id')

        channel = self._download_json(f'https://apiv3.fansly.com/api/v1/streaming/channel/{video_id}?ngsw-bypass=true', video_id)
        if not user.get('success') or not user.get('response'):
            raise ExtractorError('Failed to get channel info')  # TODO: is there an error message returned?
        stream = traverse_obj(channel, ('response', 'stream'))
        if not stream.get('access') or not stream.get('playbackUrl'):
            raise ExtractorError('Channel is not live', expected=True)

        return {
            'id': stream.get('id'),
            'title': stream.get('title'),
            'formats': self._extract_m3u8_formats(stream.get('playbackUrl'), video_id, ext='mp4', live=True),
            'timestamp': stream.get('startedAt'),
            'modified_timestamp': stream.get('updatedAt'),
            'channel_id': stream.get('accountId'),
            'concurrent_view_count': stream.get('viewerCount'),
            'age_limit': 18,
            'is_live': True,
        }


class FanslyIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?fansly\.com/post/(?P<id>[0-9]+)'
    _NETRC_MACHINE = 'fansly'
    _TESTS = [{
        'url': 'https://fansly.com/post/713619348626874370',
        'info_dict': {
            'id': '713619348626874370',
            'ext': 'mp4',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _initialize_pre_login(self):
        self._auth_headers = {}

    def _perform_login(self, username, password):
        devid = self._download_json('https://apiv3.fansly.com/api/v1/device/id?ngsw-bypass=true', None, impersonate=True).get('response')
        res = self._download_json('https://apiv3.fansly.com/api/v1/login?ngsw-bypass=true', None, impersonate=True, data=json.dumps({
            'deviceId': devid,
            'username': username,
            'password': password,
        }).encode())
        if traverse_obj(res, ('response', 'twofa')):
            token = traverse_obj(res, ('response', 'twofa', 'token'))
            code = self._get_tfa_info(f'two-factor verification code sent to {traverse_obj(res, ("response", "twofa", "email"))}')
            tfa_res = self._download_json('https://apiv3.fansly.com/api/v1/login/twofa?ngsw-bypass=true', None, impersonate=True, data=json.dumps({
                'token': token,
                'code': code,
            }).encode())
            self._auth_headers = {'Authorization': traverse_obj(tfa_res, ('response', 'token'))}
        else:
            self._auth_headers = {'Authorization': traverse_obj(res, ('response', 'session', 'token'))}

    def _real_extract(self, url):
        video_id = self._match_id(url)
        res = self._download_json(
            f'https://apiv3.fansly.com/api/v1/post?ids={video_id}&ngsw-bypass=true',
            video_id, impersonate=True, headers=self._auth_headers)
        if not res.get('success') or not res.get('response'):
            raise ExtractorError('Failed to get post info')  # TODO: is there an error message returned?
        try:
            post = traverse_obj(res, ('response', 'posts'))[0]
        except IndexError:
            raise ExtractorError('Could not find post')
        try:
            account = traverse_obj(res, ('response', 'accounts'))[0]
        except IndexError:
            raise ExtractorError('Could not find account info for post')

        playlist = []
        for media in traverse_obj(res, ('response', 'accountMedia', lambda _, v: v['media'])):
            thumbnail = None
            m = media['media']
            metadata = json.loads(m.get('metadata'))

            try:
                formats = [{
                    'url': m.get('locations')[0].get('location'),
                    'format_id': str(m.get('type')),
                    'width': m.get('width'),
                    'height': m.get('height'),
                    'fps': metadata.get('frameRate'),
                    'http_headers': {
                        'Cookie': '; '.join(['CloudFront-' + k + '=' + v for k, v in m.get('locations')[0].get('metadata').items()]),
                    } if m.get('locations')[0].get('metadata') else {},
                }]
                for variant in traverse_obj(m, ('variants', lambda _, v: v['mimetype'] and v['locations'])):
                    mimetype = variant.get('mimetype')
                    try:
                        location = variant['locations'][0]
                    except IndexError:
                        self.report_warning(f'Could not get variant location for ID {variant.get("id")}, skipping (you may need to log in)', video_id)
                        continue
                    headers = {
                        'Cookie': '; '.join(['CloudFront-' + k + '=' + v for k, v in location.get('metadata').items()]),
                    } if location.get('metadata') else {}
                    if mimetype == 'application/vnd.apple.mpegurl':
                        f = self._extract_m3u8_formats(location.get('location'), video_id, ext='mp4', headers=headers)
                        for fmt in f:
                            fmt['http_headers'] = headers
                        formats.extend(f)
                    elif mimetype == 'application/dash+xml':
                        f = self._extract_mpd_formats(location.get('location'), video_id, headers=headers)
                        for fmt in f:
                            fmt['http_headers'] = headers
                        formats.extend(f)
                    else:
                        vmetadata = json.loads(variant.get('metadata'))
                        formats.append({
                            'url': location.get('location'),
                            'format_id': str(variant.get('type')),
                            'width': variant.get('width'),
                            'height': variant.get('height'),
                            'fps': vmetadata.get('frameRate') or metadata.get('frameRate'),
                            'http_headers': headers,
                        })
                    if mimetype == 'image/jpeg' and thumbnail is None:  # TODO: this assumes the first is highest res - is this important and/or reliable?
                        thumbnail = location.get('location')
            except IndexError:
                self.report_warning(f'Could not get media locations for ID {m.get("id")}. You may need to authenticate with --username and --password.', video_id)
                formats = []

            if any(v.get('price') > 0 or (v.get('metadata') != '' and v.get('metadata') != '{}') for v in traverse_obj(media, ('permissions', 'permissionFlags')) or []):
                availability = 'premium_only'
            elif len(formats) == 0:
                availability = 'needs_auth'
            else:
                availability = 'public'

            playlist.append({
                'id': media.get('mediaId'),
                'title': '',
                'formats': formats,
                'thumbnail': thumbnail,
                'uploader': account.get('username'),
                'timestamp': m.get('createdAt'),
                'release_timestamp': media.get('createdAt'),
                'modified_timestamp': m.get('updatedAt'),
                'uploader_id': post.get('accountId'),
                'uploader_url': 'https://fansly.com/' + account.get('username'),
                'channel_id': post.get('accountId'),
                'channel_url': 'https://fansly.com/' + account.get('username'),
                'channel_follower_count': account.get('followCount'),
                'channel_is_verified': True,  # TODO: this is probably true for all accounts that are able to post? or maybe it's a flag
                'location': account.get('location'),
                'duration': metadata.get('duration'),
                'like_count': media.get('likeCount'),
                'comment_count': post.get('replyCount') or 0,
                'age_limit': 18,
                'tags': re.findall(r'#[^ ]+', post.get('content') or ''),
                'is_live': False,
                'availability': availability,
            })

        return self.playlist_result(playlist, video_id, playlist_description=post.get('content'))
