import functools
import hashlib
import hmac
import json
import re
import time
import uuid

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    determine_ext,
    filter_dict,
    int_or_none,
    join_nonempty,
    jwt_decode_hs256,
    parse_iso8601,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import require, traverse_obj


class HotStarBaseIE(InfoExtractor):
    _TOKEN_NAME = 'userUP'
    _BASE_URL = 'https://www.hotstar.com'
    _API_URL = 'https://api.hotstar.com'
    _API_URL_V2 = 'https://apix.hotstar.com/v2'
    _AKAMAI_ENCRYPTION_KEY = b'\x05\xfc\x1a\x01\xca\xc9\x4b\xc4\x12\xfc\x53\x12\x07\x75\xf9\xee'

    _FREE_HEADERS = {
        'user-agent': 'Hotstar;in.startv.hotstar/25.06.30.0.11580 (Android/12)',
        'x-hs-client': 'platform:android;app_id:in.startv.hotstar;app_version:25.06.30.0;os:Android;os_version:12;schema_version:0.0.1523',
        'x-hs-platform': 'android',
    }
    _SUB_HEADERS = {
        'user-agent': 'Disney+;in.startv.hotstar.dplus.tv/23.08.14.4.2915 (Android/13)',
        'x-hs-client': 'platform:androidtv;app_id:in.startv.hotstar.dplus.tv;app_version:23.08.14.4;os:Android;os_version:13;schema_version:0.0.970',
        'x-hs-platform': 'androidtv',
    }

    def _has_active_subscription(self, cookies, server_time):
        server_time = int_or_none(server_time) or int(time.time())
        expiry = traverse_obj(cookies, (
            self._TOKEN_NAME, 'value', {jwt_decode_hs256}, 'sub', {json.loads},
            'subscriptions', 'in', ..., 'expiry', {parse_iso8601}, all, {max})) or 0
        return expiry > server_time

    def _call_api_v1(self, path, *args, **kwargs):
        return self._download_json(
            f'{self._API_URL}/o/v1/{path}', *args, **kwargs,
            headers={'x-country-code': 'IN', 'x-platform-code': 'PCTV'})

    def _call_api_impl(self, path, video_id, query, cookies=None, st=None):
        st = int_or_none(st) or int(time.time())
        exp = st + 6000
        auth = f'st={st}~exp={exp}~acl=/*'
        auth += '~hmac=' + hmac.new(self._AKAMAI_ENCRYPTION_KEY, auth.encode(), hashlib.sha256).hexdigest()
        response = self._download_json(
            f'{self._API_URL_V2}/{path}', video_id, query=query,
            headers=filter_dict({
                **(self._SUB_HEADERS if self._has_active_subscription(cookies, st) else self._FREE_HEADERS),
                'hotstarauth': auth,
                'x-hs-usertoken': traverse_obj(cookies, (self._TOKEN_NAME, 'value')),
                'x-hs-device-id': traverse_obj(cookies, ('deviceId', 'value')) or str(uuid.uuid4()),
                'content-type': 'application/json',
            }))

        if not traverse_obj(response, ('success', {dict})):
            raise ExtractorError('API call was unsuccessful')
        return response['success']

    def _call_api_v2(self, path, video_id, content_type, cookies=None, st=None):
        return self._call_api_impl(f'{path}', video_id, query={
            'content_id': video_id,
            'filters': f'content_type={content_type}',
            'client_capabilities': json.dumps({
                'package': ['dash', 'hls'],
                'container': ['fmp4', 'fmp4br', 'ts'],
                'ads': ['non_ssai', 'ssai'],
                'audio_channel': ['stereo', 'dolby51', 'atmos'],
                'encryption': ['plain', 'widevine'],  # wv only so we can raise appropriate error
                'video_codec': ['h264', 'h265'],
                'video_codec_non_secure': ['h264', 'h265', 'vp9'],
                'ladder': ['phone', 'tv', 'full'],
                'resolution': ['hd', '4k'],
                'true_resolution': ['hd', '4k'],
                'dynamic_range': ['sdr', 'hdr'],
            }, separators=(',', ':')),
            'drm_parameters': json.dumps({
                'widevine_security_level': ['SW_SECURE_DECODE', 'SW_SECURE_CRYPTO'],
                'hdcp_version': ['HDCP_V2_2', 'HDCP_V2_1', 'HDCP_V2', 'HDCP_V1'],
            }, separators=(',', ':')),
        }, cookies=cookies, st=st)

    @staticmethod
    def _parse_metadata_v1(video_data):
        return traverse_obj(video_data, {
            'id': ('contentId', {str}),
            'title': ('title', {str}),
            'description': ('description', {str}),
            'duration': ('duration', {int_or_none}),
            'timestamp': (('broadcastDate', 'startDate'), {int_or_none}, any),
            'release_year': ('year', {int_or_none}),
            'channel': ('channelName', {str}),
            'channel_id': ('channelId', {int}, {str_or_none}),
            'series': ('showName', {str}),
            'season': ('seasonName', {str}),
            'season_number': ('seasonNo', {int_or_none}),
            'season_id': ('seasonId', {int}, {str_or_none}),
            'episode': ('title', {str}),
            'episode_number': ('episodeNo', {int_or_none}),
        })

    def _fetch_page(self, path, item_id, name, query, root, page):
        results = self._call_api_v1(
            path, item_id, note=f'Downloading {name} page {page + 1} JSON', query={
                **query,
                'tao': page * self._PAGE_SIZE,
                'tas': self._PAGE_SIZE,
            })['body']['results']

        for video in traverse_obj(results, (('assets', None), 'items', lambda _, v: v['contentId'])):
            yield self.url_result(
                HotStarIE._video_url(video['contentId'], root=root), HotStarIE, **self._parse_metadata_v1(video))


class HotStarIE(HotStarBaseIE):
    IE_NAME = 'hotstar'
    IE_DESC = 'JioHotstar'
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?hotstar\.com(?:/in)?/(?!in/)
        (?:
            (?P<type>movies|sports|clips|episode|(?P<tv>tv|shows))/
            (?(tv)(?:[^/?#]+/){2}|[^?#]*)
        )?
        [^/?#]+/
        (?P<id>\d{10})
    '''

    _TESTS = [{
        'url': 'https://www.hotstar.com/can-you-not-spread-rumours/1000076273',
        'info_dict': {
            'id': '1000076273',
            'ext': 'mp4',
            'title': 'Can You Not Spread Rumours?',
            'description': 'md5:c957d8868e9bc793ccb813691cc4c434',
            'timestamp': 1447248600,
            'upload_date': '20151111',
            'duration': 381,
            'episode': 'Can You Not Spread Rumours?',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.hotstar.com/tv/ek-bhram-sarvagun-sampanna/s-2116/janhvi-targets-suman/1000234847',
        'info_dict': {
            'id': '1000234847',
            'ext': 'mp4',
            'title': 'Janhvi Targets Suman',
            'description': 'md5:78a85509348910bd1ca31be898c5796b',
            'timestamp': 1556670600,
            'upload_date': '20190501',
            'duration': 1219,
            'channel': 'StarPlus',
            'channel_id': '821',
            'series': 'Ek Bhram - Sarvagun Sampanna',
            'season': 'Chapter 1',
            'season_number': 1,
            'season_id': '1260004607',
            'episode': 'Janhvi Targets Suman',
            'episode_number': 8,
        },
        'params': {'skip_download': 'm3u8'},
    }, {  # Metadata call gets HTTP Error 504 with tas=10000
        'url': 'https://www.hotstar.com/in/shows/anupama/1260022017/anupama-anuj-share-a-moment/1000282843',
        'info_dict': {
            'id': '1000282843',
            'ext': 'mp4',
            'title': 'Anupama, Anuj Share a Moment',
            'season': 'Chapter 1',
            'description': 'md5:8d74ed2248423b8b06d5c8add4d7a0c0',
            'timestamp': 1678149000,
            'channel': 'StarPlus',
            'series': 'Anupama',
            'season_number': 1,
            'season_id': '1260022018',
            'upload_date': '20230307',
            'episode': 'Anupama, Anuj Share a Moment',
            'episode_number': 853,
            'duration': 1266,
            'channel_id': '821',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.hotstar.com/in/shows/kana-kaanum-kaalangal/1260097087/back-to-school/1260097320',
        'info_dict': {
            'id': '1260097320',
            'ext': 'mp4',
            'title': 'Back To School',
            'season': 'Chapter 1',
            'description': 'md5:b0d6a4c8a650681491e7405496fc7e13',
            'timestamp': 1650564000,
            'channel': 'Hotstar Specials',
            'series': 'Kana Kaanum Kaalangal',
            'season_number': 1,
            'season_id': '1260097089',
            'upload_date': '20220421',
            'episode': 'Back To School',
            'episode_number': 1,
            'duration': 1810,
            'channel_id': '1260003991',
        },
        'params': {'skip_download': 'm3u8'},
    }, {  # Metadata call gets HTTP Error 504 with tas=10000
        'url': 'https://www.hotstar.com/in/clips/e3-sairat-kahani-pyaar-ki/1000262286',
        'info_dict': {
            'id': '1000262286',
            'ext': 'mp4',
            'title': 'E3 - SaiRat, Kahani Pyaar Ki',
            'description': 'md5:e3b4b3203bc0c5396fe7d0e4948a6385',
            'episode': 'E3 - SaiRat, Kahani Pyaar Ki',
            'upload_date': '20210606',
            'timestamp': 1622943900,
            'duration': 5395,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.hotstar.com/in/movies/premam/1000091195',
        'info_dict': {
            'id': '1000091195',
            'ext': 'mp4',
            'title': 'Premam',
            'release_year': 2015,
            'description': 'md5:096cd8aaae8dab56524823dc19dfa9f7',
            'timestamp': 1462149000,
            'upload_date': '20160502',
            'episode': 'Premam',
            'duration': 8994,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.hotstar.com/movies/radha-gopalam/1000057157',
        'only_matching': True,
    }, {
        'url': 'https://www.hotstar.com/in/sports/cricket/follow-the-blues-2021/recap-eng-fight-back-on-day-2/1260066104',
        'only_matching': True,
    }, {
        'url': 'https://www.hotstar.com/in/sports/football/most-costly-pl-transfers-ft-grealish/1260065956',
        'only_matching': True,
    }]
    _GEO_BYPASS = False

    _TYPE = {
        'movies': 'movie',
        'sports': 'match',
        'episode': 'episode',
        'tv': 'episode',
        'shows': 'episode',
        'clips': 'content',
        None: 'content',
    }

    _CONTENT_TYPE = {
        'movie': 'MOVIE',
        'episode': 'EPISODE',
        'match': 'SPORT',
        'content': 'CLIPS',
    }

    _IGNORE_MAP = {
        'res': 'resolution',
        'vcodec': 'video_codec',
        'dr': 'dynamic_range',
    }

    _TAG_FIELDS = {
        'language': 'language',
        'acodec': 'audio_codec',
        'vcodec': 'video_codec',
    }

    @classmethod
    def _video_url(cls, video_id, video_type=None, *, slug='ignore_me', root=None):
        assert None in (video_type, root)
        if not root:
            root = join_nonempty(cls._BASE_URL, video_type, delim='/')
        return f'{root}/{slug}/{video_id}'

    def _real_extract(self, url):
        video_id, video_type = self._match_valid_url(url).group('id', 'type')
        video_type = self._TYPE[video_type]
        cookies = self._get_cookies(url)  # Cookies before any request
        if not cookies or not cookies.get(self._TOKEN_NAME):
            self.raise_login_required()

        video_data = traverse_obj(
            self._call_api_v1(f'{video_type}/detail', video_id, fatal=False, query={
                'tas': 5,  # See https://github.com/yt-dlp/yt-dlp/issues/7946
                'contentId': video_id,
            }), ('body', 'results', 'item', {dict})) or {}

        if video_data.get('drmProtected'):
            self.report_drm(video_id)

        geo_restricted = False
        formats, subs, has_drm = [], {}, False
        headers = {'Referer': f'{self._BASE_URL}/in'}
        content_type = traverse_obj(video_data, ('contentType', {str})) or self._CONTENT_TYPE[video_type]

        # See https://github.com/yt-dlp/yt-dlp/issues/396
        st = self._request_webpage(
            f'{self._BASE_URL}/in', video_id, 'Fetching server time').get_header('x-origin-date')
        watch = self._call_api_v2('pages/watch', video_id, content_type, cookies, st)
        player_config = traverse_obj(watch, (
            'page', 'spaces', 'player', 'widget_wrappers', lambda _, v: v['template'] == 'PlayerWidget',
            'widget', 'data', 'player_config', {dict}, any, {require('player config')}))

        for playback_set in traverse_obj(player_config, (
            ('media_asset', 'media_asset_v2'),
            ('primary', 'fallback'),
            all, lambda _, v: url_or_none(v['content_url']),
        )):
            tags = str_or_none(playback_set.get('playback_tags')) or ''
            if any(f'{prefix}:{ignore}' in tags
                   for key, prefix in self._IGNORE_MAP.items()
                   for ignore in self._configuration_arg(key)):
                continue

            tag_dict = dict((*t.split(':', 1), None)[:2] for t in tags.split(';'))
            if tag_dict.get('encryption') not in ('plain', None):
                has_drm = True
                continue

            format_url = re.sub(r'(?<=//staragvod)(\d)', r'web\1', playback_set['content_url'])
            ext = determine_ext(format_url)

            current_formats, current_subs = [], {}
            try:
                if 'package:hls' in tags or ext == 'm3u8':
                    current_formats, current_subs = self._extract_m3u8_formats_and_subtitles(
                        format_url, video_id, ext='mp4', headers=headers)
                elif 'package:dash' in tags or ext == 'mpd':
                    current_formats, current_subs = self._extract_mpd_formats_and_subtitles(
                        format_url, video_id, headers=headers)
                elif ext == 'f4m':
                    pass  # XXX: produce broken files
                else:
                    current_formats = [{
                        'url': format_url,
                        'width': int_or_none(playback_set.get('width')),
                        'height': int_or_none(playback_set.get('height')),
                    }]
            except ExtractorError as e:
                if isinstance(e.cause, HTTPError) and e.cause.status in (403, 474):
                    geo_restricted = True
                else:
                    self.write_debug(e)
                continue

            for f in current_formats:
                for k, v in self._TAG_FIELDS.items():
                    if not f.get(k):
                        f[k] = tag_dict.get(v)
                if f.get('vcodec') != 'none' and not f.get('dynamic_range'):
                    f['dynamic_range'] = tag_dict.get('dynamic_range')
                if f.get('acodec') != 'none' and not f.get('audio_channels'):
                    f['audio_channels'] = {
                        'stereo': 2,
                        'dolby51': 6,
                    }.get(tag_dict.get('audio_channel'))
                    if (
                        'Audio_Description' in f['format_id']
                        or 'Audio Description' in (f.get('format_note') or '')
                    ):
                        f['source_preference'] = -99 + (f.get('source_preference') or -1)
                f['format_note'] = join_nonempty(
                    tag_dict.get('ladder'),
                    tag_dict.get('audio_channel') if f.get('acodec') != 'none' else None,
                    f.get('format_note'),
                    delim=', ')

            formats.extend(current_formats)
            subs = self._merge_subtitles(subs, current_subs)

        if not formats:
            if geo_restricted:
                self.raise_geo_restricted(countries=['IN'], metadata_available=True)
            elif has_drm:
                self.report_drm(video_id)
            elif not self._has_active_subscription(cookies, st):
                self.raise_no_formats('Your account does not have access to this content', expected=True)
        self._remove_duplicate_formats(formats)
        for f in formats:
            f.setdefault('http_headers', {}).update(headers)

        return {
            **self._parse_metadata_v1(video_data),
            'id': video_id,
            'formats': formats,
            'subtitles': subs,
        }


class HotStarPrefixIE(InfoExtractor):
    """ The "hotstar:" prefix is no longer in use, but this is kept for backward compatibility """
    IE_DESC = False
    _VALID_URL = r'hotstar:(?:(?P<type>\w+):)?(?P<id>\d+)$'
    _TESTS = [{
        'url': 'hotstar:1000076273',
        'only_matching': True,
    }, {
        'url': 'hotstar:movies:1260009879',
        'info_dict': {
            'id': '1260009879',
            'ext': 'mp4',
            'title': 'Nuvvu Naaku Nachav',
            'description': 'md5:d43701b1314e6f8233ce33523c043b7d',
            'timestamp': 1567525674,
            'upload_date': '20190903',
            'duration': 10787,
            'episode': 'Nuvvu Naaku Nachav',
        },
    }, {
        'url': 'hotstar:episode:1000234847',
        'only_matching': True,
    }, {
        # contentData
        'url': 'hotstar:sports:1260065956',
        'only_matching': True,
    }, {
        # contentData
        'url': 'hotstar:sports:1260066104',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id, video_type = self._match_valid_url(url).group('id', 'type')
        return self.url_result(HotStarIE._video_url(video_id, video_type), HotStarIE, video_id)


class HotStarSeriesIE(HotStarBaseIE):
    IE_NAME = 'hotstar:series'
    _VALID_URL = r'(?P<url>https?://(?:www\.)?hotstar\.com(?:/in)?/(?:tv|shows)/[^/]+/(?P<id>\d+))/?(?:[#?]|$)'
    _TESTS = [{
        'url': 'https://www.hotstar.com/in/tv/radhakrishn/1260000646',
        'info_dict': {
            'id': '1260000646',
        },
        'playlist_mincount': 690,
    }, {
        'url': 'https://www.hotstar.com/tv/dancee-/1260050431',
        'info_dict': {
            'id': '1260050431',
        },
        'playlist_mincount': 42,
    }, {
        'url': 'https://www.hotstar.com/in/tv/mahabharat/435/',
        'info_dict': {
            'id': '435',
        },
        'playlist_mincount': 267,
    }, {  # HTTP Error 504 with tas=10000 (possibly because total size is over 1000 items?)
        'url': 'https://www.hotstar.com/in/shows/anupama/1260022017/',
        'info_dict': {
            'id': '1260022017',
        },
        'playlist_mincount': 1601,
    }]
    _PAGE_SIZE = 100

    def _real_extract(self, url):
        url, series_id = self._match_valid_url(url).group('url', 'id')
        eid = self._call_api_v1(
            'show/detail', series_id, query={'contentId': series_id})['body']['results']['item']['id']

        entries = OnDemandPagedList(functools.partial(
            self._fetch_page, 'tray/g/1/items', series_id,
            'series', {'etid': 0, 'eid': eid}, url), self._PAGE_SIZE)

        return self.playlist_result(entries, series_id)
