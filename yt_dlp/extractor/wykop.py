import json

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    format_field,
    parse_iso8601,
    traverse_obj,
    url_or_none,
)


class WykopBaseExtractor(InfoExtractor):
    def _get_token(self, force_refresh=False):
        if not force_refresh:
            maybe_cached = self.cache.load('wykop', 'bearer')
            if maybe_cached:
                return maybe_cached

        new_token = traverse_obj(
            self._do_call_api('auth', None, 'Downloading anonymous auth token', data={
                # hardcoded in frontend
                'key': 'w53947240748',
                'secret': 'd537d9e0a7adc1510842059ae5316419',
            }), ('data', 'token'))

        self.cache.store('wykop', 'bearer', new_token)
        return new_token

    def _do_call_api(self, path, video_id, note='Downloading JSON metadata', data=None, headers={}):
        if data:
            data = json.dumps({'data': data}).encode()
            headers['Content-Type'] = 'application/json'

        return self._download_json(
            f'https://wykop.pl/api/v3/{path}', video_id,
            note=note, data=data, headers=headers)

    def _call_api(self, path, video_id, note='Downloading JSON metadata'):
        token = self._get_token()
        for retrying in range(2):
            try:
                return self._do_call_api(path, video_id, note, headers={'Authorization': f'Bearer {token}'})
            except ExtractorError as e:
                if not retrying and isinstance(e.cause, HTTPError) and e.cause.status == 403:
                    token = self._get_token(True)
                    continue
                raise

    def _common_data_extract(self, data):
        author = traverse_obj(data, ('author', 'username'), expected_type=str)

        return {
            '_type': 'url_transparent',
            'display_id': data.get('slug'),
            'url': traverse_obj(data,
                                ('media', 'embed', 'url'),  # what gets an iframe embed
                                ('source', 'url'),  # clickable url (dig only)
                                expected_type=url_or_none),
            'thumbnail': traverse_obj(
                data, ('media', 'photo', 'url'), ('media', 'embed', 'thumbnail'), expected_type=url_or_none),
            'uploader': author,
            'uploader_id': author,
            'uploader_url': format_field(author, None, 'https://wykop.pl/ludzie/%s'),
            'timestamp': parse_iso8601(data.get('created_at'), delimiter=' '),  # time it got submitted
            'like_count': traverse_obj(data, ('votes', 'up'), expected_type=int),
            'dislike_count': traverse_obj(data, ('votes', 'down'), expected_type=int),
            'comment_count': traverse_obj(data, ('comments', 'count'), expected_type=int),
            'age_limit': 18 if data.get('adult') else 0,
            'tags': data.get('tags'),
        }


class WykopDigIE(WykopBaseExtractor):
    IE_NAME = 'wykop:dig'
    _VALID_URL = r'https?://(?:www\.)?wykop\.pl/link/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://wykop.pl/link/6912923/najbardziej-zrzedliwy-kot-na-swiecie-i-frozen-planet-ii-i-bbc-earth',
        'info_dict': {
            'id': 'rlSTBvViflc',
            'ext': 'mp4',
            'title': 'Najbardziej zrzędliwy kot na świecie I Frozen Planet II I BBC Earth',
            'display_id': 'najbardziej-zrzedliwy-kot-na-swiecie-i-frozen-planet-ii-i-bbc-earth',
            'description': 'md5:ac0f87dea1cdcb6b0c53f3612a095c87',
            'tags': ['zwierzaczki', 'koty', 'smiesznykotek', 'humor', 'rozrywka', 'ciekawostki'],
            'age_limit': 0,
            'timestamp': 1669154480,
            'release_timestamp': 1669194241,
            'release_date': '20221123',
            'uploader': 'starnak',
            'uploader_id': 'starnak',
            'uploader_url': 'https://wykop.pl/ludzie/starnak',
            'like_count': int,
            'dislike_count': int,
            'comment_count': int,
            'thumbnail': r're:https?://wykop\.pl/cdn/.+',
            'view_count': int,
            'channel': 'BBC Earth',
            'channel_id': 'UCwmZiChSryoWQCZMIQezgTg',
            'channel_url': 'https://www.youtube.com/channel/UCwmZiChSryoWQCZMIQezgTg',
            'categories': ['Pets & Animals'],
            'upload_date': '20220923',
            'duration': 191,
            'channel_follower_count': int,
            'availability': 'public',
            'live_status': 'not_live',
            'playable_in_embed': True,
        },
    }]

    @classmethod
    def suitable(cls, url):
        return cls._match_valid_url(url) and not WykopDigCommentIE.suitable(url)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._call_api(f'links/{video_id}', video_id)['data']

        return {
            **self._common_data_extract(data),
            'id': video_id,
            'title': data['title'],
            'description': data.get('description'),
            # time it got "digged" to the homepage
            'release_timestamp': parse_iso8601(data.get('published_at'), delimiter=' '),
        }


class WykopDigCommentIE(WykopBaseExtractor):
    IE_NAME = 'wykop:dig:comment'
    _VALID_URL = r'https?://(?:www\.)?wykop\.pl/link/(?P<dig_id>\d+)/[^/]+/komentarz/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://wykop.pl/link/6992589/strollowal-oszusta-przez-ponad-24-minuty-udawal-naiwniaka-i-nagral-rozmowe/komentarz/114540527/podobna-sytuacja-ponizej-ciekawa-dyskusja-z-oszustem-na-sam-koniec-sam-bylem-w-biurze-swiadkiem-podobnej-rozmowy-niemal-zakonczonej-sukcesem-bandyty-g',
        'info_dict': {
            'id': 'u6tEi2FmKZY',
            'ext': 'mp4',
            'title': 'md5:e7c741c5baa7ed6478000caf72865577',
            'display_id': 'md5:45b2d12bd0e262d09cc7cf7abc8412db',
            'description': 'md5:bcec7983429f9c0630f9deb9d3d1ba5e',
            'timestamp': 1674476945,
            'uploader': 'Bartholomew',
            'uploader_id': 'Bartholomew',
            'uploader_url': 'https://wykop.pl/ludzie/Bartholomew',
            'thumbnail': r're:https?://wykop\.pl/cdn/.+',
            'tags': [],
            'availability': 'public',
            'duration': 1838,
            'upload_date': '20230117',
            'categories': ['Entertainment'],
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'comment_count': int,
            'channel_follower_count': int,
            'playable_in_embed': True,
            'live_status': 'not_live',
            'age_limit': 0,
            'chapters': 'count:3',
            'channel': 'Poszukiwacze Okazji',
            'channel_id': 'UCzzvJDZThwv06dR4xmzrZBw',
            'channel_url': 'https://www.youtube.com/channel/UCzzvJDZThwv06dR4xmzrZBw',
        },
    }]

    def _real_extract(self, url):
        dig_id, comment_id = self._search_regex(self._VALID_URL, url, 'dig and comment ids', group=('dig_id', 'id'))
        data = self._call_api(f'links/{dig_id}/comments/{comment_id}', comment_id)['data']

        return {
            **self._common_data_extract(data),
            'id': comment_id,
            'title': f"{traverse_obj(data, ('author', 'username'))} - {data.get('content') or ''}",
            'description': data.get('content'),
        }


class WykopPostIE(WykopBaseExtractor):
    IE_NAME = 'wykop:post'
    _VALID_URL = r'https?://(?:www\.)?wykop\.pl/wpis/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://wykop.pl/wpis/68893343/kot-koty-smiesznykotek',
        'info_dict': {
            'id': 'PL8JMjiUPHUhwc9ZlKa_5IFeBwBV8Xe7jI',
            'title': 'PawelW124 - #kot #koty #smiesznykotek',
            'description': '#kot #koty #smiesznykotek',
            'display_id': 'kot-koty-smiesznykotek',
            'tags': ['kot', 'koty', 'smiesznykotek'],
            'uploader': 'PawelW124',
            'uploader_id': 'PawelW124',
            'uploader_url': 'https://wykop.pl/ludzie/PawelW124',
            'timestamp': 1668938142,
            'age_limit': 0,
            'like_count': int,
            'dislike_count': int,
            'thumbnail': r're:https?://wykop\.pl/cdn/.+',
            'comment_count': int,
            'channel': 'Revan',
            'channel_id': 'UCW9T_-uZoiI7ROARQdTDyOw',
            'channel_url': 'https://www.youtube.com/channel/UCW9T_-uZoiI7ROARQdTDyOw',
            'upload_date': '20221120',
            'modified_date': '20220814',
            'availability': 'public',
            'view_count': int,
        },
        'playlist_mincount': 15,
        'params': {
            'flat_playlist': True,
        }
    }]

    @classmethod
    def suitable(cls, url):
        return cls._match_valid_url(url) and not WykopPostCommentIE.suitable(url)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._call_api(f'entries/{video_id}', video_id)['data']

        return {
            **self._common_data_extract(data),
            'id': video_id,
            'title': f"{traverse_obj(data, ('author', 'username'))} - {data.get('content') or ''}",
            'description': data.get('content'),
        }


class WykopPostCommentIE(WykopBaseExtractor):
    IE_NAME = 'wykop:post:comment'
    _VALID_URL = r'https?://(?:www\.)?wykop\.pl/wpis/(?P<post_id>\d+)/[^/#]+#(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://wykop.pl/wpis/70084873/test-test-test#249303979',
        'info_dict': {
            'id': 'confusedquickarmyant',
            'ext': 'mp4',
            'title': 'tpap - treść komentarza',
            'display_id': 'tresc-komentarza',
            'description': 'treść komentarza',
            'uploader': 'tpap',
            'uploader_id': 'tpap',
            'uploader_url': 'https://wykop.pl/ludzie/tpap',
            'timestamp': 1675349470,
            'upload_date': '20230202',
            'tags': [],
            'duration': 2.12,
            'age_limit': 0,
            'categories': [],
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'thumbnail': r're:https?://wykop\.pl/cdn/.+',
        },
    }]

    def _real_extract(self, url):
        post_id, comment_id = self._search_regex(self._VALID_URL, url, 'post and comment ids', group=('post_id', 'id'))
        data = self._call_api(f'entries/{post_id}/comments/{comment_id}', comment_id)['data']

        return {
            **self._common_data_extract(data),
            'id': comment_id,
            'title': f"{traverse_obj(data, ('author', 'username'))} - {data.get('content') or ''}",
            'description': data.get('content'),
        }
