import itertools
import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    format_field,
    make_archive_id,
    parse_iso8601,
    remove_start,
    smuggle_url,
    traverse_obj,
    unsmuggle_url,
)

_BASE_URL_RE = r'https?://(?:www\.|beta\.)?(?:watchnebula\.com|nebula\.app|nebula\.tv)'


class NebulaBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'watchnebula'
    _token = _api_token = None

    def _perform_login(self, username, password):
        try:
            response = self._download_json(
                'https://api.watchnebula.com/api/v1/auth/login/', None,
                'Logging in to Nebula', 'Login failed',
                data=json.dumps({'email': username, 'password': password}).encode(),
                headers={
                    'content-type': 'application/json',
                    'cookie': ''  # 'sessionid' cookie causes 403
                })
        except ExtractorError as e:
            if isinstance(e.cause, urllib.error.HTTPError) and e.cause.code == 400:
                raise ExtractorError('Login failed: Invalid username or password', expected=True)
            raise
        self._api_token = response.get('key')
        if not self._api_token:
            raise ExtractorError('Login failed: No token')

    def _call_api(self, *args, **kwargs):
        if self._token:
            kwargs.setdefault('headers', {})['Authorization'] = f'Bearer {self._token}'
        try:
            return self._download_json(*args, **kwargs)
        except ExtractorError as exc:
            if not isinstance(exc.cause, urllib.error.HTTPError) or exc.cause.code not in (401, 403):
                raise
            username, password = self._get_login_info()
            if not username:
                self.raise_login_required(method='password')

            self.to_screen(f'Reauthenticating to Nebula and retrying, '
                           f'because last API call resulted in error {exc.cause.code}')
            self._perform_login(username, password)
            self._real_initialize()
            return self._download_json(*args, **kwargs)

    def _real_initialize(self):
        self._token = self._download_json(
            'https://api.watchnebula.com/api/v1/authorization/', None,
            headers={'Authorization': f'Token {self._api_token}'} if self._api_token else None,
            note='Authorizing to Nebula', data=b'')['token']

    def _extract_formats(self, slug):
        stream_info = self._call_api(
            f'https://content.watchnebula.com/video/{slug}/stream/',
            slug, note='Fetching video stream info')
        fmts, subs = self._extract_m3u8_formats_and_subtitles(stream_info['manifest'], slug, 'mp4')
        return {'formats': fmts, 'subtitles': subs}

    def _extract_video_metadata(self, episode):
        channel_url = format_field(episode, 'channel_slug', 'https://nebula.app/%s')
        return {
            'id': remove_start(episode['id'], 'video_episode:'),
            **traverse_obj(episode, {
                'display_id': 'slug',
                'title': 'title',
                'description': 'description',
                'timestamp': ('published_at', {parse_iso8601}),
                'duration': 'duration',
                'channel_id': 'channel_slug',
                'uploader_id': 'channel_slug',
                'channel': 'channel_title',
                'uploader': 'channel_title',
                'series': 'channel_title',
                'creator': 'channel_title',
                '_old_archive_ids': ('zype_id', {lambda x: [make_archive_id(NebulaIE, x)]}),
            }),
            'channel_url': channel_url,
            'uploader_url': channel_url,
            'thumbnails': [{
                # 'id': tn.get('name'),  # this appears to be null
                'url': tn['original'],
                'height': key,
            } for key, tn in traverse_obj(episode, ('assets', 'thumbnail'), default={}).items()],
        }


class NebulaIE(NebulaBaseIE):
    _VALID_URL = rf'{_BASE_URL_RE}/videos/(?P<id>[-\w]+)'
    _TESTS = [
        {
            'url': 'https://nebula.tv/videos/that-time-disney-remade-beauty-and-the-beast',
            'info_dict': {
                'id': '84ed544d-4afd-4723-8cd5-2b95261f0abf',
                'ext': 'mp4',
                'title': 'That Time Disney Remade Beauty and the Beast',
                'description': 'md5:2aae3c4cfc5ee09a1ecdff0909618cf4',
                'upload_date': '20180731',
                'timestamp': 1533009600,
                'channel': 'Lindsay Ellis',
                'channel_id': 'lindsayellis',
                'uploader': 'Lindsay Ellis',
                'uploader_id': 'lindsayellis',
                'uploader_url': r're:https://nebula\.(tv|app)/lindsayellis',
                'series': 'Lindsay Ellis',
                'display_id': 'that-time-disney-remade-beauty-and-the-beast',
                'channel_url': r're:https://nebula\.(tv|app)/lindsayellis',
                'creator': 'Lindsay Ellis',
                'duration': 2212,
                'thumbnail': r're:https://\w+\.cloudfront\.net/[\w-]+\.jpeg?.*',
            },
            'params': {'skip_download': 'm3u8'},
        },
        {
            'url': 'https://nebula.tv/videos/the-logistics-of-d-day-landing-craft-how-the-allies-got-ashore',
            'md5': 'd05739cf6c38c09322422f696b569c23',
            'info_dict': {
                'id': '7e623145-1b44-4ca3-aa0b-ed25a247ea34',
                'ext': 'mp4',
                'title': 'Landing Craft - How The Allies Got Ashore',
                'description': r're:^In this episode we explore the unsung heroes of D-Day, the landing craft.',
                'upload_date': '20200327',
                'timestamp': 1585348140,
                'channel': 'Real Engineering — The Logistics of D-Day',
                'channel_id': 'd-day',
                'uploader': 'Real Engineering — The Logistics of D-Day',
                'uploader_id': 'd-day',
                'series': 'Real Engineering — The Logistics of D-Day',
                'display_id': 'the-logistics-of-d-day-landing-craft-how-the-allies-got-ashore',
                'creator': 'Real Engineering — The Logistics of D-Day',
                'duration': 841,
                'channel_url': 'https://nebula.tv/d-day',
                'uploader_url': 'https://nebula.tv/d-day',
                'thumbnail': r're:https://\w+\.cloudfront\.net/[\w-]+\.jpeg?.*',
            },
        },
        {
            'url': 'https://nebula.tv/videos/money-episode-1-the-draw',
            'md5': 'ebe28a7ad822b9ee172387d860487868',
            'info_dict': {
                'id': 'b96c5714-9e2b-4ec3-b3f1-20f6e89cc553',
                'ext': 'mp4',
                'title': 'Episode 1: The Draw',
                'description': r'contains:There’s free money on offer… if the players can all work together.',
                'upload_date': '20200323',
                'timestamp': 1584980400,
                'channel': 'Tom Scott Presents: Money',
                'channel_id': 'tom-scott-presents-money',
                'uploader': 'Tom Scott Presents: Money',
                'uploader_id': 'tom-scott-presents-money',
                'uploader_url': 'https://nebula.tv/tom-scott-presents-money',
                'duration': 825,
                'channel_url': 'https://nebula.tv/tom-scott-presents-money',
                'series': 'Tom Scott Presents: Money',
                'display_id': 'money-episode-1-the-draw',
                'thumbnail': r're:https://\w+\.cloudfront\.net/[\w-]+\.jpeg?.*',
                'creator': 'Tom Scott Presents: Money',
            },
        },
        {
            'url': 'https://watchnebula.com/videos/money-episode-1-the-draw',
            'only_matching': True,
        }, {
            'url': 'https://nebula.tv/videos/tldrnewseu-did-the-us-really-blow-up-the-nordstream-pipelines',
            'info_dict': {
                'id': 'e389af9d-1dab-44f2-8788-ee24deb7ff0d',
                'ext': 'mp4',
                'display_id': 'tldrnewseu-did-the-us-really-blow-up-the-nordstream-pipelines',
                'title': 'Did the US Really Blow Up the NordStream Pipelines?',
                'description': 'md5:b4e2a14e3ff08f546a3209c75261e789',
                'upload_date': '20230223',
                'timestamp': 1677144070,
                'channel': 'TLDR News EU',
                'channel_id': 'tldrnewseu',
                'uploader': 'TLDR News EU',
                'uploader_id': 'tldrnewseu',
                'uploader_url': r're:https://nebula\.(tv|app)/tldrnewseu',
                'duration': 524,
                'channel_url': r're:https://nebula\.(tv|app)/tldrnewseu',
                'series': 'TLDR News EU',
                'thumbnail': r're:https?://.*\.jpeg',
                'creator': 'TLDR News EU',
                '_old_archive_ids': ['nebula 63f64c74366fcd00017c1513'],
            },
            'params': {'skip_download': 'm3u8'},
        },
        {
            'url': 'https://beta.nebula.tv/videos/money-episode-1-the-draw',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        slug = self._match_id(url)
        url, smuggled_data = unsmuggle_url(url, {})
        if smuggled_data.get('id'):
            return {
                'id': smuggled_data['id'],
                'display_id': slug,
                'title': '',
                **self._extract_formats(slug),
            }

        return {
            **self._extract_video_metadata(self._call_api(
                f'https://content.watchnebula.com/video/{slug}/',
                slug, note='Fetching video metadata')),
            **self._extract_formats(slug),
        }


class NebulaSubscriptionsIE(NebulaBaseIE):
    IE_NAME = 'nebula:subscriptions'
    _VALID_URL = rf'{_BASE_URL_RE}/(?P<id>myshows)'
    _TESTS = [
        {
            'url': 'https://nebula.tv/myshows',
            'playlist_mincount': 1,
            'info_dict': {
                'id': 'myshows',
            },
        },
    ]

    def _generate_playlist_entries(self):
        next_url = 'https://content.watchnebula.com/library/video/?page_size=100'
        for page_num in itertools.count(1):
            channel = self._call_api(
                next_url, 'myshows', note=f'Retrieving subscriptions page {page_num}')
            for episode in channel['results']:
                metadata = self._extract_video_metadata(episode)
                yield self.url_result(smuggle_url(
                    f'https://nebula.tv/videos/{metadata["display_id"]}',
                    {'id': metadata['id']}), NebulaIE, url_transparent=True, **metadata)
            next_url = channel.get('next')
            if not next_url:
                return

    def _real_extract(self, url):
        return self.playlist_result(self._generate_playlist_entries(), 'myshows')


class NebulaChannelIE(NebulaBaseIE):
    IE_NAME = 'nebula:channel'
    _VALID_URL = rf'{_BASE_URL_RE}/(?!myshows|videos/)(?P<id>[-\w]+)'
    _TESTS = [
        {
            'url': 'https://nebula.tv/tom-scott-presents-money',
            'info_dict': {
                'id': 'tom-scott-presents-money',
                'title': 'Tom Scott Presents: Money',
                'description': 'Tom Scott hosts a series all about trust, negotiation and money.',
            },
            'playlist_count': 5,
        }, {
            'url': 'https://nebula.tv/lindsayellis',
            'info_dict': {
                'id': 'lindsayellis',
                'title': 'Lindsay Ellis',
                'description': 'Enjoy these hottest of takes on Disney, Transformers, and Musicals.',
            },
            'playlist_mincount': 2,
        }, {
            'url': 'https://nebula.tv/johnnyharris',
            'info_dict': {
                'id': 'johnnyharris',
                'title': 'Johnny Harris',
                'description': 'I make videos about maps and many other things.',
            },
            'playlist_mincount': 90,
        },
    ]

    def _generate_playlist_entries(self, collection_id, channel):
        for page_num in itertools.count(2):
            for episode in channel['episodes']['results']:
                metadata = self._extract_video_metadata(episode)
                yield self.url_result(smuggle_url(
                    episode.get('share_url') or f'https://nebula.tv/videos/{metadata["display_id"]}',
                    {'id': metadata['id']}), NebulaIE, url_transparent=True, **metadata)
            next_url = channel['episodes'].get('next')
            if not next_url:
                break
            channel = self._call_api(next_url, collection_id, note=f'Retrieving channel page {page_num}')

    def _real_extract(self, url):
        collection_id = self._match_id(url)
        channel = self._call_api(
            f'https://content.watchnebula.com/video/channels/{collection_id}/',
            collection_id, note='Retrieving channel')

        return self.playlist_result(
            entries=self._generate_playlist_entries(collection_id, channel),
            playlist_id=collection_id,
            playlist_title=traverse_obj(channel, ('details', 'title')),
            playlist_description=traverse_obj(channel, ('details', 'description')))
