import itertools
import json
import random
import string

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    format_field,
    int_or_none,
    str_or_none,
    traverse_obj,
    try_get,
)


class TrovoBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://(?:www\.)?trovo\.live/'
    _HEADERS = {'Origin': 'https://trovo.live'}

    def _call_api(self, video_id, data):
        if 'persistedQuery' in data.get('extensions', {}):
            url = 'https://gql.trovo.live'
        else:
            url = 'https://api-web.trovo.live/graphql'

        resp = self._download_json(
            url, video_id, data=json.dumps([data]).encode(), headers={'Accept': 'application/json'},
            query={
                'qid': ''.join(random.choices(string.ascii_uppercase + string.digits, k=16)),
            })[0]
        if 'errors' in resp:
            raise ExtractorError(f'Trovo said: {resp["errors"][0]["message"]}')
        return resp['data'][data['operationName']]

    def _extract_streamer_info(self, data):
        streamer_info = data.get('streamerInfo') or {}
        username = streamer_info.get('userName')
        return {
            'uploader': streamer_info.get('nickName'),
            'uploader_id': str_or_none(streamer_info.get('uid')),
            'uploader_url': format_field(username, None, 'https://trovo.live/%s'),
        }


class TrovoIE(TrovoBaseIE):
    _VALID_URL = TrovoBaseIE._VALID_URL_BASE + r'(?:s/)?(?!(?:clip|video)/)(?P<id>(?!s/)[^/?&#]+(?![^#]+[?&]vid=))'
    _TESTS = [{
        'url': 'https://trovo.live/Exsl',
        'only_matching': True,
    }, {
        'url': 'https://trovo.live/s/SkenonSLive/549759191497',
        'only_matching': True,
    }, {
        'url': 'https://trovo.live/s/zijo987/208251706',
        'info_dict': {
            'id': '104125853_104125853_1656439572',
            'ext': 'flv',
            'uploader_url': 'https://trovo.live/zijo987',
            'uploader_id': '104125853',
            'thumbnail': 'https://livecover.trovo.live/screenshot/73846_104125853_104125853-2022-06-29-04-00-22-852x480.jpg',
            'uploader': 'zijo987',
            'title': '💥IGRAMO IGRICE UPADAJTE💥2500/5000 2022-06-28 22:01',
            'live_status': 'is_live',
        },
        'skip': 'May not be live'
    }]

    def _real_extract(self, url):
        username = self._match_id(url)
        live_info = self._call_api(username, data={
            'operationName': 'live_LiveReaderService_GetLiveInfo',
            'variables': {
                'params': {
                    'userName': username,
                },
            },
        })
        if live_info.get('isLive') == 0:
            raise ExtractorError('%s is offline' % username, expected=True)
        program_info = live_info['programInfo']
        program_id = program_info['id']
        title = program_info['title']

        formats = []
        for stream_info in (program_info.get('streamInfo') or []):
            play_url = stream_info.get('playUrl')
            if not play_url:
                continue
            format_id = stream_info.get('desc')
            formats.append({
                'format_id': format_id,
                'height': int_or_none(format_id[:-1]) if format_id else None,
                'url': play_url,
                'tbr': stream_info.get('bitrate'),
                'http_headers': self._HEADERS,
            })

        info = {
            'id': program_id,
            'title': title,
            'formats': formats,
            'thumbnail': program_info.get('coverUrl'),
            'is_live': True,
        }
        info.update(self._extract_streamer_info(live_info))
        return info


class TrovoVodIE(TrovoBaseIE):
    _VALID_URL = TrovoBaseIE._VALID_URL_BASE + r'(?:clip|video|s)/(?:[^/]+/\d+[^#]*[?&]vid=)?(?P<id>(?<!/s/)[^/?&#]+)'
    _TESTS = [{
        'url': 'https://trovo.live/clip/lc-5285890818705062210?ltab=videos',
        'params': {'getcomments': True},
        'info_dict': {
            'id': 'lc-5285890818705062210',
            'ext': 'mp4',
            'title': 'fatal moaning for a super good🤣🤣',
            'uploader': 'OneTappedYou',
            'timestamp': 1621628019,
            'upload_date': '20210521',
            'uploader_id': '100719456',
            'duration': 31,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'comments': 'mincount:1',
            'categories': ['Call of Duty: Mobile'],
            'uploader_url': 'https://trovo.live/OneTappedYou',
            'thumbnail': r're:^https?://.*\.jpg',
        },
    }, {
        'url': 'https://trovo.live/s/SkenonSLive/549759191497?vid=ltv-100829718_100829718_387702301737980280',
        'info_dict': {
            'id': 'ltv-100829718_100829718_387702301737980280',
            'ext': 'mp4',
            'timestamp': 1654909624,
            'thumbnail': 'http://vod.trovo.live/1f09baf0vodtransger1301120758/ef9ea3f0387702301737980280/coverBySnapshot/coverBySnapshot_10_0.jpg',
            'uploader_id': '100829718',
            'uploader': 'SkenonSLive',
            'title': 'Trovo u secanju, uz par modova i muzike :)',
            'uploader_url': 'https://trovo.live/SkenonSLive',
            'duration': 10830,
            'view_count': int,
            'like_count': int,
            'upload_date': '20220611',
            'comment_count': int,
            'categories': ['Minecraft'],
        },
        'skip': 'Not available',
    }, {
        'url': 'https://trovo.live/s/Trovo/549756886599?vid=ltv-100264059_100264059_387702304241698583',
        'info_dict': {
            'id': 'ltv-100264059_100264059_387702304241698583',
            'ext': 'mp4',
            'timestamp': 1661479563,
            'thumbnail': 'http://vod.trovo.live/be5ae591vodtransusw1301120758/cccb9915387702304241698583/coverBySnapshot/coverBySnapshot_10_0.jpg',
            'uploader_id': '100264059',
            'uploader': 'Trovo',
            'title': 'Dev Corner 8/25',
            'uploader_url': 'https://trovo.live/Trovo',
            'duration': 3753,
            'view_count': int,
            'like_count': int,
            'upload_date': '20220826',
            'comment_count': int,
            'categories': ['Talk Shows'],
        },
    }, {
        'url': 'https://trovo.live/video/ltv-100095501_100095501_1609596043',
        'only_matching': True,
    }, {
        'url': 'https://trovo.live/s/SkenonSLive/549759191497?foo=bar&vid=ltv-100829718_100829718_387702301737980280',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        vid = self._match_id(url)

        # NOTE: It is also possible to extract this info from the Nuxt data on the website,
        # however that seems unreliable - sometimes it randomly doesn't return the data,
        # at least when using a non-residential IP.
        resp = self._call_api(vid, data={
            'operationName': 'vod_VodReaderService_BatchGetVodDetailInfo',
            'variables': {
                'params': {
                    'vids': [vid],
                },
            },
            'extensions': {},
        })

        vod_detail_info = traverse_obj(resp, ('VodDetailInfos', vid), expected_type=dict)
        if not vod_detail_info:
            raise ExtractorError('This video not found or not available anymore', expected=True)
        vod_info = vod_detail_info.get('vodInfo')
        title = vod_info.get('title')

        if try_get(vod_info, lambda x: x['playbackRights']['playbackRights'] != 'Normal'):
            playback_rights_setting = vod_info['playbackRights']['playbackRightsSetting']
            if playback_rights_setting == 'SubscriberOnly':
                raise ExtractorError('This video is only available for subscribers', expected=True)
            else:
                raise ExtractorError(f'This video is not available ({playback_rights_setting})', expected=True)

        language = vod_info.get('languageName')
        formats = []
        for play_info in (vod_info.get('playInfos') or []):
            play_url = play_info.get('playUrl')
            if not play_url:
                continue
            format_id = play_info.get('desc')
            formats.append({
                'ext': 'mp4',
                'filesize': int_or_none(play_info.get('fileSize')),
                'format_id': format_id,
                'height': int_or_none(format_id[:-1]) if format_id else None,
                'language': language,
                'protocol': 'm3u8_native',
                'tbr': int_or_none(play_info.get('bitrate')),
                'url': play_url,
                'http_headers': self._HEADERS,
            })

        category = vod_info.get('categoryName')
        get_count = lambda x: int_or_none(vod_info.get(x + 'Num'))

        info = {
            'id': vid,
            'title': title,
            'formats': formats,
            'thumbnail': vod_info.get('coverUrl'),
            'timestamp': int_or_none(vod_info.get('publishTs')),
            'duration': int_or_none(vod_info.get('duration')),
            'view_count': get_count('watch'),
            'like_count': get_count('like'),
            'comment_count': get_count('comment'),
            'categories': [category] if category else None,
            '__post_extractor': self.extract_comments(vid),
        }
        info.update(self._extract_streamer_info(vod_detail_info))
        return info

    def _get_comments(self, vid):
        for page in itertools.count(1):
            comments_json = self._call_api(vid, data={
                'operationName': 'public_CommentProxyService_GetCommentList',
                'variables': {
                    'params': {
                        'appInfo': {
                            'postID': vid,
                        },
                        'preview': {},
                        'pageSize': 99,
                        'page': page,
                    },
                },
                'extensions': {
                    'singleReq': 'true',
                },
            })
            for comment in comments_json['commentList']:
                content = comment.get('content')
                if not content:
                    continue
                author = comment.get('author') or {}
                parent = comment.get('parentID')
                yield {
                    'author': author.get('nickName'),
                    'author_id': str_or_none(author.get('uid')),
                    'id': str_or_none(comment.get('commentID')),
                    'text': content,
                    'timestamp': int_or_none(comment.get('createdAt')),
                    'parent': 'root' if parent == 0 else str_or_none(parent),
                }

            if comments_json['lastPage']:
                break


class TrovoChannelBaseIE(TrovoBaseIE):
    def _entries(self, spacename):
        for page in itertools.count(1):
            vod_json = self._call_api(spacename, data={
                'operationName': self._OPERATION,
                'variables': {
                    'params': {
                        'terminalSpaceID': {
                            'spaceName': spacename,
                        },
                        'currPage': page,
                        'pageSize': 99,
                    },
                },
                'extensions': {
                    'singleReq': 'true',
                },
            })
            vods = vod_json.get('vodInfos', [])
            for vod in vods:
                vid = vod.get('vid')
                room = traverse_obj(vod, ('spaceInfo', 'roomID'))
                yield self.url_result(
                    f'https://trovo.live/s/{spacename}/{room}?vid={vid}',
                    ie=TrovoVodIE.ie_key())
            has_more = vod_json.get('hasMore')
            if not has_more:
                break

    def _real_extract(self, url):
        spacename = self._match_id(url)
        return self.playlist_result(self._entries(spacename), playlist_id=spacename)


class TrovoChannelVodIE(TrovoChannelBaseIE):
    _VALID_URL = r'trovovod:(?P<id>[^\s]+)'
    IE_DESC = 'All VODs of a trovo.live channel; "trovovod:" prefix'

    _TESTS = [{
        'url': 'trovovod:OneTappedYou',
        'playlist_mincount': 24,
        'info_dict': {
            'id': 'OneTappedYou',
        },
    }]

    _OPERATION = 'vod_VodReaderService_GetChannelLtvVideoInfos'


class TrovoChannelClipIE(TrovoChannelBaseIE):
    _VALID_URL = r'trovoclip:(?P<id>[^\s]+)'
    IE_DESC = 'All Clips of a trovo.live channel; "trovoclip:" prefix'

    _TESTS = [{
        'url': 'trovoclip:OneTappedYou',
        'playlist_mincount': 29,
        'info_dict': {
            'id': 'OneTappedYou',
        },
    }]

    _OPERATION = 'vod_VodReaderService_GetChannelClipVideoInfos'
