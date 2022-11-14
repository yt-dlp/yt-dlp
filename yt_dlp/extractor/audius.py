import random

from .common import InfoExtractor
from ..compat import compat_str, compat_urllib_parse_unquote
from ..utils import ExtractorError, str_or_none, try_get


class AudiusBaseIE(InfoExtractor):
    _API_BASE = None
    _API_V = '/v1'

    def _get_response_data(self, response):
        if isinstance(response, dict):
            response_data = response.get('data')
            if response_data is not None:
                return response_data
            if len(response) == 1 and 'message' in response:
                raise ExtractorError('API error: %s' % response['message'],
                                     expected=True)
        raise ExtractorError('Unexpected API response')

    def _select_api_base(self):
        """Selecting one of the currently available API hosts"""
        response = super(AudiusBaseIE, self)._download_json(
            'https://api.audius.co/', None,
            note='Requesting available API hosts',
            errnote='Unable to request available API hosts')
        hosts = self._get_response_data(response)
        if isinstance(hosts, list):
            self._API_BASE = random.choice(hosts)
            return
        raise ExtractorError('Unable to get available API hosts')

    @staticmethod
    def _prepare_url(url, title):
        """
        Audius removes forward slashes from the uri, but leaves backslashes.
        The problem is that the current version of Chrome replaces backslashes
        in the address bar with a forward slashes, so if you copy the link from
        there and paste it into youtube-dl, you won't be able to download
        anything from this link, since the Audius API won't be able to resolve
        this url
        """
        url = compat_urllib_parse_unquote(url)
        title = compat_urllib_parse_unquote(title)
        if '/' in title or '%2F' in title:
            fixed_title = title.replace('/', '%5C').replace('%2F', '%5C')
            return url.replace(title, fixed_title)
        return url

    def _api_request(self, path, item_id=None, note='Downloading JSON metadata',
                     errnote='Unable to download JSON metadata',
                     expected_status=None):
        if self._API_BASE is None:
            self._select_api_base()
        try:
            response = super(AudiusBaseIE, self)._download_json(
                '%s%s%s' % (self._API_BASE, self._API_V, path), item_id, note=note,
                errnote=errnote, expected_status=expected_status)
        except ExtractorError as exc:
            # some of Audius API hosts may not work as expected and return HTML
            if 'Failed to parse JSON' in compat_str(exc):
                raise ExtractorError('An error occurred while receiving data. Try again',
                                     expected=True)
            raise exc
        return self._get_response_data(response)

    def _resolve_url(self, url, item_id):
        return self._api_request('/resolve?url=%s' % url, item_id,
                                 expected_status=404)


class AudiusIE(AudiusBaseIE):
    _VALID_URL = r'''(?x)https?://(?:www\.)?(?:audius\.co/(?P<uploader>[\w\d-]+)(?!/album|/playlist)/(?P<title>\S+))'''
    IE_DESC = 'Audius.co'
    _TESTS = [
        {
            # URL from Chrome address bar which replace backslash to forward slash
            'url': 'https://audius.co/test_acc/t%D0%B5%D0%B5%D0%B5est-1.%5E_%7B%7D/%22%3C%3E.%E2%84%96~%60-198631',
            'md5': '92c35d3e754d5a0f17eef396b0d33582',
            'info_dict': {
                'id': 'xd8gY',
                'title': '''Tеееest/ 1.!@#$%^&*()_+=[]{};'\\\":<>,.?/№~`''',
                'ext': 'mp3',
                'description': 'Description',
                'duration': 30,
                'track': '''Tеееest/ 1.!@#$%^&*()_+=[]{};'\\\":<>,.?/№~`''',
                'artist': 'test',
                'genre': 'Electronic',
                'thumbnail': r're:https?://.*\.jpg',
                'view_count': int,
                'like_count': int,
                'repost_count': int,
            }
        },
        {
            # Regular track
            'url': 'https://audius.co/voltra/radar-103692',
            'md5': '491898a0a8de39f20c5d6a8a80ab5132',
            'info_dict': {
                'id': 'KKdy2',
                'title': 'RADAR',
                'ext': 'mp3',
                'duration': 318,
                'track': 'RADAR',
                'artist': 'voltra',
                'genre': 'Trance',
                'thumbnail': r're:https?://.*\.jpg',
                'view_count': int,
                'like_count': int,
                'repost_count': int,
            }
        },
    ]

    _ARTWORK_MAP = {
        "150x150": 150,
        "480x480": 480,
        "1000x1000": 1000
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        track_id = try_get(mobj, lambda x: x.group('track_id'))
        if track_id is None:
            title = mobj.group('title')
            # uploader = mobj.group('uploader')
            url = self._prepare_url(url, title)
            track_data = self._resolve_url(url, title)
        else:  # API link
            title = None
            # uploader = None
            track_data = self._api_request('/tracks/%s' % track_id, track_id)

        if not isinstance(track_data, dict):
            raise ExtractorError('Unexpected API response')

        track_id = track_data.get('id')
        if track_id is None:
            raise ExtractorError('Unable to get ID of the track')

        artworks_data = track_data.get('artwork')
        thumbnails = []
        if isinstance(artworks_data, dict):
            for quality_key, thumbnail_url in artworks_data.items():
                thumbnail = {
                    "url": thumbnail_url
                }
                quality_code = self._ARTWORK_MAP.get(quality_key)
                if quality_code is not None:
                    thumbnail['preference'] = quality_code
                thumbnails.append(thumbnail)

        return {
            'id': track_id,
            'title': track_data.get('title', title),
            'url': '%s/v1/tracks/%s/stream' % (self._API_BASE, track_id),
            'ext': 'mp3',
            'description': track_data.get('description'),
            'duration': track_data.get('duration'),
            'track': track_data.get('title'),
            'artist': try_get(track_data, lambda x: x['user']['name'], compat_str),
            'genre': track_data.get('genre'),
            'thumbnails': thumbnails,
            'view_count': track_data.get('play_count'),
            'like_count': track_data.get('favorite_count'),
            'repost_count': track_data.get('repost_count'),
        }


class AudiusTrackIE(AudiusIE):
    _VALID_URL = r'''(?x)(?:audius:)(?:https?://(?:www\.)?.+/v1/tracks/)?(?P<track_id>\w+)'''
    IE_NAME = 'audius:track'
    IE_DESC = 'Audius track ID or API link. Prepend with "audius:"'
    _TESTS = [
        {
            'url': 'audius:9RWlo',
            'only_matching': True
        },
        {
            'url': 'audius:http://discoveryprovider.audius.prod-us-west-2.staked.cloud/v1/tracks/9RWlo',
            'only_matching': True
        },
    ]


class AudiusPlaylistIE(AudiusBaseIE):
    _VALID_URL = r'https?://(?:www\.)?audius\.co/(?P<uploader>[\w\d-]+)/(?:album|playlist)/(?P<title>\S+)'
    IE_NAME = 'audius:playlist'
    IE_DESC = 'Audius.co playlists'
    _TEST = {
        'url': 'https://audius.co/test_acc/playlist/test-playlist-22910',
        'info_dict': {
            'id': 'DNvjN',
            'title': 'test playlist',
            'description': 'Test description\n\nlol',
        },
        'playlist_count': 175,
    }

    def _build_playlist(self, tracks):
        entries = []
        for track in tracks:
            if not isinstance(track, dict):
                raise ExtractorError('Unexpected API response')
            track_id = str_or_none(track.get('id'))
            if not track_id:
                raise ExtractorError('Unable to get track ID from playlist')
            entries.append(self.url_result(
                'audius:%s' % track_id,
                ie=AudiusTrackIE.ie_key(), video_id=track_id))
        return entries

    def _real_extract(self, url):
        self._select_api_base()
        mobj = self._match_valid_url(url)
        title = mobj.group('title')
        # uploader = mobj.group('uploader')
        url = self._prepare_url(url, title)
        playlist_response = self._resolve_url(url, title)

        if not isinstance(playlist_response, list) or len(playlist_response) != 1:
            raise ExtractorError('Unexpected API response')

        playlist_data = playlist_response[0]
        if not isinstance(playlist_data, dict):
            raise ExtractorError('Unexpected API response')

        playlist_id = playlist_data.get('id')
        if playlist_id is None:
            raise ExtractorError('Unable to get playlist ID')

        playlist_tracks = self._api_request(
            '/playlists/%s/tracks' % playlist_id,
            title, note='Downloading playlist tracks metadata',
            errnote='Unable to download playlist tracks metadata')
        if not isinstance(playlist_tracks, list):
            raise ExtractorError('Unexpected API response')

        entries = self._build_playlist(playlist_tracks)
        return self.playlist_result(entries, playlist_id,
                                    playlist_data.get('playlist_name', title),
                                    playlist_data.get('description'))


class AudiusProfileIE(AudiusPlaylistIE):
    IE_NAME = 'audius:artist'
    IE_DESC = 'Audius.co profile/artist pages'
    _VALID_URL = r'https?://(?:www)?audius\.co/(?P<id>[^\/]+)/?(?:[?#]|$)'
    _TEST = {
        'url': 'https://audius.co/pzl/',
        'info_dict': {
            'id': 'ezRo7',
            'description': 'TAMALE\n\nContact: officialpzl@gmail.com',
            'title': 'pzl',
        },
        'playlist_count': 24,
    }

    def _real_extract(self, url):
        self._select_api_base()
        profile_id = self._match_id(url)
        try:
            _profile_data = self._api_request('/full/users/handle/' + profile_id, profile_id)
        except ExtractorError as e:
            raise ExtractorError('Could not download profile info; ' + str(e))
        profile_audius_id = _profile_data[0]['id']
        profile_bio = _profile_data[0].get('bio')

        api_call = self._api_request('/full/users/handle/%s/tracks' % profile_id, profile_id)
        return self.playlist_result(self._build_playlist(api_call), profile_audius_id, profile_id, profile_bio)
