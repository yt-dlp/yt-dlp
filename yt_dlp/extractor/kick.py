import functools
import itertools
import json
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    UserNotLive,
    clean_html,
    determine_ext,
    int_or_none,
    join_nonempty,
    parse_iso8601,
    parse_qs,
    parse_resolution,
    smuggle_url,
    str_or_none,
    unified_timestamp,
    unsmuggle_url,
    url_basename,
    url_or_none,
)
from ..utils.traversal import require, traverse_obj


class KickBaseIE(InfoExtractor):
    _BASE_URL = 'https://kick.com'

    @functools.cached_property
    def _api_headers(self):
        cookies = self._get_cookies(self._BASE_URL)
        token = traverse_obj(cookies, (
            'session_token', 'value', {urllib.parse.unquote}))
        return {'Authorization': f'Bearer {token}'} if token else {}

    def _call_api(self, path, display_id, note='Downloading API JSON', headers={}, **kwargs):
        api_domain = {
            'v1': 'web.kick.com',
            'v2': 'kick.com',
        }[path.partition('/')[0]]

        return self._download_json(
            f'https://{api_domain}/api/{path}', display_id, note=note,
            headers={**self._api_headers, **headers}, impersonate=True, **kwargs)

    def _get_creator_info(self, channel_id):
        channel_data = self._call_api(
            f'v2/channels/{channel_id}', channel_id, note='Downloading creator info')
        creator_id = traverse_obj(channel_data, (
            'id', {int}, {str_or_none}, {require('creator ID')}))
        username = traverse_obj(channel_data, ('user', 'username', {str}, filter))

        return creator_id, username


class KickIE(KickBaseIE):
    IE_NAME = 'kick:live'

    _VALID_URL = r'https?://(?:www\.)?kick\.com/(?!(?:video|categories|search|auth)(?:[/?#]|$))(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://kick.com/xqc',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if (
            KickVODIE.suitable(url)
            or KickClipIE.suitable(url)
            or KickVideosIE.suitable(url)
            or KickClipsIE.suitable(url)
        ) else super().suitable(url)

    def _real_extract(self, url):
        channel_id = self._match_id(url).lower()
        channel_data = self._call_api(f'v2/channels/{channel_id}', channel_id)
        if not traverse_obj(channel_data, ('livestream', {dict})):
            raise UserNotLive(video_id=channel_id)

        m3u8_url = traverse_obj(channel_data, (
            'playback_url', {url_or_none}, {require('m3u8 URL')}))

        return {
            'channel_id': channel_id,
            'formats': self._extract_m3u8_formats(m3u8_url, channel_id, 'mp4'),
            'is_live': True,
            **traverse_obj(channel_data, {
                'channel_follower_count': ('followers_count', {int_or_none}),
                'channel_is_verified': ('verified', {bool}),
                'uploader_id': ('slug', {str}, filter),
            }),
            **traverse_obj(channel_data, ('livestream', {
                'id': ('id', {str_or_none}),
                'title': ('session_title', {clean_html}, filter),
                'age_limit': ('is_mature', {bool}, {lambda x: 18 if x else None}),
                'categories': ('categories', ..., 'name', {clean_html}, filter, all, filter),
                'concurrent_view_count': ('viewer_count', {int_or_none}),
                'release_timestamp': ('start_time', {unified_timestamp}),
                'tags': ('tags', ..., {clean_html}, filter, all, filter),
                'thumbnail': ('thumbnail', 'url', {url_or_none}),
                'timestamp': ('created_at', {unified_timestamp}),
            })),
            **traverse_obj(channel_data, ('user', {
                'channel': ('username', {str}, filter),
                'description': ('bio', {clean_html}, filter),
                'uploader': ('username', {str}, filter),
            })),
        }


class KickVODIE(KickBaseIE):
    IE_NAME = 'kick:vod'

    _VALID_URL = r'https?://(?:www\.)?kick\.com/[\w-]+/videos/(?P<id>[\da-f]{8}-(?:[\da-f]{4}-){3}[\da-f]{12})'
    _TESTS = [{
        'url': 'https://kick.com/xqc/videos/019f77a6-ec40-7e2d-b1fc-575b6801b20d',
        'info_dict': {
            'id': '019f77a6-ec40-7e2d-b1fc-575b6801b20d',
            'ext': 'mp4',
            'title': 'md5:adc68f02c1f0b6cd9315831850e19d36',
            'age_limit': 18,
            'availability': 'public',
            'categories': ['Just Chatting'],
            'channel': 'xQc',
            'channel_id': 'xqc',
            'duration': 38674,
            'thumbnail': r're:https?://.+',
            'timestamp': 1784418856,
            'upload_date': '20260718',
            'uploader': 'xQc',
            'uploader_id': 'xqc',
            'view_count': int,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # Ongoing livestream VOD
        'url': 'https://kick.com/a-log-burner/videos/019f9c52-2528-75fd-a634-199577affa36',
        'info_dict': {
            'id': '019f9c52-2528-75fd-a634-199577affa36',
            'ext': 'mp4',
            'title': str,
            'availability': 'public',
            'categories': ['Meditation & Mindfulness'],
            'channel': 'A_Log_Burner',
            'channel_id': 'a-log-burner',
            'live_status': 'is_live',
            'tags': 'count:9',
            'thumbnail': r're:https?://.+',
            'timestamp': 1785034057,
            'upload_date': '20260726',
            'uploader': 'A_Log_Burner',
            'uploader_id': 'a-log-burner',
            'view_count': int,
        },
        'skip': 'Livestream',
    }]

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        video_id = self._match_id(url)
        playback = self._call_api(
            f'v1/stream/{video_id}/playback', video_id, headers={
                'Content-Type': 'application/json',
            }, data=json.dumps({
                'video_player': {'player': {}},
                'video_session': {},
                'user_session': {
                    'non_personalised_ads': True,
                },
            }).encode(), expected_status=404)
        if data := traverse_obj(playback, ('data', {dict})):
            err_msg = join_nonempty('type', 'details', delim=': ', from_dict=data)
            raise ExtractorError(
                err_msg or 'API returned an error response', expected=True)

        video_data = traverse_obj(smuggled_data, ('video_data', {dict}))
        if not video_data:
            creator_id = traverse_obj(playback, (
                'video_session', 'creator_id', {str}, {require('creator ID')}))
            videos = self._call_api(f'v1/channels/{creator_id}/videos', creator_id)
            video_data = traverse_obj(videos, (
                'data', lambda _, v: v['id'] == video_id, {dict}, any))

        vod_session_url = traverse_obj(playback, (
            'playback_url', 'vod_session', {url_or_none}, {require('vod session URL')}))
        vod_session = self._download_json(vod_session_url, video_id)
        m3u8_url = traverse_obj(vod_session, (
            'manifestUrl', {url_or_none}, {require('m3u8 URL')}))

        return {
            'id': video_id,
            'availability': {
                'sub_only': 'subscriber_only',
                'private': 'private',
                'public': 'public',
            }.get(traverse_obj(video_data, ('status', {str}))),
            'formats': self._extract_m3u8_formats(m3u8_url, video_id, 'mp4'),
            **traverse_obj(video_data, {
                'title': ('title', {clean_html}, filter),
                'age_limit': ('is_mature', {bool}, {lambda x: 18 if x else None}),
                'categories': ('category', 'name', {clean_html}, filter, all, filter),
                'duration': ('duration', {int_or_none}),
                'is_live': ('is_live', {bool}),
                'tags': ('tags', ..., {clean_html}, filter, all, filter),
                'thumbnails': (
                    'thumbnail', 'srcSet', {lambda x: x.split(',')}, ..., {str.strip},
                    {lambda x: x.rsplit(maxsplit=1)}, {
                        'url': (0, {url_or_none}),
                        'width': (1, {parse_resolution(lenient=True)}, 'width'),
                        'height': (0, {url_basename}, {lambda x: int_or_none(x.partition('.')[0])}),
                    },
                ),
                'timestamp': ('start_time', {parse_iso8601}),
                'view_count': ('viewer_count', {int_or_none}),
            }),
            **traverse_obj(video_data, ('channel', {
                'channel': ('username', {str}, filter),
                'channel_id': ('slug', {str}, filter),
                'uploader': ('username', {str}, filter),
                'uploader_id': ('slug', {str}, filter),
            })),
        }


class KickClipIE(KickBaseIE):
    IE_NAME = 'kick:clip'

    _VALID_URL = r'https?://(?:www\.)?kick\.com/[\w-]+(?:/clips/|/?\?(?:[^#]+&)?clip=)(?P<id>clip_[\w-]+)'
    _TESTS = [{
        'url': 'https://kick.com/mxddy?clip=clip_01GYXVB5Y8PWAPWCWMSBCFB05X',
        'md5': 'a1014e8a26b6f45bc64bcef679dd19a7',
        'info_dict': {
            'id': 'clip_01GYXVB5Y8PWAPWCWMSBCFB05X',
            'ext': 'mp4',
            'title': 'Maddy detains Abd D:',
            'channel': 'Mxddy',
            'channel_id': 'mxddy',
            'uploader': 'Mxddy',
            'uploader_id': 'mxddy',
            'thumbnail': r're:https?://.+',
            'duration': 35,
            'timestamp': 1682481453,
            'upload_date': '20230426',
            'view_count': int,
            'like_count': int,
            'categories': ['VALORANT'],
            'age_limit': 18,
        },
    }, {
        'url': 'https://kick.com/destiny?clip=clip_01H9SKET879NE7N9RJRRDS98J3',
        'info_dict': {
            'id': 'clip_01H9SKET879NE7N9RJRRDS98J3',
            'title': 'W jews',
            'ext': 'mp4',
            'channel': 'Destiny',
            'channel_id': 'destiny',
            'uploader': 'Destiny',
            'uploader_id': 'destiny',
            'duration': 49,
            'upload_date': '20230908',
            'timestamp': 1694150180,
            'thumbnail': r're:https?://.+',
            'view_count': int,
            'like_count': int,
            'categories': ['Just Chatting'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://kick.com/spreen/clips/clip_01J8RGZRKHXHXXKJEHGRM932A5',
        'info_dict': {
            'id': 'clip_01J8RGZRKHXHXXKJEHGRM932A5',
            'ext': 'mp4',
            'title': 'KLJASLDJKLJKASDLJKDAS',
            'channel': 'Spreen',
            'channel_id': 'spreen',
            'uploader': 'Spreen',
            'uploader_id': 'spreen',
            'duration': 43,
            'upload_date': '20240927',
            'timestamp': 1727399987,
            'thumbnail': r're:https?://.+',
            'view_count': int,
            'like_count': int,
            'categories': ['Just Chatting'],
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        clip_id = self._match_id(url)

        clip_data = traverse_obj(smuggled_data, ('clip_data', {dict}))
        if not clip_data:
            clip = self._call_api(f'v2/clips/{clip_id}', clip_id)
            clip_data = traverse_obj(clip, ('clip', {dict}))

        clip_url = traverse_obj(clip_data, (
            ('playback_url', 'clip_url', 'video_url'),
            {url_or_none}, any, {require('clip source URL')}))
        if determine_ext(clip_url) == 'm3u8':
            formats = self._extract_m3u8_formats(clip_url, clip_id, 'mp4')
        else:
            formats = [{'url': clip_url}]

        return {
            'id': clip_id,
            'formats': formats,
            **traverse_obj(clip_data, {
                'title': ('title', {clean_html}, filter),
                'age_limit': ('is_mature', {bool}, {lambda x: 18 if x else None}),
                'categories': ('category', 'name', {clean_html}, filter, all, filter),
                'duration': ('duration', {int_or_none}),
                'like_count': (('likes_count', 'likes'), {int_or_none}, any),
                'thumbnail': ('thumbnail_url', {url_or_none}),
                'timestamp': ('created_at', {parse_iso8601}),
                'view_count': (('views_count', 'view_count', 'views'), {int_or_none}, any),
            }),
            **traverse_obj(clip_data, ('channel', {
                'channel': ('username', {str}, filter),
                'channel_id': ('slug', {str}, filter),
                'uploader': ('username', {str}, filter),
                'uploader_id': ('slug', {str}, filter),
            })),
        }


class KickVideosIE(KickBaseIE):
    IE_NAME = 'kick:videos'

    _VALID_URL = r'https?://(?:www\.)?kick\.com/(?P<id>[\w-]+)/videos/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://kick.com/xqc/videos',
        'info_dict': {
            'id': 'xqc',
            'title': 'xQc - Videos sorted by Date',
        },
        'playlist_mincount': 10,
    }, {
        'url': 'https://kick.com/xqc/videos?sort=views',
        'info_dict': {
            'id': 'xqc',
            'title': 'xQc - Videos sorted by Views',
        },
        'playlist_mincount': 10,
    }]

    def _entries(self, creator_id, channel_id, sort_param):
        videos = self._call_api(f'v1/channels/{creator_id}/videos', channel_id)
        if sort_param == 'views':
            videos['data'].sort(key=lambda v: v['viewer_count'], reverse=True)

        for video_data in traverse_obj(videos, (
            'data', lambda _, v: str_or_none(v['id']),
        )):
            video_id = video_data['id']

            yield self.url_result(smuggle_url(
                f'{self._BASE_URL}/{channel_id}/videos/{video_id}',
                {'video_data': video_data},
            ), KickVODIE, video_id)

    def _real_extract(self, url):
        channel_id = self._match_id(url).lower()
        creator_id, username = self._get_creator_info(channel_id)

        sort_param = traverse_obj(parse_qs(url), ('sort', -1, {str}, filter))
        sort_label = 'Views' if sort_param == 'views' else 'Date'

        return self.playlist_result(
            self._entries(creator_id, channel_id, sort_param), channel_id,
            f'{username or channel_id} - Videos sorted by {sort_label}')


class KickClipsIE(KickBaseIE):
    IE_NAME = 'kick:clips'

    _VALID_URL = r'https?://(?:www\.)?kick\.com/(?P<id>[\w-]+)/clips/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://kick.com/xqc/clips',
        'info_dict': {
            'id': 'xqc',
            'title': 'xQc - Clips sorted by Views (Last Week)',
        },
        'playlist_mincount': 100,
    }, {
        'url': 'https://kick.com/xqc/clips?sort=date&range=day',
        'info_dict': {
            'id': 'xqc',
            'title': 'xQc - Clips sorted by Date (Last Day)',
        },
        'playlist_mincount': 10,
    }]

    def _entries(self, creator_id, channel_id, sort_param, range_param):
        query = {
            'sort': 'views' if sort_param == 'view' else 'date',
            'time': range_param,
        }
        for page in itertools.count(1):
            clips = self._call_api(
                f'v1/channels/{creator_id}/clips', channel_id,
                note=f'Downloading page {page}', query=query)

            for clip_data in traverse_obj(clips, (
                'data', 'clips', lambda _, v: str_or_none(v['id']),
            )):
                clip_id = clip_data['id']

                yield self.url_result(smuggle_url(
                    f'{self._BASE_URL}/{channel_id}/clips/{clip_id}',
                    {'clip_data': clip_data},
                ), KickClipIE, clip_id)

            cursor = traverse_obj(clips, ('data', 'cursor', {str}, filter))
            if not cursor:
                break
            query['cursor'] = cursor

    def _real_extract(self, url):
        channel_id = self._match_id(url).lower()
        creator_id, username = self._get_creator_info(channel_id)

        query = parse_qs(url)
        sort_param = traverse_obj(query, ('sort', -1, {str}, filter))
        if sort_param not in ('view', 'date'):
            sort_param = 'view'
        range_param = traverse_obj(query, ('range', -1, {str}, filter))
        if range_param not in ('day', 'week', 'month', 'all'):
            range_param = 'week'

        sort_label = 'Views' if sort_param == 'view' else 'Date'
        range_label = {
            'day': 'Last Day',
            'month': 'Last Month',
            'all': 'All Time',
        }.get(range_param, 'Last Week')

        return self.playlist_result(
            self._entries(creator_id, channel_id, sort_param, range_param), channel_id,
            f'{username or channel_id} - Clips sorted by {sort_label} ({range_label})')
