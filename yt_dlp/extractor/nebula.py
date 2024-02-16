import itertools
import json

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    int_or_none,
    make_archive_id,
    parse_iso8601,
    smuggle_url,
    try_call,
    unsmuggle_url,
    update_url_query,
    url_or_none,
    urljoin,
)
from ..utils.traversal import traverse_obj

_BASE_URL_RE = r'https?://(?:www\.|beta\.)?(?:watchnebula\.com|nebula\.app|nebula\.tv)'


class NebulaBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'watchnebula'
    _token = _api_token = None

    def _perform_login(self, username, password):
        try:
            response = self._download_json(
                'https://nebula.tv/auth/login/', None,
                'Logging in to Nebula', 'Login failed',
                data=json.dumps({'email': username, 'password': password}).encode(),
                headers={'content-type': 'application/json'})
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 400:
                raise ExtractorError('Login failed: Invalid username or password', expected=True)
            raise
        self._api_token = traverse_obj(response, ('key', {str}))
        if not self._api_token:
            raise ExtractorError('Login failed: No token')

    def _call_api(self, *args, **kwargs):
        if self._token:
            kwargs.setdefault('headers', {})['Authorization'] = f'Bearer {self._token}'
        try:
            return self._download_json(*args, **kwargs)
        except ExtractorError as e:
            if not isinstance(e.cause, HTTPError) or e.cause.status not in (401, 403):
                raise
            self.to_screen(
                f'Reauthorizing with Nebula and retrying, because last API call resulted in error {e.cause.status}')
            self._real_initialize()
            if self._token:
                kwargs.setdefault('headers', {})['Authorization'] = f'Bearer {self._token}'
            return self._download_json(*args, **kwargs)

    def _real_initialize(self):
        if not self._api_token:
            self._api_token = try_call(
                lambda: self._get_cookies('https://nebula.tv')['nebula_auth.apiToken'].value)
        self._token = self._download_json(
            'https://users.api.nebula.app/api/v1/authorization/', None,
            headers={'Authorization': f'Token {self._api_token}'} if self._api_token else None,
            note='Authorizing to Nebula', data=b'')['token']

    def _extract_formats(self, content_id, slug):
        for retry in (False, True):
            try:
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    f'https://content.api.nebula.app/{content_id.split(":")[0]}s/{content_id}/manifest.m3u8',
                    slug, 'mp4', query={
                        'token': self._token,
                        'app_version': '23.10.0',
                        'platform': 'ios',
                    })
                return {'formats': fmts, 'subtitles': subs}
            except ExtractorError as e:
                if isinstance(e.cause, HTTPError) and e.cause.status == 401:
                    self.raise_login_required()
                if not retry and isinstance(e.cause, HTTPError) and e.cause.status == 403:
                    self.to_screen('Reauthorizing with Nebula and retrying, because fetching video resulted in error')
                    self._real_initialize()
                    continue
                raise

    def _extract_video_metadata(self, episode):
        channel_url = traverse_obj(
            episode, (('channel_slug', 'class_slug'), {lambda x: urljoin('https://nebula.tv/', x)}), get_all=False)
        return {
            'id': episode['id'].partition(':')[2],
            **traverse_obj(episode, {
                'display_id': 'slug',
                'title': 'title',
                'description': 'description',
                'timestamp': ('published_at', {parse_iso8601}),
                'duration': ('duration', {int_or_none}),
                'channel_id': 'channel_slug',
                'uploader_id': 'channel_slug',
                'channel': 'channel_title',
                'uploader': 'channel_title',
                'series': 'channel_title',
                'creator': 'channel_title',
                'thumbnail': ('images', 'thumbnail', 'src', {url_or_none}),
                'episode_number': ('order', {int_or_none}),
                # Old code was wrongly setting extractor_key from NebulaSubscriptionsIE
                '_old_archive_ids': ('zype_id', {lambda x: [
                    make_archive_id(NebulaIE, x), make_archive_id(NebulaSubscriptionsIE, x)] if x else None}),
            }),
            'channel_url': channel_url,
            'uploader_url': channel_url,
        }


class NebulaIE(NebulaBaseIE):
    _VALID_URL = rf'{_BASE_URL_RE}/videos/(?P<id>[-\w]+)'
    _TESTS = [{
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
            'thumbnail': r're:https://\w+\.cloudfront\.net/[\w-]+',
            '_old_archive_ids': ['nebula 5c271b40b13fd613090034fd', 'nebulasubscriptions 5c271b40b13fd613090034fd'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
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
            'thumbnail': r're:https://\w+\.cloudfront\.net/[\w-]+',
            '_old_archive_ids': ['nebula 5e7e78171aaf320001fbd6be', 'nebulasubscriptions 5e7e78171aaf320001fbd6be'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
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
            'thumbnail': r're:https://\w+\.cloudfront\.net/[\w-]+',
            'creator': 'Tom Scott Presents: Money',
            '_old_archive_ids': ['nebula 5e779ebdd157bc0001d1c75a', 'nebulasubscriptions 5e779ebdd157bc0001d1c75a'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
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
            'thumbnail': r're:https://\w+\.cloudfront\.net/[\w-]+',
            'creator': 'TLDR News EU',
            '_old_archive_ids': ['nebula 63f64c74366fcd00017c1513', 'nebulasubscriptions 63f64c74366fcd00017c1513'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://beta.nebula.tv/videos/money-episode-1-the-draw',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        slug = self._match_id(url)
        url, smuggled_data = unsmuggle_url(url, {})
        if smuggled_data.get('id'):
            return {
                'id': smuggled_data['id'],
                'display_id': slug,
                'title': '',
                **self._extract_formats(smuggled_data['id'], slug),
            }

        metadata = self._call_api(
            f'https://content.api.nebula.app/content/videos/{slug}',
            slug, note='Fetching video metadata')
        return {
            **self._extract_video_metadata(metadata),
            **self._extract_formats(metadata['id'], slug),
        }


class NebulaClassIE(NebulaBaseIE):
    IE_NAME = 'nebula:class'
    _VALID_URL = rf'{_BASE_URL_RE}/(?P<id>[-\w]+)/(?P<ep>\d+)'
    _TESTS = [{
        'url': 'https://nebula.tv/copyright-for-fun-and-profit/14',
        'info_dict': {
            'id': 'd7432cdc-c608-474d-942c-f74345daed7b',
            'ext': 'mp4',
            'display_id': '14',
            'channel_url': 'https://nebula.tv/copyright-for-fun-and-profit',
            'episode_number': 14,
            'thumbnail': 'https://dj423fildxgac.cloudfront.net/d533718d-9307-42d4-8fb0-e283285e99c9',
            'uploader_url': 'https://nebula.tv/copyright-for-fun-and-profit',
            'duration': 646,
            'episode': 'Episode 14',
            'title': 'Photos, Sculpture, and Video',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        slug, episode = self._match_valid_url(url).group('id', 'ep')
        url, smuggled_data = unsmuggle_url(url, {})
        if smuggled_data.get('id'):
            return {
                'id': smuggled_data['id'],
                'display_id': slug,
                'title': '',
                **self._extract_formats(smuggled_data['id'], slug),
            }

        metadata = self._call_api(
            f'https://content.api.nebula.app/content/{slug}/{episode}/?include=lessons',
            slug, note='Fetching video metadata')
        return {
            **self._extract_video_metadata(metadata),
            **self._extract_formats(metadata['id'], slug),
        }


class NebulaSubscriptionsIE(NebulaBaseIE):
    IE_NAME = 'nebula:subscriptions'
    _VALID_URL = rf'{_BASE_URL_RE}/(?P<id>myshows|library/latest-videos)'
    _TESTS = [{
        'url': 'https://nebula.tv/myshows',
        'playlist_mincount': 1,
        'info_dict': {
            'id': 'myshows',
        },
    }]

    def _generate_playlist_entries(self):
        next_url = update_url_query('https://content.api.nebula.app/video_episodes/', {
            'following': 'true',
            'include': 'engagement',
            'ordering': '-published_at',
        })
        for page_num in itertools.count(1):
            channel = self._call_api(
                next_url, 'myshows', note=f'Retrieving subscriptions page {page_num}')
            for episode in channel['results']:
                metadata = self._extract_video_metadata(episode)
                yield self.url_result(smuggle_url(
                    f'https://nebula.tv/videos/{metadata["display_id"]}',
                    {'id': episode['id']}), NebulaIE, url_transparent=True, **metadata)
            next_url = channel.get('next')
            if not next_url:
                return

    def _real_extract(self, url):
        return self.playlist_result(self._generate_playlist_entries(), 'myshows')


class NebulaChannelIE(NebulaBaseIE):
    IE_NAME = 'nebula:channel'
    _VALID_URL = rf'{_BASE_URL_RE}/(?!myshows|library|videos/)(?P<id>[-\w]+)/?(?:$|[?#])'
    _TESTS = [{
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
    }, {
        'url': 'https://nebula.tv/copyright-for-fun-and-profit',
        'info_dict': {
            'id': 'copyright-for-fun-and-profit',
            'title': 'Copyright for Fun and Profit',
            'description': 'md5:6690248223eed044a9f11cd5a24f9742',
        },
        'playlist_count': 23,
    }]

    def _generate_playlist_entries(self, collection_id, collection_slug):
        next_url = f'https://content.api.nebula.app/video_channels/{collection_id}/video_episodes/?ordering=-published_at'
        for page_num in itertools.count(1):
            episodes = self._call_api(next_url, collection_slug, note=f'Retrieving channel page {page_num}')
            for episode in episodes['results']:
                metadata = self._extract_video_metadata(episode)
                yield self.url_result(smuggle_url(
                    episode.get('share_url') or f'https://nebula.tv/videos/{metadata["display_id"]}',
                    {'id': episode['id']}), NebulaIE, url_transparent=True, **metadata)
            next_url = episodes.get('next')
            if not next_url:
                break

    def _generate_class_entries(self, channel):
        for lesson in channel['lessons']:
            metadata = self._extract_video_metadata(lesson)
            yield self.url_result(smuggle_url(
                lesson.get('share_url') or f'https://nebula.tv/{metadata["class_slug"]}/{metadata["slug"]}',
                {'id': lesson['id']}), NebulaClassIE, url_transparent=True, **metadata)

    def _real_extract(self, url):
        collection_slug = self._match_id(url)
        channel = self._call_api(
            f'https://content.api.nebula.app/content/{collection_slug}/?include=lessons',
            collection_slug, note='Retrieving channel')

        if channel.get('type') == 'class':
            entries = self._generate_class_entries(channel)
        else:
            entries = self._generate_playlist_entries(channel['id'], collection_slug)

        return self.playlist_result(
            entries=entries,
            playlist_id=collection_slug,
            playlist_title=channel.get('title'),
            playlist_description=channel.get('description'))
