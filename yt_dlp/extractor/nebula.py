import itertools
import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    format_field,
    parse_iso8601,
    smuggle_url,
    traverse_obj,
    unsmuggle_url,
)

_BASE_URL_RE = r'https?://(?:www\.|beta\.)?(?:watchnebula\.com|nebula\.app|nebula\.tv)'


class NebulaBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'watchnebula'
    _tokens = {'api': None, 'bearer': None}

    def _perform_nebula_auth(self, username, password):
        if not username or not password:
            self.raise_login_required(method='password')

        data = json.dumps({'email': username, 'password': password}).encode('utf8')
        response = self._download_json(
            'https://api.watchnebula.com/api/v1/auth/login/',
            data=data, fatal=False, video_id=None,
            headers={
                'content-type': 'application/json',
                # Submitting the 'sessionid' cookie always causes a 403 on auth endpoint
                'cookie': ''
            },
            note='Logging in to Nebula with supplied credentials',
            errnote='Authentication failed or rejected')
        if not response or not response.get('key'):
            self.raise_login_required(method='password')

        return self._download_json(
            'https://api.watchnebula.com/api/v1/authorization/', None,
            headers={'Authorization': f'Token {response["key"]}'},
            note='Authorizing to Nebula', data=b'')['token']

    def _call_nebula_api(self, url, video_id, note):
        def inner_call():
            return self._download_json(url, video_id, note=note,
                                       headers={'Authorization': f'Bearer {self._token}'})

        try:
            return inner_call()
        except ExtractorError as exc:  # if 401 or 403, attempt credential re-auth and retry
            if isinstance(exc.cause, urllib.error.HTTPError) and exc.cause.code in (401, 403):
                self.to_screen(f'Reauthenticating to Nebula and retrying, '
                               f'because last API call resulted in error {exc.cause.code}')
                self._perform_login(*self._get_login_info())
                return inner_call()
            raise

    def _build_video_info_from_data(self, slug, data, fetch_formats_and_subs=True):
        if fetch_formats_and_subs:
            stream_info = self._call_nebula_api(
                f'https://content.watchnebula.com/video/{slug}/stream/',
                slug, note='Fetching video stream info')
            fmts, subs = self._extract_m3u8_formats_and_subtitles(stream_info['manifest'], slug)
            info = {'formats': fmts, 'subtitles': subs}
        else:
            info = {
                '_type': 'url',
                'url': smuggle_url(f'https://nebula.tv/{slug}', data)
            }

        channel_url = format_field(data, 'channel_id', 'https://nebula.app/%s')
        return {
            'display_id': slug,
            'channel_url': channel_url,
            'uploader_url': channel_url,
            **info,
            **traverse_obj(data, {
                'id': 'id',
                'title': 'title',
                'description': 'description',
                'timestamp': 'timestamp',
                'thumbnails': 'thumbnails',
                'duration': 'duration',
                'channel_id': 'channel_id',
                'uploader_id': 'channel_id',
                'channel': 'channel',
                'uploader': 'channel',
                'series': 'channel',
                'creator': 'channel',
            })
        }

    def _build_video_info(self, episode, fetch_formats_and_subs=True):
        return self._build_video_info_from_data(episode['slug'], {
            **traverse_obj(episode, {
                'id': 'zype_id',
                'title': 'title',
                'description': 'description',
                'timestamp': ('published_at', parse_iso8601),
                'duration': 'duration',
                'channel_id': 'channel_slug',
                'channel': 'channel_title',
            }),
            'thumbnails': [{
                # 'id': tn.get('name'),  # this appears to be null
                'url': tn['original'],
                'height': key,
            } for key, tn in traverse_obj(episode, ('assets', 'thumbnail'), default={}).items()],
        }, fetch_formats_and_subs)

    def _perform_login(self, username, password):
        self._token = self._perform_nebula_auth(username, password)


class NebulaIE(NebulaBaseIE):
    _VALID_URL = rf'{_BASE_URL_RE}/videos/(?P<id>[-\w]+)'
    _TESTS = [
        {
            'url': 'https://nebula.tv/videos/that-time-disney-remade-beauty-and-the-beast',
            'info_dict': {
                'id': '84ed544d-4afd-4723-8cd5-2b95261f0abf',
                'ext': 'mp4',
                'title': 'That Time Disney Remade Beauty and the Beast',
                'description': 'Note: this video was originally posted on YouTube with the sponsor read included. We weren’t able to remove it without reducing video quality, so it’s presented here in its original context.',
                'upload_date': '20180731',
                'timestamp': 1533009600,
                'channel': 'Lindsay Ellis',
                'channel_id': 'lindsayellis',
                'uploader': 'Lindsay Ellis',
                'uploader_id': 'lindsayellis',
                'timestamp': 1533009600,
                'uploader_url': 'https://nebula.tv/lindsayellis',
                'series': 'Lindsay Ellis',
                'display_id': 'that-time-disney-remade-beauty-and-the-beast',
                'channel_url': 'https://nebula.tv/lindsayellis',
                'creator': 'Lindsay Ellis',
                'duration': 2212,
                'thumbnail': r're:https://\w+\.cloudfront\.net/[\w-]+\.jpeg?.*',
            },
            'params': {
                'skip_download': 'm3u8',
            },
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
                'id': '63f64c74366fcd00017c1513',
                'display_id': 'tldrnewseu-did-the-us-really-blow-up-the-nordstream-pipelines',
                'title': 'Did the US Really Blow Up the NordStream Pipelines?',
                'description': 'md5:b4e2a14e3ff08f546a3209c75261e789',
                'upload_date': '20230223',
                'timestamp': 1677144070,
                'channel': 'TLDR News EU',
                'channel_id': 'tldrnewseu',
                'uploader': 'TLDR News EU',
                'uploader_id': 'tldrnewseu',
                'uploader_url': 'https://nebula.tv/tldrnewseu',
                'duration': 524,
                'channel_url': 'https://nebula.tv/tldrnewseu',
                'series': 'TLDR News EU',
                'thumbnail': r're:https?://.*\.jpeg',
                'creator': 'TLDR News EU',
                'ext': 'mp4',
            },
            'params': {
                'skip_download': 'm3u8',
            },
        },
        {
            'url': 'https://beta.nebula.tv/videos/money-episode-1-the-draw',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        slug = self._match_id(url)
        url, smuggled_data = unsmuggle_url(url, {})
        if smuggled_data:
            return self._build_video_info_from_data(slug, smuggled_data)
        return self._build_video_info(self._call_nebula_api(
            f'https://content.watchnebula.com/video/{slug}/',
            slug, note='Fetching video meta data'))


class NebulaSubscriptionsIE(NebulaBaseIE):
    IE_NAME = 'nebula:subscriptions'
    _VALID_URL = rf'{_BASE_URL_RE}/myshows'
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
        page_num = 1
        while next_url:
            channel = self._call_nebula_api(
                next_url, 'myshows', note=f'Retrieving subscriptions page {page_num}')
            for episode in channel['results']:
                yield self._build_video_info(episode)
            next_url = channel.get('next')
            page_num += 1

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
                yield self._build_video_info(episode, fetch_formats_and_subs=False)
            next_url = channel['episodes'].get('next')
            if not next_url:
                break
            channel = self._call_nebula_api(
                next_url, collection_id, note=f'Retrieving channel page {page_num}')

    def _real_extract(self, url):
        collection_id = self._match_id(url)
        channel = self._call_nebula_api(
            f'https://content.watchnebula.com/video/channels/{collection_id}/',
            collection_id, note='Retrieving channel')

        return self.playlist_result(
            entries=self._generate_playlist_entries(collection_id, channel),
            playlist_id=collection_id,
            playlist_title=traverse_obj(channel, ('details', 'title')),
            playlist_description=traverse_obj(channel, ('details', 'description')))
