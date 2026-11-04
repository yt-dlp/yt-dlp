import json
import time

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    determine_ext,
    float_or_none,
    int_or_none,
    join_nonempty,
    jwt_decode_hs256,
    parse_duration,
    parse_iso8601,
    parse_qs,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class SBSBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'sbs'
    _ACCESS_TOKEN = None
    _REFRESH_TOKEN = None
    _LOGIN_API_BASE = 'https://auth.sbs.com.au'
    _LOGIN_API_KEY = '74165a3a-0ae7-4d27-ac1a-e71e81062a89'
    _CACHE_KEY = 'sbs_data'
    _REFRESH_COOKIE = 'auth.refresh-token'

    def _is_jwt_expired(self, token):
        return jwt_decode_hs256(token)['exp'] - time.time() < 300

    def _parse_and_cache_login_response(self, data=None):
        if not data:
            self._ACCESS_TOKEN, self._REFRESH_TOKEN = self.cache.load(self._NETRC_MACHINE, self._CACHE_KEY, default=[None, None])
            if self._ACCESS_TOKEN and not self._is_jwt_expired(self._ACCESS_TOKEN):
                return self._ACCESS_TOKEN
            elif self._REFRESH_TOKEN:
                return self._refresh_access_token()
            return False

        self._ACCESS_TOKEN = data.get('accessToken')
        if not self._ACCESS_TOKEN:
            raise ExtractorError('Login failed unable to get access token')
        if refresh_cookie := self._get_cookies('https://sbs.com.au').get(self._REFRESH_COOKIE):
            self._REFRESH_TOKEN = refresh_cookie.value
        self.cache.store(self._NETRC_MACHINE, self._CACHE_KEY, [self._ACCESS_TOKEN, self._REFRESH_TOKEN])
        return self._ACCESS_TOKEN, self._REFRESH_TOKEN

    def _refresh_access_token(self):
        if not self._REFRESH_TOKEN:
            self.report_warning('Unable to get refresh token')
            self._perform_login(*self._get_login_info(), force=True)
            return
        self._set_cookie('.sbs.com.au', self._REFRESH_COOKIE, self._REFRESH_TOKEN)
        try:
            data = self._download_json(
                f'{self._LOGIN_API_BASE}/refresh',
                None, 'Refreshing access token',
                data=json.dumps({
                    'deviceName': 'Chrome - Linux',
                }).encode(),
                headers={
                    'x-api-key': self._LOGIN_API_KEY,
                },
            )
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status in (400, 401, 403):
                self.report_warning('Unable to get refresh token')
                self._perform_login(*self._get_login_info(), force=True)
                return
            raise
        return self._parse_and_cache_login_response(data)

    def _perform_login(self, username, password, force=False):
        if not force:
            if self._parse_and_cache_login_response():
                return
        try:
            login = self._download_json(
                f'{self._LOGIN_API_BASE}/login',
                None, 'Logged in',
                data=json.dumps({
                    'deviceName': 'Chrome - Linux',
                    'email': username,
                    'password': password,
                }).encode(),
                headers={
                    'x-api-key': self._LOGIN_API_KEY,
                },
            )
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 401:
                raise ExtractorError('Invalid username/password')
            raise
        return self._parse_and_cache_login_response(login)

    def _call_api(self, api, video_id, note='Downloading JSON metadata', headers=None, **kwargs):
        headers = headers or {}
        if access_token := self._ACCESS_TOKEN:
            headers['Authorization'] = f'Bearer {access_token}'
        return self._download_json(url_or_request=api, video_id=video_id, note=note, headers=headers, **kwargs)


class SBSIE(SBSBaseIE):
    IE_DESC = 'sbs.com.au'
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?sbs\.com\.au/(?:
            ondemand(?:
                /video/(?:single/)?|
                /(?:movie|tv-program)/[^/]+/|
                /(?:tv|news)-series/(?:[^/]+/){3}|
                .*?\bplay=|/watch/
            )|news/(?:embeds/)?video/
        )(?P<id>[0-9]+)'''
    _EMBED_REGEX = [r'''(?x)]
            (?:
                <meta\s+property="og:video"\s+content=|
                <iframe[^>]+?src=
            )
            ("|')(?P<url>https?://(?:www\.)?sbs\.com\.au/ondemand/video/.+?)\1''']

    _TESTS = [{
        # Original URL is handled by the generic IE which finds the iframe:
        # http://www.sbs.com.au/thefeed/blog/2014/08/21/dingo-conservation
        'url': 'http://www.sbs.com.au/ondemand/video/single/320403011771/?source=drupal&vertical=thefeed',
        'md5': '31f84a7a19b53635db63c73f8ab0c4a7',
        'info_dict': {
            'id': '320403011771',  # '_rFBPRPO4pMR',
            'ext': 'mp4',
            'title': 'Dingo Conservation (The Feed)',
            'description': 'md5:f250a9856fca50d22dec0b5b8015f8a5',
            'thumbnail': r're:https?://.*\.jpg',
            'duration': 308,
            'timestamp': 1408613220,
            'upload_date': '20140821',
            'uploader': 'SBSC',
        },
        'skip': '400 Bad Bad Request',
        'expected_warnings': ['Unable to download JSON metadata'],
    }, {
        'url': 'https://www.sbs.com.au/ondemand/tv-series/hudson-and-rex/season-8/hudson-and-rex-s8-ep1/2487482947557',
        'info_dict': {
            'id': '2487482947557',
            'ext': 'mp4',
            'title': 'Hudson & Rex S8 Ep1 - Into The Wilds',
            'description': 'md5:f70e534ea13ecd54bb944b0a5d032b37',
            'uploader': 'SBSC',
            'age_limit': 14,
            'duration': 2507.0,
            'tags': ['Mature Themes', 'Violence'],
            'series': 'Hudson & Rex',
            'series_id': '06f4f06e-9e32-578a-823f-edc27cec5f2b',
            'season': 'Season 8',
            'season_number': 8,
            'episode': 'Episode 1',
            'episode_number': 1,
            'release_year': 2025,
            'thumbnail': r're:https?://image.pr.sbsod.com/.+',
        },
        'params': {'skip_download': 'm3u8'},
        'skip': 'Login required',
    }, {
        'url': 'http://www.sbs.com.au/ondemand/video/320403011771/Dingo-Conservation-The-Feed',
        'only_matching': True,
    }, {
        'url': 'http://www.sbs.com.au/news/video/471395907773/The-Feed-July-9',
        'only_matching': True,
    }, {
        'url': 'https://www.sbs.com.au/ondemand/?play=1836638787723',
        'only_matching': True,
    }, {
        'url': 'https://www.sbs.com.au/ondemand/program/inside-windsor-castle?play=1283505731842',
        'only_matching': True,
    }, {
        'url': 'https://www.sbs.com.au/news/embeds/video/1840778819866',
        'only_matching': True,
    }, {
        'url': 'https://www.sbs.com.au/ondemand/watch/1698704451971',
        'only_matching': True,
    }, {
        'url': 'https://www.sbs.com.au/ondemand/movie/coherence/1469404227931',
        'only_matching': True,
    }, {
        'note': 'Live stream',
        'url': 'https://www.sbs.com.au/ondemand/video/1726824003663/sbs-24x7-live-stream-nsw',
        'only_matching': True,
    }, {
        'url': 'https://www.sbs.com.au/ondemand/news-series/dateline/dateline-2022/dateline-s2022-ep26/2072245827515',
        'only_matching': True,
    }, {
        'url': 'https://www.sbs.com.au/ondemand/tv-series/the-handmaids-tale/season-5/the-handmaids-tale-s5-ep1/2065631811776',
        'only_matching': True,
    }, {
        'url': 'https://www.sbs.com.au/ondemand/tv-program/autun-romes-forgotten-sister/2116212803602',
        'only_matching': True,
    }]

    _GEO_COUNTRIES = ['AU']
    _GEO_BYPASS = False
    _AUS_TV_PARENTAL_GUIDELINES = {
        'P': 0,
        'C': 7,
        'G': 0,
        'PG': 0,
        'M': 14,
        'MA15+': 15,
        'MAV15+': 15,
        'R18+': 18,
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        try:
            media = self._call_api(
                f'https://playback.pr.sbsod.com/stream/{video_id}',
                video_id,
                data=json.dumps({
                    'deviceClass': 'web',
                    'streamOptions': {'audio': 'demuxed'},
                    'streamProviders': ['HLS'],
                }).encode(),
            )
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status in (401, 400):
                if self._ACCESS_TOKEN:
                    self._refresh_access_token()
                self.raise_login_required()
            raise

        formats, subtitles = [], {}
        for fmt_url in traverse_obj(media, ('streamProviders', ..., 'url')):
            ext = determine_ext(fmt_url)
            if ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(fmt_url, video_id)
            elif ext == 'mpd':
                fmts, subs = self._extract_mpd_formats_and_subtitles(fmt_url, video_id)
            else:
                continue
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        for sub in traverse_obj(media, ('streamProviders', ..., 'textTracks', lambda _, y: y.get('url'))):
            lang = sub.get('lang', 'en')
            ext = traverse_obj(sub,
                               ('format', {lambda x: 'vtt' if x == 'WebVTT' else None}),
                               ('url', {parse_qs}, 'format', 0),
                               ('url', {determine_ext(default_ext='vtt')}),
                               )
            subtitles.setdefault(lang, []).append({
                **traverse_obj(sub, {
                    'url': ('url', {url_or_none}),
                    'name': ('name', {str_or_none}),
                }),
                'ext': ext,
            })

        media.update(self._download_json(
            f'https://catalogue.pr.sbsod.com/mpx-media/{video_id}',
            video_id, fatal=not media) or {})

        # For named episodes, use the catalogue's title to set episode, rather than generic 'Episode N'.
        if traverse_obj(media, ('partOfSeries', {dict})):
            media['epName'] = traverse_obj(media, ('title', {str}))

        # Need to set different language for forced subs or else they have priority over full subs
        fixed_subtitles = {}
        for lang, subs in subtitles.items():
            for sub in subs:
                fixed_lang = lang
                if sub['url'].lower().endswith('_fe.vtt'):
                    fixed_lang += '-forced'
                fixed_subtitles.setdefault(fixed_lang, []).append(sub)

        thumbnails = []
        for thumb in traverse_obj(media, ('images', lambda _, y: y.get('id'))):
            tid = thumb.get('id')
            thumb_root = 'https://image.pr.sbsod.com'
            width, height, label = self._search_regex(
                r'\|(?P<w>\d+)\|(?P<h>\d+)\|(?P<l>[^\|]+)',
                thumb.get('category'),
                'thumbail info',
                group=('w', 'h', 'l'),
                default=[None, None, None],
            )
            thumbnails.append({
                'url': join_nonempty(thumb_root, tid, delim='/'),
                'width': int_or_none(width),
                'height': int_or_none(height),
                'id': f'{label}-{tid[:5]}',
            })

        return {
            'id': video_id,
            **traverse_obj(media, {
                'title': (('cdpTitle', 'title'), {str}),
                'description': ('description', {str}),
                'channel': ('taxonomy', 'channel', 'name', {str}),
                'series': ((('partOfSeries', 'name'), 'seriesTitle'), {str}),
                'series_id': ((('partOfSeries', 'uuid'), 'seriesID'), {str}),
                'season_number': ('seasonNumber', {int_or_none}),
                'episode': ('epName', {str}),
                'episode_number': ('episodeNumber', {int_or_none}),
                'timestamp': (('datePublished', ('publication', 'startDate')), {parse_iso8601}),
                'release_year': ('releaseYear', {int_or_none}),
                'duration': ('duration', ({float_or_none}, {parse_duration})),
                'is_live': ('liveStream', {bool}),
                'age_limit': (
                    ('classificationID', 'contentRating'), {str.upper}, {self._AUS_TV_PARENTAL_GUIDELINES.get}),
            }, get_all=False),
            **traverse_obj(media, {
                'categories': (('genres', ...), ('taxonomy', ('genre', 'subgenre'), 'name'), {str}),
                'tags': (('consumerAdviceTexts', ('sbsSubCertification', 'consumerAdvice')), ..., {str}),
            }),
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': fixed_subtitles,
            'uploader': 'SBSC',
        }
