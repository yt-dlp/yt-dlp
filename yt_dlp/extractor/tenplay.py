import base64
import datetime as dt
import functools
import itertools

from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import int_or_none, traverse_obj, urlencode_postdata, urljoin


class TenPlayIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?10play\.com\.au/(?:[^/]+/)+(?P<id>tpv\d{6}[a-z]{5})'
    _NETRC_MACHINE = '10play'
    _TESTS = [{
        'url': 'https://10play.com.au/neighbours/web-extras/season-39/nathan-borg-is-the-first-aussie-actor-with-a-cochlear-implant-to-join-neighbours/tpv210128qupwd',
        'info_dict': {
            'id': '6226844312001',
            'ext': 'mp4',
            'title': 'Nathan Borg Is The First Aussie Actor With A Cochlear Implant To Join Neighbours',
            'alt_title': 'Nathan Borg Is The First Aussie Actor With A Cochlear Implant To Join Neighbours',
            'description': 'md5:a02d0199c901c2dd4c796f1e7dd0de43',
            'duration': 186,
            'season': 'Season 39',
            'season_number': 39,
            'series': 'Neighbours',
            'thumbnail': r're:https://.*\.jpg',
            'uploader': 'Channel 10',
            'age_limit': 15,
            'timestamp': 1611810000,
            'upload_date': '20210128',
            'uploader_id': '2199827728001',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Only available in Australia',
    }, {
        'url': 'https://10play.com.au/todd-sampsons-body-hack/episodes/season-4/episode-7/tpv200921kvngh',
        'info_dict': {
            'id': '6192880312001',
            'ext': 'mp4',
            'title': "Todd Sampson's Body Hack - S4 Ep. 2",
            'description': 'md5:fa278820ad90f08ea187f9458316ac74',
            'age_limit': 15,
            'timestamp': 1600770600,
            'upload_date': '20200922',
            'uploader': 'Channel 10',
            'uploader_id': '2199827728001'
        },
        'params': {
            'skip_download': True,
        }
    }, {
        'url': 'https://10play.com.au/how-to-stay-married/web-extras/season-1/terrys-talks-ep-1-embracing-change/tpv190915ylupc',
        'only_matching': True,
    }]
    _GEO_BYPASS = False

    _AUS_AGES = {
        'G': 0,
        'PG': 15,
        'M': 15,
        'MA': 15,
        'MA15+': 15,
        'R': 18,
        'X': 18
    }

    def _get_bearer_token(self, video_id):
        username, password = self._get_login_info()
        if username is None or password is None:
            self.raise_login_required('Your 10play account\'s details must be provided with --username and --password.')
        _timestamp = dt.datetime.now().strftime('%Y%m%d000000')
        _auth_header = base64.b64encode(_timestamp.encode('ascii')).decode('ascii')
        data = self._download_json('https://10play.com.au/api/user/auth', video_id, 'Getting bearer token', headers={
            'X-Network-Ten-Auth': _auth_header,
        }, data=urlencode_postdata({
            'email': username,
            'password': password,
        }))
        return 'Bearer ' + data['jwt']['accessToken']

    def _real_extract(self, url):
        content_id = self._match_id(url)
        data = self._download_json(
            'https://10play.com.au/api/v1/videos/' + content_id, content_id)
        headers = {}

        if data.get('memberGated') is True:
            _token = self._get_bearer_token(content_id)
            headers = {'Authorization': _token}

        _video_url = self._download_json(
            data.get('playbackApiEndpoint'), content_id, 'Downloading video JSON',
            headers=headers).get('source')
        m3u8_url = self._request_webpage(HEADRequest(
            _video_url), content_id).url
        if '10play-not-in-oz' in m3u8_url:
            self.raise_geo_restricted(countries=['AU'])
        formats = self._extract_m3u8_formats(m3u8_url, content_id, 'mp4')

        return {
            'formats': formats,
            'subtitles': {'en': [{'url': data.get('captionUrl')}]} if data.get('captionUrl') else None,
            'id': data.get('altId') or content_id,
            'duration': data.get('duration'),
            'title': data.get('subtitle'),
            'alt_title': data.get('title'),
            'description': data.get('description'),
            'age_limit': self._AUS_AGES.get(data.get('classification')),
            'series': data.get('tvShow'),
            'season_number': int_or_none(data.get('season')),
            'episode_number': int_or_none(data.get('episode')),
            'timestamp': data.get('published'),
            'thumbnail': data.get('imageUrl'),
            'uploader': 'Channel 10',
            'uploader_id': '2199827728001',
        }


class TenPlaySeasonIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?10play\.com\.au/(?P<show>[^/?#]+)/episodes/(?P<season>[^/?#]+)/?(?:$|[?#])'
    _TESTS = [{
        'url': 'https://10play.com.au/masterchef/episodes/season-14',
        'info_dict': {
            'title': 'Season 14',
            'id': 'MjMyOTIy',
        },
        'playlist_mincount': 64,
    }, {
        'url': 'https://10play.com.au/the-bold-and-the-beautiful-fast-tracked/episodes/season-2022',
        'info_dict': {
            'title': 'Season 2022',
            'id': 'Mjc0OTIw',
        },
        'playlist_mincount': 256,
    }]

    def _entries(self, load_more_url, display_id=None):
        skip_ids = []
        for page in itertools.count(1):
            episodes_carousel = self._download_json(
                load_more_url, display_id, query={'skipIds[]': skip_ids},
                note=f'Fetching episodes page {page}')

            episodes_chunk = episodes_carousel['items']
            skip_ids.extend(ep['id'] for ep in episodes_chunk)

            for ep in episodes_chunk:
                yield ep['cardLink']
            if not episodes_carousel['hasMore']:
                break

    def _real_extract(self, url):
        show, season = self._match_valid_url(url).group('show', 'season')
        season_info = self._download_json(
            f'https://10play.com.au/api/shows/{show}/episodes/{season}', f'{show}/{season}')

        episodes_carousel = traverse_obj(season_info, (
            'content', 0, 'components', (
                lambda _, v: v['title'].lower() == 'episodes',
                (..., {dict}),
            )), get_all=False) or {}

        playlist_id = episodes_carousel['tpId']

        return self.playlist_from_matches(
            self._entries(urljoin(url, episodes_carousel['loadMoreUrl']), playlist_id),
            playlist_id, traverse_obj(season_info, ('content', 0, 'title', {str})),
            getter=functools.partial(urljoin, url))
