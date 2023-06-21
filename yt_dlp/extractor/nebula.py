import itertools
import json
import urllib.error

from .common import InfoExtractor
from ..utils import ExtractorError, make_archive_id, parse_iso8601, remove_start

_BASE_URL_RE = r'https?://(?:www\.|beta\.)?(?:watchnebula\.com|nebula\.app|nebula\.tv)'


class NebulaBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'watchnebula'

    _nebula_api_token = None
    _nebula_bearer_token = None

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

        return response['key']

    def _call_nebula_api(self, url, video_id=None, method='GET', auth_type='api', note=''):
        assert method in ('GET', 'POST',)
        assert auth_type in ('api', 'bearer',)

        def inner_call():
            authorization = f'Token {self._nebula_api_token}' if auth_type == 'api' else f'Bearer {self._nebula_bearer_token}'
            return self._download_json(
                url, video_id, note=note, headers={'Authorization': authorization},
                data=b'' if method == 'POST' else None)

        try:
            return inner_call()
        except ExtractorError as exc:
            # if 401 or 403, attempt credential re-auth and retry
            if exc.cause and isinstance(exc.cause, urllib.error.HTTPError) and exc.cause.code in (401, 403):
                self.to_screen(f'Reauthenticating to Nebula and retrying, because last {auth_type} call resulted in error {exc.cause.code}')
                self._perform_login()
                return inner_call()
            else:
                raise

    def _fetch_nebula_bearer_token(self):
        """
        Get a Bearer token for the Nebula API. This will be required to fetch video meta data.
        """
        response = self._call_nebula_api('https://api.watchnebula.com/api/v1/authorization/',
                                         method='POST',
                                         note='Authorizing to Nebula')
        return response['token']

    def _fetch_video_formats(self, slug):
        stream_info = self._call_nebula_api(f'https://content.api.nebula.app/video/{slug}/stream/',
                                            video_id=slug,
                                            auth_type='bearer',
                                            note='Fetching video stream info')
        manifest_url = stream_info['manifest']
        return self._extract_m3u8_formats_and_subtitles(manifest_url, slug, 'mp4')

    def _build_video_info(self, episode):
        fmts, subs = self._fetch_video_formats(episode['slug'])
        channel_slug = episode['channel_slug']
        channel_title = episode['channel_title']
        zype_id = episode.get('zype_id')
        return {
            'id': remove_start(episode['id'], 'video_episode:'),
            'display_id': episode['slug'],
            'formats': fmts,
            'subtitles': subs,
            'webpage_url': f'https://nebula.tv/{episode["slug"]}',
            'title': episode['title'],
            'description': episode['description'],
            'timestamp': parse_iso8601(episode['published_at']),
            'thumbnails': [{
                # 'id': tn.get('name'),  # this appears to be null
                'url': tn['original'],
                'height': key,
            } for key, tn in episode['assets']['thumbnail'].items()],
            'duration': episode['duration'],
            'channel': channel_title,
            'channel_id': channel_slug,
            'channel_url': f'https://nebula.tv/{channel_slug}',
            'uploader': channel_title,
            'uploader_id': channel_slug,
            'uploader_url': f'https://nebula.tv/{channel_slug}',
            'series': channel_title,
            'creator': channel_title,
            'extractor_key': NebulaIE.ie_key(),
            'extractor': NebulaIE.IE_NAME,
            '_old_archive_ids': [make_archive_id(NebulaIE, zype_id)] if zype_id else None,
        }

    def _perform_login(self, username=None, password=None):
        self._nebula_api_token = self._perform_nebula_auth(username, password)
        self._nebula_bearer_token = self._fetch_nebula_bearer_token()


class NebulaIE(NebulaBaseIE):
    _VALID_URL = rf'{_BASE_URL_RE}/videos/(?P<id>[-\w]+)'
    _TESTS = [
        {
            'url': 'https://nebula.tv/videos/that-time-disney-remade-beauty-and-the-beast',
            'md5': '14944cfee8c7beeea106320c47560efc',
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
        },
        {
            'url': 'https://beta.nebula.tv/videos/money-episode-1-the-draw',
            'only_matching': True,
        },
    ]

    def _fetch_video_metadata(self, slug):
        return self._call_nebula_api(f'https://content.api.nebula.app/video/{slug}/',
                                     video_id=slug,
                                     auth_type='bearer',
                                     note='Fetching video meta data')

    def _real_extract(self, url):
        slug = self._match_id(url)
        video = self._fetch_video_metadata(slug)
        return self._build_video_info(video)


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
            channel = self._call_nebula_api(next_url, 'myshows', auth_type='bearer',
                                            note=f'Retrieving subscriptions page {page_num}')
            for episode in channel['results']:
                yield self._build_video_info(episode)
            next_url = channel['next']
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
        },
    ]

    def _generate_playlist_entries(self, collection_id, channel):
        episodes = channel['episodes']['results']
        for page_num in itertools.count(2):
            for episode in episodes:
                yield self._build_video_info(episode)
            next_url = channel['episodes']['next']
            if not next_url:
                break
            channel = self._call_nebula_api(next_url, collection_id, auth_type='bearer',
                                            note=f'Retrieving channel page {page_num}')
            episodes = channel['episodes']['results']

    def _real_extract(self, url):
        collection_id = self._match_id(url)
        channel_url = f'https://content.watchnebula.com/video/channels/{collection_id}/'
        channel = self._call_nebula_api(channel_url, collection_id, auth_type='bearer', note='Retrieving channel')
        channel_details = channel['details']

        return self.playlist_result(
            entries=self._generate_playlist_entries(collection_id, channel),
            playlist_id=collection_id,
            playlist_title=channel_details['title'],
            playlist_description=channel_details['description']
        )
