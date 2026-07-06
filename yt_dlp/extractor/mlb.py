import json
import re
import time
import uuid

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    join_nonempty,
    jwt_decode_hs256,
    parse_duration,
    parse_iso8601,
    try_get,
    url_or_none,
    urlencode_postdata,
)
from ..utils.traversal import traverse_obj


class MLBBaseIE(InfoExtractor):
    def _real_extract(self, url):
        display_id = self._match_id(url)
        video = self._download_video_data(display_id)
        video_id = video['id']
        title = video['title']
        feed = self._get_feed(video)

        formats = []
        for playback in (feed.get('playbacks') or []):
            playback_url = playback.get('url')
            if not playback_url:
                continue
            name = playback.get('name')
            ext = determine_ext(playback_url)
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    playback_url, video_id, 'mp4',
                    'm3u8_native', m3u8_id=name, fatal=False))
            else:
                f = {
                    'format_id': name,
                    'url': playback_url,
                }
                mobj = re.search(r'_(\d+)K_(\d+)X(\d+)', name)
                if mobj:
                    f.update({
                        'height': int(mobj.group(3)),
                        'tbr': int(mobj.group(1)),
                        'width': int(mobj.group(2)),
                    })
                mobj = re.search(r'_(\d+)x(\d+)_(\d+)_(\d+)K\.mp4', playback_url)
                if mobj:
                    f.update({
                        'fps': int(mobj.group(3)),
                        'height': int(mobj.group(2)),
                        'tbr': int(mobj.group(4)),
                        'width': int(mobj.group(1)),
                    })
                formats.append(f)

        thumbnails = []
        for cut in (try_get(feed, lambda x: x['image']['cuts'], list) or []):
            src = cut.get('src')
            if not src:
                continue
            thumbnails.append({
                'height': int_or_none(cut.get('height')),
                'url': src,
                'width': int_or_none(cut.get('width')),
            })

        language = (video.get('language') or 'EN').lower()

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'description': video.get('description'),
            'duration': parse_duration(feed.get('duration')),
            'thumbnails': thumbnails,
            'timestamp': parse_iso8601(video.get(self._TIMESTAMP_KEY)),
            'subtitles': self._extract_mlb_subtitles(feed, language),
        }


class MLBIE(MLBBaseIE):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:[\da-z_-]+\.)*mlb\.com/
                        (?:
                            (?:
                                (?:[^/]+/)*video/[^/]+/c-|
                                (?:
                                    shared/video/embed/(?:embed|m-internal-embed)\.html|
                                    (?:[^/]+/)+(?:play|index)\.jsp|
                                )\?.*?\bcontent_id=
                            )
                            (?P<id>\d+)
                        )
                    '''
    _EMBED_REGEX = [
        r'<iframe[^>]+?src=(["\'])(?P<url>https?://m(?:lb)?\.mlb\.com/shared/video/embed/embed\.html\?.+?)\1',
        r'data-video-link=["\'](?P<url>http://m\.mlb\.com/video/[^"\']+)',
    ]
    _TESTS = [{
        'url': 'https://www.mlb.com/mariners/video/ackleys-spectacular-catch/c-34698933',
        'info_dict': {
            'id': '34698933',
            'ext': 'mp4',
            'title': 'Ackley\'s spectacular catch',
            'description': 'md5:7f5a981eb4f3cbc8daf2aeffa2215bf0',
            'duration': 66,
            'timestamp': 1405995000,
            'upload_date': '20140722',
            'thumbnail': r're:https?://.+\.jpg',
        },
    }, {
        'url': 'https://www.mlb.com/video/stanton-prepares-for-derby/c-34496663',
        'info_dict': {
            'id': '34496663',
            'ext': 'mp4',
            'title': 'Stanton prepares for Derby',
            'description': 'md5:d00ce1e5fd9c9069e9c13ab4faedfa57',
            'duration': 46,
            'timestamp': 1405120200,
            'upload_date': '20140711',
            'thumbnail': r're:https?://.+\.jpg',
        },
    }, {
        'url': 'https://www.mlb.com/video/cespedes-repeats-as-derby-champ/c-34578115',
        'info_dict': {
            'id': '34578115',
            'ext': 'mp4',
            'title': 'Cespedes repeats as Derby champ',
            'description': 'md5:08df253ce265d4cf6fb09f581fafad07',
            'duration': 488,
            'timestamp': 1405414336,
            'upload_date': '20140715',
            'thumbnail': r're:https?://.+\.jpg',
        },
    }, {
        'url': 'https://www.mlb.com/video/bautista-on-home-run-derby/c-34577915',
        'info_dict': {
            'id': '34577915',
            'ext': 'mp4',
            'title': 'Bautista on Home Run Derby',
            'description': 'md5:b80b34031143d0986dddc64a8839f0fb',
            'duration': 52,
            'timestamp': 1405405122,
            'upload_date': '20140715',
            'thumbnail': r're:https?://.+\.jpg',
        },
    }, {
        'url': 'https://www.mlb.com/video/hargrove-homers-off-caldwell/c-1352023483?tid=67793694',
        'only_matching': True,
    }, {
        'url': 'http://m.mlb.com/shared/video/embed/embed.html?content_id=35692085&topic_id=6479266&width=400&height=224&property=mlb',
        'only_matching': True,
    }, {
        'url': 'http://mlb.mlb.com/shared/video/embed/embed.html?content_id=36599553',
        'only_matching': True,
    }, {
        'url': 'http://mlb.mlb.com/es/video/play.jsp?content_id=36599553',
        'only_matching': True,
    }, {
        'url': 'https://www.mlb.com/cardinals/video/piscottys-great-sliding-catch/c-51175783',
        'only_matching': True,
    }, {
        # From http://m.mlb.com/news/article/118550098/blue-jays-kevin-pillar-goes-spidey-up-the-wall-to-rob-tim-beckham-of-a-homer
        'url': 'http://mlb.mlb.com/shared/video/embed/m-internal-embed.html?content_id=75609783&property=mlb&autoplay=true&hashmode=false&siteSection=mlb/multimedia/article_118550098/article_embed&club=mlb',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://www.mlbdailydish.com/2013/2/25/4028804/mlb-classic-video-vault-open-watch-embed-share',
        'info_dict': {
            'id': 'mlb-classic-video-vault-open-watch-embed-share',
            'title': 'MLB Classic vault is open! Don\'t avert your eyes!',
            'age_limit': 0,
            'description': 'All the video needed to hold you over until real baseball starts next month.',
            'thumbnail': r're:https?://cdn\.vox-cdn\.com/thumbor/.+\.jpg',
        },
        'playlist_count': 3,
    }]
    _TIMESTAMP_KEY = 'date'

    @staticmethod
    def _get_feed(video):
        return video

    @staticmethod
    def _extract_mlb_subtitles(feed, language):
        subtitles = {}
        for keyword in (feed.get('keywordsAll') or []):
            keyword_type = keyword.get('type')
            if keyword_type and keyword_type.startswith('closed_captions_location_'):
                cc_location = keyword.get('value')
                if cc_location:
                    subtitles.setdefault(language, []).append({
                        'url': cc_location,
                    })
        return subtitles

    def _download_video_data(self, display_id):
        return self._download_json(
            f'http://content.mlb.com/mlb/item/id/v1/{display_id}/details/web-v1.json',
            display_id)


class MLBVideoIE(MLBBaseIE):
    _VALID_URL = r'https?://(?:www\.)?mlb\.com/(?:[^/]+/)*video/(?P<id>[^/?&#]+)'
    _TESTS = [{
        'url': 'https://www.mlb.com/mariners/video/ackley-s-spectacular-catch-c34698933',
        'info_dict': {
            'id': 'c04a8863-f569-42e6-9f87-992393657614',
            'ext': 'mp4',
            'title': 'Ackley\'s spectacular catch',
            'description': 'md5:7f5a981eb4f3cbc8daf2aeffa2215bf0',
            'duration': 66,
            'timestamp': 1405995000,
            'upload_date': '20140722',
            'thumbnail': r're:https?://.+',
        },
    }]
    _TIMESTAMP_KEY = 'timestamp'

    @classmethod
    def suitable(cls, url):
        return False if MLBIE.suitable(url) else super().suitable(url)

    @staticmethod
    def _get_feed(video):
        return video['feeds'][0]

    @staticmethod
    def _extract_mlb_subtitles(feed, language):
        subtitles = {}
        for cc_location in (feed.get('closedCaptions') or []):
            subtitles.setdefault(language, []).append({
                'url': cc_location,
            })

    def _download_video_data(self, display_id):
        # https://www.mlb.com/data-service/en/videos/[SLUG]
        return self._download_json(
            'https://fastball-gateway.mlb.com/graphql',
            display_id, query={
                'query': '''{
  mediaPlayback(ids: "%s") {
    description
    feeds(types: CMS) {
      closedCaptions
      duration
      image {
        cuts {
          width
          height
          src
        }
      }
      playbacks {
        name
        url
      }
    }
    id
    timestamp
    title
  }
}''' % display_id,  # noqa: UP031
            })['data']['mediaPlayback'][0]


class MLBTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?mlb\.com/tv/g(?P<id>\d{6})'
    _NETRC_MACHINE = 'mlb'
    _TESTS = [{
        'url': 'https://www.mlb.com/tv/g661581/vee2eff5f-a7df-4c20-bdb4-7b926fa12638',
        'info_dict': {
            'id': '661581',
            'ext': 'mp4',
            'title': '2022-07-02 - St. Louis Cardinals @ Philadelphia Phillies',
            'release_date': '20220702',
            'release_timestamp': 1656792300,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # makeup game: has multiple dates, need to avoid games with 'rescheduleDate'
        'url': 'https://www.mlb.com/tv/g747039/vd22541c4-5a29-45f7-822b-635ec041cf5e',
        'info_dict': {
            'id': '747039',
            'ext': 'mp4',
            'title': '2024-07-29 - Toronto Blue Jays @ Baltimore Orioles',
            'release_date': '20240729',
            'release_timestamp': 1722280200,
        },
        'params': {'skip_download': 'm3u8'},
    }]
    _GRAPHQL_INIT_QUERY = '''\
mutation initSession($device: InitSessionInput!, $clientType: ClientType!, $experience: ExperienceTypeInput) {
    initSession(device: $device, clientType: $clientType, experience: $experience) {
        deviceId
        sessionId
        entitlements {
            code
        }
        location {
            countryCode
            regionName
            zipCode
            latitude
            longitude
        }
        clientExperience
        features
    }
  }'''
    _GRAPHQL_PLAYBACK_QUERY = '''\
mutation initPlaybackSession(
        $adCapabilities: [AdExperienceType]
        $mediaId: String!
        $deviceId: String!
        $sessionId: String!
        $quality: PlaybackQuality
    ) {
        initPlaybackSession(
            adCapabilities: $adCapabilities
            mediaId: $mediaId
            deviceId: $deviceId
            sessionId: $sessionId
            quality: $quality
        ) {
            playbackSessionId
            playback {
                url
                token
                expiration
                cdn
            }
        }
    }'''
    _APP_VERSION = '7.8.2'
    _device_id = None
    _session_id = None
    _access_token = None
    _token_expiry = 0

    @property
    def _api_headers(self):
        if (self._token_expiry - 120) <= time.time():
            self.write_debug('Access token has expired; re-logging in')
            self._perform_login(*self._get_login_info())
        return {'Authorization': f'Bearer {self._access_token}'}

    def _real_initialize(self):
        if not self._access_token:
            self.raise_login_required(
                'All videos are only available to registered users', method='password')

    def _set_device_id(self, username):
        if self._device_id:
            return
        device_id_cache = self.cache.load(self._NETRC_MACHINE, 'device_ids', default={})
        self._device_id = device_id_cache.get(username)
        if self._device_id:
            return
        self._device_id = str(uuid.uuid4())
        device_id_cache[username] = self._device_id
        self.cache.store(self._NETRC_MACHINE, 'device_ids', device_id_cache)

    def _perform_login(self, username, password):
        try:
            self._access_token = self._download_json(
                'https://ids.mlb.com/oauth2/aus1m088yK07noBfh356/v1/token', None,
                'Logging in', 'Unable to log in', headers={
                    'User-Agent': 'okhttp/3.12.1',
                    'Content-Type': 'application/x-www-form-urlencoded',
                }, data=urlencode_postdata({
                    'grant_type': 'password',
                    'username': username,
                    'password': password,
                    'scope': 'openid offline_access',
                    'client_id': '0oa3e1nutA1HLzAKG356',
                }))['access_token']
        except ExtractorError as error:
            if isinstance(error.cause, HTTPError) and error.cause.status == 400:
                raise ExtractorError('Invalid username or password', expected=True)
            raise

        self._token_expiry = traverse_obj(self._access_token, ({jwt_decode_hs256}, 'exp', {int})) or 0
        self._set_device_id(username)

        self._session_id = self._call_api({
            'operationName': 'initSession',
            'query': self._GRAPHQL_INIT_QUERY,
            'variables': {
                'device': {
                    'appVersion': self._APP_VERSION,
                    'deviceFamily': 'desktop',
                    'knownDeviceId': self._device_id,
                    'languagePreference': 'ENGLISH',
                    'manufacturer': '',
                    'model': '',
                    'os': '',
                    'osVersion': '',
                },
                'clientType': 'WEB',
            },
        }, None, 'session ID')['data']['initSession']['sessionId']

    def _call_api(self, data, video_id, description='GraphQL JSON', fatal=True):
        return self._download_json(
            'https://media-gateway.mlb.com/graphql', video_id,
            f'Downloading {description}', f'Unable to download {description}', fatal=fatal,
            headers={
                **self._api_headers,
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'x-client-name': 'WEB',
                'x-client-version': self._APP_VERSION,
            }, data=json.dumps(data, separators=(',', ':')).encode())

    def _extract_formats_and_subtitles(self, broadcast, video_id):
        feed = traverse_obj(broadcast, ('homeAway', {str.title}))
        medium = traverse_obj(broadcast, ('type', {str}))
        language = traverse_obj(broadcast, ('language', {str.lower}))
        format_id = join_nonempty(feed, medium, language)

        response = self._call_api({
            'operationName': 'initPlaybackSession',
            'query': self._GRAPHQL_PLAYBACK_QUERY,
            'variables': {
                'adCapabilities': ['GOOGLE_STANDALONE_AD_PODS'],
                'deviceId': self._device_id,
                'mediaId': broadcast['mediaId'],
                'quality': 'PLACEHOLDER',
                'sessionId': self._session_id,
            },
        }, video_id, f'{format_id} broadcast JSON', fatal=False)

        playback = traverse_obj(response, ('data', 'initPlaybackSession', 'playback', {dict}))
        m3u8_url = traverse_obj(playback, ('url', {url_or_none}))
        token = traverse_obj(playback, ('token', {str}))

        if not (m3u8_url and token):
            errors = '; '.join(traverse_obj(response, ('errors', ..., 'message', {str})))
            if errors:  # Only warn when 'blacked out' or 'not entitled'; radio formats may be available
                self.report_warning(f'API returned errors for {format_id}: {errors}')
            else:
                self.report_warning(f'No formats available for {format_id} broadcast; skipping')
            return [], {}

        fmts, subs = self._extract_m3u8_formats_and_subtitles(
            m3u8_url, video_id, 'mp4', m3u8_id=format_id, fatal=False)
        for fmt in fmts:
            fmt.setdefault('format_note', join_nonempty(feed, medium, delim=' '))
            fmt.setdefault('language', language)
            if fmt.get('vcodec') == 'none' and fmt['language'] == 'en':
                fmt['source_preference'] = 10

        return fmts, subs

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._download_json(
            'https://statsapi.mlb.com/api/v1/schedule', video_id, query={
                'gamePk': video_id,
                'hydrate': 'broadcasts(all),statusFlags',
            })
        metadata = traverse_obj(data, (
            'dates', ..., 'games',
            lambda _, v: str(v['gamePk']) == video_id and not v.get('rescheduleDate'), any))

        broadcasts = traverse_obj(metadata, (
            'broadcasts', lambda _, v: v['mediaId'] and v['mediaState']['mediaStateCode'] != 'MEDIA_OFF'))

        formats, subtitles = [], {}
        for broadcast in broadcasts:
            fmts, subs = self._extract_formats_and_subtitles(broadcast, video_id)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        return {
            'id': video_id,
            'title': join_nonempty(
                traverse_obj(metadata, ('officialDate', {str})),
                traverse_obj(metadata, ('teams', ('away', 'home'), 'team', 'name', {str}, all, {' @ '.join})),
                delim=' - '),
            'is_live': traverse_obj(broadcasts, (..., 'mediaState', 'mediaStateCode', {str}, any)) == 'MEDIA_ON',
            'release_timestamp': traverse_obj(metadata, ('gameDate', {parse_iso8601})),
            'formats': formats,
            'subtitles': subtitles,
        }


class MLBArticleIE(InfoExtractor):
    _VALID_URL = r'https?://www\.mlb\.com/news/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.mlb.com/news/manny-machado-robs-guillermo-heredia-reacts',
        'info_dict': {
            'id': '36db7394-343c-4ea3-b8ca-ead2e61bca9a',
            'title': 'Machado\'s grab draws hilarious irate reaction',
            'modified_timestamp': 1675888370,
            'description': 'md5:a19d4eb0487b2cb304e9a176f6b67676',
            'modified_date': '20230208',
        },
        'playlist_mincount': 2,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        apollo_cache_json = self._search_json(r'window\.initState\s*=', webpage, 'window.initState', display_id)['apolloCache']

        content_real_info = traverse_obj(
            apollo_cache_json, ('ROOT_QUERY', lambda k, _: k.startswith('getArticle')), get_all=False)

        return self.playlist_from_matches(
            traverse_obj(content_real_info, ('parts', lambda _, v: v['__typename'] == 'Video' or v['type'] == 'video')),
            getter=lambda x: f'https://www.mlb.com/video/{x["slug"]}',
            ie=MLBVideoIE, playlist_id=content_real_info.get('translationId'),
            title=self._html_search_meta('og:title', webpage),
            description=content_real_info.get('summary'),
            modified_timestamp=parse_iso8601(content_real_info.get('lastUpdatedDate')))
