import functools
import itertools
import json
import re

from .common import InfoExtractor, SearchInfoExtractor
from ..networking import HEADRequest
from ..networking.exceptions import HTTPError
from ..utils import (
    KNOWN_EXTENSIONS,
    ExtractorError,
    float_or_none,
    int_or_none,
    join_nonempty,
    mimetype2ext,
    parse_qs,
    str_or_none,
    try_call,
    unified_timestamp,
    update_url_query,
    url_or_none,
    urlhandle_detect_ext,
)
from ..utils.traversal import traverse_obj


class SoundcloudEmbedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:w|player|p)\.soundcloud\.com/player/?.*?\burl=(?P<id>.+)'
    _EMBED_REGEX = [r'<iframe[^>]+src=(["\'])(?P<url>(?:https?://)?(?:w\.)?soundcloud\.com/player.+?)\1']
    _TEST = {
        # from https://www.soundi.fi/uutiset/ennakkokuuntelussa-timo-kaukolammen-station-to-station-to-station-julkaisua-juhlitaan-tanaan-g-livelabissa/
        'url': 'https://w.soundcloud.com/player/?visual=true&url=https%3A%2F%2Fapi.soundcloud.com%2Fplaylists%2F922213810&show_artwork=true&maxwidth=640&maxheight=960&dnt=1&secret_token=s-ziYey',
        'only_matching': True,
    }

    def _real_extract(self, url):
        query = parse_qs(url)
        api_url = query['url'][0]
        secret_token = query.get('secret_token')
        if secret_token:
            api_url = update_url_query(api_url, {'secret_token': secret_token[0]})
        return self.url_result(api_url)


class SoundcloudBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'soundcloud'

    _API_V2_BASE = 'https://api-v2.soundcloud.com/'
    _BASE_URL = 'https://soundcloud.com/'
    _USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36'
    _API_AUTH_QUERY_TEMPLATE = '?client_id=%s'
    _API_AUTH_URL_PW = 'https://api-auth.soundcloud.com/web-auth/sign-in/password%s'
    _API_VERIFY_AUTH_TOKEN = 'https://api-auth.soundcloud.com/connect/session%s'
    _HEADERS = {}

    _IMAGE_REPL_RE = r'-([0-9a-z]+)\.jpg'

    _ARTWORK_MAP = {
        'mini': 16,
        'tiny': 20,
        'small': 32,
        'badge': 47,
        't67x67': 67,
        'large': 100,
        't300x300': 300,
        'crop': 400,
        't500x500': 500,
        'original': 0,
    }

    _DEFAULT_FORMATS = ['http_aac', 'hls_aac', 'http_opus', 'hls_opus', 'http_mp3', 'hls_mp3']

    @functools.cached_property
    def _is_requested(self):
        return re.compile(r'|'.join(set(
            re.escape(pattern).replace(r'\*', r'.*') if pattern != 'default'
            else '|'.join(map(re.escape, self._DEFAULT_FORMATS))
            for pattern in self._configuration_arg('formats', ['default'], ie_key=SoundcloudIE)
        ))).fullmatch

    def _store_client_id(self, client_id):
        self.cache.store('soundcloud', 'client_id', client_id)

    def _update_client_id(self):
        webpage = self._download_webpage('https://soundcloud.com/', None)
        for src in reversed(re.findall(r'<script[^>]+src="([^"]+)"', webpage)):
            script = self._download_webpage(src, None, fatal=False)
            if script:
                client_id = self._search_regex(
                    r'client_id\s*:\s*"([0-9a-zA-Z]{32})"',
                    script, 'client id', default=None)
                if client_id:
                    self._CLIENT_ID = client_id
                    self._store_client_id(client_id)
                    return
        raise ExtractorError('Unable to extract client id')

    def _call_api(self, *args, **kwargs):
        non_fatal = kwargs.get('fatal') is False
        if non_fatal:
            del kwargs['fatal']
        query = kwargs.get('query', {}).copy()
        for _ in range(2):
            query['client_id'] = self._CLIENT_ID
            kwargs['query'] = query
            try:
                return self._download_json(*args, **kwargs)
            except ExtractorError as e:
                if isinstance(e.cause, HTTPError) and e.cause.status in (401, 403):
                    self._store_client_id(None)
                    self._update_client_id()
                    continue
                elif non_fatal:
                    self.report_warning(str(e))
                    return False
                raise

    def _initialize_pre_login(self):
        self._CLIENT_ID = self.cache.load('soundcloud', 'client_id') or 'a3e059563d7fd3372b49b37f00a00bcf'

    def _verify_oauth_token(self, token):
        if self._request_webpage(
                self._API_VERIFY_AUTH_TOKEN % (self._API_AUTH_QUERY_TEMPLATE % self._CLIENT_ID),
                None, note='Verifying login token...', fatal=False,
                data=json.dumps({'session': {'access_token': token}}).encode()):
            self._HEADERS['Authorization'] = f'OAuth {token}'
            self.report_login()
        else:
            self.report_warning('Provided authorization token is invalid. Continuing as guest')

    def _real_initialize(self):
        if self._HEADERS:
            return
        if token := try_call(lambda: self._get_cookies(self._BASE_URL)['oauth_token'].value):
            self._verify_oauth_token(token)

    def _perform_login(self, username, password):
        if username != 'oauth':
            raise ExtractorError(
                'Login using username and password is not currently supported. '
                'Use "--username oauth --password <oauth_token>" to login using an oauth token, '
                f'or else {self._login_hint(method="cookies")}', expected=True)
        if self._HEADERS:
            return
        self._verify_oauth_token(password)

        r'''
        def genDevId():
            def genNumBlock():
                return ''.join([str(random.randrange(10)) for i in range(6)])
            return '-'.join([genNumBlock() for i in range(4)])

        payload = {
            'client_id': self._CLIENT_ID,
            'recaptcha_pubkey': 'null',
            'recaptcha_response': 'null',
            'credentials': {
                'identifier': username,
                'password': password
            },
            'signature': self.sign(username, password, self._CLIENT_ID),
            'device_id': genDevId(),
            'user_agent': self._USER_AGENT
        }

        response = self._call_api(
            self._API_AUTH_URL_PW % (self._API_AUTH_QUERY_TEMPLATE % self._CLIENT_ID),
            None, note='Verifying login token...', fatal=False,
            data=json.dumps(payload).encode())

        if token := traverse_obj(response, ('session', 'access_token', {str})):
            self._HEADERS['Authorization'] = f'OAuth {token}'
            self.report_login()
            return

        raise ExtractorError('Unable to get access token, login may have failed', expected=True)
        '''

    # signature generation
    def sign(self, user, pw, clid):
        a = 33
        i = 1
        s = 440123
        w = 117
        u = 1800000
        l = 1042
        b = 37
        k = 37
        c = 5
        n = '0763ed7314c69015fd4a0dc16bbf4b90'  # _KEY
        y = '8'  # _REV
        r = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36'  # _USER_AGENT
        e = user  # _USERNAME
        t = clid  # _CLIENT_ID

        d = '-'.join([str(mInt) for mInt in [a, i, s, w, u, l, b, k]])
        h = n + y + d + r + e + t + d + n

        m = 8011470

        for f in range(len(h)):
            m = (m >> 1) + ((1 & m) << 23)
            m += ord(h[f])
            m &= 16777215

        # c is not even needed
        return f'{y}:{d}:{m:x}:{c}'

    def _extract_info_dict(self, info, full_title=None, secret_token=None, extract_flat=False):
        track_id = str(info['id'])

        format_urls = set()
        formats = []
        query = {'client_id': self._CLIENT_ID}
        if secret_token:
            query['secret_token'] = secret_token

        if not extract_flat and info.get('downloadable') and info.get('has_downloads_left'):
            try:
                # Do not use _call_api(); HTTP Error codes have different meanings for this request
                download_data = self._download_json(
                    f'{self._API_V2_BASE}tracks/{track_id}/download', track_id,
                    'Downloading original download format info JSON', query=query, headers=self._HEADERS)
            except ExtractorError as e:
                if isinstance(e.cause, HTTPError) and e.cause.status == 401:
                    self.report_warning(
                        'Original download format is only available '
                        f'for registered users. {self._login_hint()}')
                elif isinstance(e.cause, HTTPError) and e.cause.status == 403:
                    self.write_debug('Original download format is not available for this client')
                else:
                    self.report_warning(e.msg)
                download_data = None

            if redirect_url := traverse_obj(download_data, ('redirectUri', {url_or_none})):
                urlh = self._request_webpage(
                    HEADRequest(redirect_url), track_id, 'Checking original download format availability',
                    'Original download format is not available', fatal=False)
                if urlh:
                    format_url = urlh.url
                    format_urls.add(format_url)
                    formats.append({
                        'format_id': 'download',
                        'ext': urlhandle_detect_ext(urlh) or 'mp3',
                        'filesize': int_or_none(urlh.headers.get('Content-Length')),
                        'url': format_url,
                        'quality': 10,
                        'format_note': 'Original',
                    })

        def invalid_url(url):
            return not url or url in format_urls

        def add_format(f, protocol, is_preview=False):
            mobj = re.search(r'\.(?P<abr>\d+)\.(?P<ext>[0-9a-z]{3,4})(?=[/?])', stream_url)
            if mobj:
                for k, v in mobj.groupdict().items():
                    if not f.get(k):
                        f[k] = v
            format_id_list = []
            if protocol:
                format_id_list.append(protocol)
            ext = f.get('ext')
            if ext == 'aac':
                f.update({
                    'abr': 256,
                    'quality': 5,
                    'format_note': 'Premium',
                })
            for k in ('ext', 'abr'):
                v = str_or_none(f.get(k))
                if v:
                    format_id_list.append(v)
            preview = is_preview or re.search(r'/(?:preview|playlist)/0/30/', f['url'])
            if preview:
                format_id_list.append('preview')
            abr = f.get('abr')
            if abr:
                f['abr'] = int(abr)
            if protocol in ('hls', 'hls-aes'):
                protocol = 'm3u8' if ext == 'aac' else 'm3u8_native'
            else:
                protocol = 'http'
            f.update({
                'format_id': '_'.join(format_id_list),
                'protocol': protocol,
                'preference': -10 if preview else None,
            })
            formats.append(f)

        # New API
        for t in traverse_obj(info, ('media', 'transcodings', lambda _, v: url_or_none(v['url']))):
            if extract_flat:
                break
            format_url = t['url']

            protocol = traverse_obj(t, ('format', 'protocol', {str}))
            if protocol == 'progressive':
                protocol = 'http'
            if protocol != 'hls' and '/hls' in format_url:
                protocol = 'hls'
            if protocol == 'encrypted-hls' or '/encrypted-hls' in format_url:
                protocol = 'hls-aes'

            ext = None
            if preset := traverse_obj(t, ('preset', {str_or_none})):
                ext = preset.split('_')[0]
            if ext not in KNOWN_EXTENSIONS:
                ext = mimetype2ext(traverse_obj(t, ('format', 'mime_type', {str})))

            identifier = join_nonempty(protocol, ext, delim='_')
            if not self._is_requested(identifier):
                self.write_debug(f'"{identifier}" is not a requested format, skipping')
                continue

            # XXX: if not extract_flat, 429 error must be caught where _extract_info_dict is called
            stream_url = traverse_obj(self._call_api(
                format_url, track_id, f'Downloading {identifier} format info JSON',
                query=query, headers=self._HEADERS), ('url', {url_or_none}))

            if invalid_url(stream_url):
                continue
            format_urls.add(stream_url)
            add_format({
                'url': stream_url,
                'ext': ext,
            }, protocol, t.get('snipped') or '/preview/' in format_url)

        for f in formats:
            f['vcodec'] = 'none'

        if not formats and info.get('policy') == 'BLOCK':
            self.raise_geo_restricted(metadata_available=True)

        user = info.get('user') or {}

        thumbnails = []
        artwork_url = info.get('artwork_url')
        thumbnail = artwork_url or user.get('avatar_url')
        if isinstance(thumbnail, str):
            if re.search(self._IMAGE_REPL_RE, thumbnail):
                for image_id, size in self._ARTWORK_MAP.items():
                    i = {
                        'id': image_id,
                        'url': re.sub(self._IMAGE_REPL_RE, f'-{image_id}.jpg', thumbnail),
                    }
                    if image_id == 'tiny' and not artwork_url:
                        size = 18
                    elif image_id == 'original':
                        i['preference'] = 10
                    if size:
                        i.update({
                            'width': size,
                            'height': size,
                        })
                    thumbnails.append(i)
            else:
                thumbnails = [{'url': thumbnail}]

        def extract_count(key):
            return int_or_none(info.get(f'{key}_count'))

        return {
            'id': track_id,
            'uploader': user.get('username'),
            'uploader_id': str_or_none(user.get('id')) or user.get('permalink'),
            'uploader_url': user.get('permalink_url'),
            'timestamp': unified_timestamp(info.get('created_at')),
            'title': info.get('title'),
            'description': info.get('description'),
            'thumbnails': thumbnails,
            'duration': float_or_none(info.get('duration'), 1000),
            'webpage_url': info.get('permalink_url'),
            'license': info.get('license'),
            'view_count': extract_count('playback'),
            'like_count': extract_count('favoritings') or extract_count('likes'),
            'comment_count': extract_count('comment'),
            'repost_count': extract_count('reposts'),
            'genres': traverse_obj(info, ('genre', {str}, filter, all, filter)),
            'artists': traverse_obj(info, ('publisher_metadata', 'artist', {str}, filter, all, filter)),
            'formats': formats if not extract_flat else None,
        }

    @classmethod
    def _resolv_url(cls, url):
        return cls._API_V2_BASE + 'resolve?url=' + url


class SoundcloudIE(SoundcloudBaseIE):
    """Information extractor for soundcloud.com
       To access the media, the uid of the song and a stream token
       must be extracted from the page source and the script must make
       a request to media.soundcloud.com/crossdomain.xml. Then
       the media can be grabbed by requesting from an url composed
       of the stream token and uid
     """

    _VALID_URL = r'''(?x)^(?:https?://)?
                    (?:(?:(?:www\.|m\.)?soundcloud\.com/
                            (?!stations/track)
                            (?P<uploader>[\w\d-]+)/
                            (?!(?:tracks|albums|sets(?:/.+?)?|reposts|likes|spotlight)/?(?:$|[?#]))
                            (?P<title>[\w\d-]+)
                            (?:/(?P<token>(?!(?:albums|sets|recommended))[^?]+?))?
                            (?:[?].*)?$)
                       |(?:api(?:-v2)?\.soundcloud\.com/tracks/(?P<track_id>\d+)
                          (?:/?\?secret_token=(?P<secret_token>[^&]+))?)
                    )
                    '''
    IE_NAME = 'soundcloud'
    _TESTS = [
        {
            'url': 'http://soundcloud.com/ethmusic/lostin-powers-she-so-heavy',
            'md5': 'de9bac153e7427a7333b4b0c1b6a18d2',
            'info_dict': {
                'id': '62986583',
                'ext': 'opus',
                'title': 'Lostin Powers - She so Heavy (SneakPreview) Adrian Ackers Blueprint 1',
                'description': 'No Downloads untill we record the finished version this weekend, i was too pumped n i had to post it , earl is prolly gonna b hella p.o\'d',
                'uploader': 'E.T. ExTerrestrial Music',
                'uploader_id': '1571244',
                'timestamp': 1349920598,
                'upload_date': '20121011',
                'duration': 143.216,
                'license': 'all-rights-reserved',
                'view_count': int,
                'like_count': int,
                'comment_count': int,
                'repost_count': int,
                'thumbnail': 'https://i1.sndcdn.com/artworks-000031955188-rwb18x-original.jpg',
                'uploader_url': 'https://soundcloud.com/ethmusic',
            },
        },
        # geo-restricted
        {
            'url': 'https://soundcloud.com/the-concept-band/goldrushed-mastered?in=the-concept-band/sets/the-royal-concept-ep',
            'info_dict': {
                'id': '47127627',
                'ext': 'opus',
                'title': 'Goldrushed',
                'description': 'From Stockholm Sweden\r\nPovel / Magnus / Filip / David\r\nwww.theroyalconcept.com',
                'uploader': 'The Royal Concept',
                'uploader_id': '9615865',
                'timestamp': 1337635207,
                'upload_date': '20120521',
                'duration': 227.155,
                'license': 'all-rights-reserved',
                'view_count': int,
                'like_count': int,
                'comment_count': int,
                'repost_count': int,
                'uploader_url': 'https://soundcloud.com/the-concept-band',
                'thumbnail': 'https://i1.sndcdn.com/artworks-v8bFHhXm7Au6-0-original.jpg',
                'genres': ['Alternative'],
                'artists': ['The Royal Concept'],
            },
        },
        # private link
        {
            'url': 'https://soundcloud.com/jaimemf/youtube-dl-test-video-a-y-baw/s-8Pjrp',
            'md5': 'aa0dd32bfea9b0c5ef4f02aacd080604',
            'info_dict': {
                'id': '123998367',
                'ext': 'mp3',
                'title': 'Youtube - Dl Test Video \'\' Ä↭',
                'description': 'test chars:  "\'/\\ä↭',
                'uploader': 'jaimeMF',
                'uploader_id': '69767071',
                'timestamp': 1386604920,
                'upload_date': '20131209',
                'duration': 9.927,
                'license': 'all-rights-reserved',
                'view_count': int,
                'like_count': int,
                'comment_count': int,
                'repost_count': int,
                'uploader_url': 'https://soundcloud.com/jaimemf',
                'thumbnail': 'https://a1.sndcdn.com/images/default_avatar_large.png',
                'genres': ['youtubedl'],
            },
        },
        # private link (alt format)
        {
            'url': 'https://api.soundcloud.com/tracks/123998367?secret_token=s-8Pjrp',
            'md5': 'aa0dd32bfea9b0c5ef4f02aacd080604',
            'info_dict': {
                'id': '123998367',
                'ext': 'mp3',
                'title': 'Youtube - Dl Test Video \'\' Ä↭',
                'description': 'test chars:  "\'/\\ä↭',
                'uploader': 'jaimeMF',
                'uploader_id': '69767071',
                'timestamp': 1386604920,
                'upload_date': '20131209',
                'duration': 9.927,
                'license': 'all-rights-reserved',
                'view_count': int,
                'like_count': int,
                'comment_count': int,
                'repost_count': int,
                'uploader_url': 'https://soundcloud.com/jaimemf',
                'thumbnail': 'https://a1.sndcdn.com/images/default_avatar_large.png',
                'genres': ['youtubedl'],
            },
        },
        # downloadable song
        {
            'url': 'https://soundcloud.com/the80m/the-following',
            'md5': '9ffcddb08c87d74fb5808a3c183a1d04',
            'info_dict': {
                'id': '343609555',
                'ext': 'wav',
                'title': 'The Following',
                'description': '',
                'uploader': '80M',
                'uploader_id': '312384765',
                'uploader_url': 'https://soundcloud.com/the80m',
                'upload_date': '20170922',
                'timestamp': 1506120436,
                'duration': 397.228,
                'thumbnail': 'https://i1.sndcdn.com/artworks-000243916348-ktoo7d-original.jpg',
                'license': 'all-rights-reserved',
                'like_count': int,
                'comment_count': int,
                'repost_count': int,
                'view_count': int,
                'genres': ['Dance & EDM'],
                'artists': ['80M'],
            },
        },
        # private link, downloadable format
        {
            'url': 'https://soundcloud.com/oriuplift/uponly-238-no-talking-wav/s-AyZUd',
            'md5': '64a60b16e617d41d0bef032b7f55441e',
            'info_dict': {
                'id': '340344461',
                'ext': 'wav',
                'title': 'Uplifting Only 238 [No Talking] (incl. Alex Feed Guestmix) (Aug 31, 2017) [wav]',
                'description': 'md5:fa20ee0fca76a3d6df8c7e57f3715366',
                'uploader': 'Ori Uplift Music',
                'uploader_id': '12563093',
                'timestamp': 1504206263,
                'upload_date': '20170831',
                'duration': 7449.096,
                'license': 'all-rights-reserved',
                'view_count': int,
                'like_count': int,
                'comment_count': int,
                'repost_count': int,
                'thumbnail': 'https://i1.sndcdn.com/artworks-000240712245-kedn4p-original.jpg',
                'uploader_url': 'https://soundcloud.com/oriuplift',
                'genres': ['Trance'],
                'artists': ['Ori Uplift'],
            },
        },
        # no album art, use avatar pic for thumbnail
        {
            'url': 'https://soundcloud.com/garyvee/sideways-prod-mad-real',
            'md5': '59c7872bc44e5d99b7211891664760c2',
            'info_dict': {
                'id': '309699954',
                'ext': 'mp3',
                'title': 'Sideways (Prod. Mad Real)',
                'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
                'uploader': 'garyvee',
                'uploader_id': '2366352',
                'timestamp': 1488152409,
                'upload_date': '20170226',
                'duration': 207.012,
                'thumbnail': r're:https?://.*\.jpg',
                'license': 'all-rights-reserved',
                'view_count': int,
                'like_count': int,
                'comment_count': int,
                'repost_count': int,
                'uploader_url': 'https://soundcloud.com/garyvee',
                'artists': ['MadReal'],
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'https://soundcloud.com/giovannisarani/mezzo-valzer',
            'md5': '8227c3473a4264df6b02ad7e5b7527ac',
            'info_dict': {
                'id': '583011102',
                'ext': 'opus',
                'title': 'Mezzo Valzer',
                'description': 'md5:f4d5f39d52e0ccc2b4f665326428901a',
                'uploader': 'Giovanni Sarani',
                'uploader_id': '3352531',
                'timestamp': 1551394171,
                'upload_date': '20190228',
                'duration': 180.157,
                'thumbnail': r're:https?://.*\.jpg',
                'license': 'all-rights-reserved',
                'view_count': int,
                'like_count': int,
                'comment_count': int,
                'repost_count': int,
                'genres': ['Piano'],
                'uploader_url': 'https://soundcloud.com/giovannisarani',
            },
        },
        {
            # AAC HQ format available (account with active subscription needed)
            'url': 'https://soundcloud.com/wandw/the-chainsmokers-ft-daya-dont-let-me-down-ww-remix-1',
            'only_matching': True,
        },
        {
            # Go+ (account with active subscription needed)
            'url': 'https://soundcloud.com/taylorswiftofficial/look-what-you-made-me-do',
            'only_matching': True,
        },
    ]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)

        track_id = mobj.group('track_id')

        query = {}
        if track_id:
            info_json_url = self._API_V2_BASE + 'tracks/' + track_id
            full_title = track_id
            token = mobj.group('secret_token')
            if token:
                query['secret_token'] = token
        else:
            full_title = resolve_title = '{}/{}'.format(*mobj.group('uploader', 'title'))
            token = mobj.group('token')
            if token:
                resolve_title += f'/{token}'
            info_json_url = self._resolv_url(self._BASE_URL + resolve_title)

        info = self._call_api(
            info_json_url, full_title, 'Downloading info JSON', query=query, headers=self._HEADERS)

        for retry in self.RetryManager():
            try:
                return self._extract_info_dict(info, full_title, token)
            except ExtractorError as e:
                if not isinstance(e.cause, HTTPError) or not e.cause.status == 429:
                    raise
                self.report_warning(
                    'You have reached the API rate limit, which is ~600 requests per '
                    '10 minutes. Use the --extractor-retries and --retry-sleep options '
                    'to configure an appropriate retry count and wait time', only_once=True)
                retry.error = e.cause


class SoundcloudPlaylistBaseIE(SoundcloudBaseIE):
    def _extract_set(self, playlist, token=None):
        playlist_id = str(playlist['id'])
        tracks = playlist.get('tracks') or []
        if not all(t.get('permalink_url') for t in tracks) and token:
            tracks = self._call_api(
                self._API_V2_BASE + 'tracks', playlist_id,
                'Downloading tracks', query={
                    'ids': ','.join([str(t['id']) for t in tracks]),
                    'playlistId': playlist_id,
                    'playlistSecretToken': token,
                }, headers=self._HEADERS)
        entries = []
        for track in tracks:
            track_id = str_or_none(track.get('id'))
            url = track.get('permalink_url')
            if not url:
                if not track_id:
                    continue
                url = self._API_V2_BASE + 'tracks/' + track_id
                if token:
                    url += '?secret_token=' + token
            entries.append(self.url_result(
                url, SoundcloudIE.ie_key(), track_id))
        return self.playlist_result(
            entries, playlist_id,
            playlist.get('title'),
            playlist.get('description'))


class SoundcloudSetIE(SoundcloudPlaylistBaseIE):
    _VALID_URL = r'https?://(?:(?:www|m)\.)?soundcloud\.com/(?P<uploader>[\w\d-]+)/sets/(?P<slug_title>[:\w\d-]+)(?:/(?P<token>[^?/]+))?'
    IE_NAME = 'soundcloud:set'
    _TESTS = [{
        'url': 'https://soundcloud.com/the-concept-band/sets/the-royal-concept-ep',
        'info_dict': {
            'id': '2284613',
            'title': 'The Royal Concept EP',
            'description': 'md5:71d07087c7a449e8941a70a29e34671e',
        },
        'playlist_mincount': 5,
    }, {
        'url': 'https://soundcloud.com/the-concept-band/sets/the-royal-concept-ep/token',
        'only_matching': True,
    }, {
        'url': 'https://soundcloud.com/discover/sets/weekly::flacmatic',
        'only_matching': True,
    }, {
        'url': 'https://soundcloud.com/discover/sets/charts-top:all-music:de',
        'only_matching': True,
    }, {
        'url': 'https://soundcloud.com/discover/sets/charts-top:hiphoprap:kr',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)

        full_title = '{}/sets/{}'.format(*mobj.group('uploader', 'slug_title'))
        token = mobj.group('token')
        if token:
            full_title += '/' + token

        info = self._call_api(self._resolv_url(
            self._BASE_URL + full_title), full_title, headers=self._HEADERS)

        if 'errors' in info:
            msgs = (str(err['error_message']) for err in info['errors'])
            raise ExtractorError('unable to download video webpage: {}'.format(','.join(msgs)))

        return self._extract_set(info, token)


class SoundcloudPagedPlaylistBaseIE(SoundcloudBaseIE):
    def _extract_playlist(self, base_url, playlist_id, playlist_title):
        return {
            '_type': 'playlist',
            'id': playlist_id,
            'title': playlist_title,
            'entries': self._entries(base_url, playlist_id),
        }

    def _entries(self, url, playlist_id):
        # Per the SoundCloud documentation, the maximum limit for a linked partitioning query is 200.
        # https://developers.soundcloud.com/blog/offset-pagination-deprecated
        query = {
            'limit': 200,
            'linked_partitioning': '1',
            'offset': 0,
        }

        for i in itertools.count():
            for retry in self.RetryManager():
                try:
                    response = self._call_api(
                        url, playlist_id, query=query, headers=self._HEADERS,
                        note=f'Downloading track page {i + 1}')
                    break
                except ExtractorError as e:
                    # Downloading page may result in intermittent 502 HTTP error
                    # See https://github.com/yt-dlp/yt-dlp/issues/872
                    if not isinstance(e.cause, HTTPError) or e.cause.status != 502:
                        raise
                    retry.error = e
                    continue

            def resolve_entry(*candidates):
                for cand in candidates:
                    if not isinstance(cand, dict):
                        continue
                    permalink_url = url_or_none(cand.get('permalink_url'))
                    if permalink_url:
                        return self.url_result(
                            permalink_url,
                            SoundcloudIE.ie_key() if SoundcloudIE.suitable(permalink_url) else None,
                            str_or_none(cand.get('id')), cand.get('title'))

            for e in response['collection'] or []:
                yield resolve_entry(e, e.get('track'), e.get('playlist'))

            url = response.get('next_href')
            if not url:
                break
            query.pop('offset', None)


class SoundcloudUserIE(SoundcloudPagedPlaylistBaseIE):
    _VALID_URL = r'''(?x)
                        https?://
                            (?:(?:www|m)\.)?soundcloud\.com/
                            (?P<user>[^/]+)
                            (?:/
                                (?P<rsrc>tracks|albums|sets|reposts|likes|spotlight)
                            )?
                            /?(?:[?#].*)?$
                    '''
    IE_NAME = 'soundcloud:user'
    _TESTS = [{
        'url': 'https://soundcloud.com/soft-cell-official',
        'info_dict': {
            'id': '207965082',
            'title': 'Soft Cell (All)',
        },
        'playlist_mincount': 28,
    }, {
        'url': 'https://soundcloud.com/soft-cell-official/tracks',
        'info_dict': {
            'id': '207965082',
            'title': 'Soft Cell (Tracks)',
        },
        'playlist_mincount': 27,
    }, {
        'url': 'https://soundcloud.com/soft-cell-official/albums',
        'info_dict': {
            'id': '207965082',
            'title': 'Soft Cell (Albums)',
        },
        'playlist_mincount': 1,
    }, {
        'url': 'https://soundcloud.com/jcv246/sets',
        'info_dict': {
            'id': '12982173',
            'title': 'Jordi / cv (Sets)',
        },
        'playlist_mincount': 2,
    }, {
        'url': 'https://soundcloud.com/jcv246/reposts',
        'info_dict': {
            'id': '12982173',
            'title': 'Jordi / cv (Reposts)',
        },
        'playlist_mincount': 6,
    }, {
        'url': 'https://soundcloud.com/clalberg/likes',
        'info_dict': {
            'id': '11817582',
            'title': 'clalberg (Likes)',
        },
        'playlist_mincount': 5,
    }, {
        'url': 'https://soundcloud.com/grynpyret/spotlight',
        'info_dict': {
            'id': '7098329',
            'title': 'Grynpyret (Spotlight)',
        },
        'playlist_mincount': 1,
    }]

    _BASE_URL_MAP = {
        'all': 'stream/users/%s',
        'tracks': 'users/%s/tracks',
        'albums': 'users/%s/albums',
        'sets': 'users/%s/playlists',
        'reposts': 'stream/users/%s/reposts',
        'likes': 'users/%s/likes',
        'spotlight': 'users/%s/spotlight',
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        uploader = mobj.group('user')

        user = self._call_api(
            self._resolv_url(self._BASE_URL + uploader),
            uploader, 'Downloading user info', headers=self._HEADERS)

        resource = mobj.group('rsrc') or 'all'

        return self._extract_playlist(
            self._API_V2_BASE + self._BASE_URL_MAP[resource] % user['id'],
            str_or_none(user.get('id')),
            '{} ({})'.format(user['username'], resource.capitalize()))


class SoundcloudUserPermalinkIE(SoundcloudPagedPlaylistBaseIE):
    _VALID_URL = r'https?://api\.soundcloud\.com/users/(?P<id>\d+)'
    IE_NAME = 'soundcloud:user:permalink'
    _TESTS = [{
        'url': 'https://api.soundcloud.com/users/30909869',
        'info_dict': {
            'id': '30909869',
            'title': 'neilcic',
        },
        'playlist_mincount': 22,
    }]

    def _real_extract(self, url):
        user_id = self._match_id(url)
        user = self._call_api(
            self._resolv_url(url), user_id, 'Downloading user info', headers=self._HEADERS)

        return self._extract_playlist(
            f'{self._API_V2_BASE}users/{user["id"]}/tracks', str(user['id']), user.get('username'))


class SoundcloudTrackStationIE(SoundcloudPagedPlaylistBaseIE):
    _VALID_URL = r'https?://(?:(?:www|m)\.)?soundcloud\.com/stations/track/[^/]+/(?P<id>[^/?#&]+)'
    IE_NAME = 'soundcloud:trackstation'
    _TESTS = [{
        'url': 'https://soundcloud.com/stations/track/officialsundial/your-text',
        'info_dict': {
            'id': '286017854',
            'title': 'Track station: your text',
        },
        'playlist_mincount': 47,
    }]

    def _real_extract(self, url):
        track_name = self._match_id(url)

        track = self._call_api(self._resolv_url(url), track_name, headers=self._HEADERS)
        track_id = self._search_regex(
            r'soundcloud:track-stations:(\d+)', track['id'], 'track id')

        return self._extract_playlist(
            self._API_V2_BASE + 'stations/{}/tracks'.format(track['id']),
            track_id, 'Track station: {}'.format(track['title']))


class SoundcloudRelatedIE(SoundcloudPagedPlaylistBaseIE):
    _VALID_URL = r'https?://(?:(?:www|m)\.)?soundcloud\.com/(?P<slug>[\w\d-]+/[\w\d-]+)/(?P<relation>albums|sets|recommended)'
    IE_NAME = 'soundcloud:related'
    _TESTS = [{
        'url': 'https://soundcloud.com/wajang/sexapil-pingers-5/recommended',
        'info_dict': {
            'id': '1084577272',
            'title': 'Sexapil - Pingers 5 (Recommended)',
        },
        'playlist_mincount': 50,
    }, {
        'url': 'https://soundcloud.com/wajang/sexapil-pingers-5/albums',
        'info_dict': {
            'id': '1084577272',
            'title': 'Sexapil - Pingers 5 (Albums)',
        },
        'playlist_mincount': 1,
    }, {
        'url': 'https://soundcloud.com/wajang/sexapil-pingers-5/sets',
        'info_dict': {
            'id': '1084577272',
            'title': 'Sexapil - Pingers 5 (Sets)',
        },
        'playlist_mincount': 4,
    }]

    _BASE_URL_MAP = {
        'albums': 'tracks/%s/albums',
        'sets': 'tracks/%s/playlists_without_albums',
        'recommended': 'tracks/%s/related',
    }

    def _real_extract(self, url):
        slug, relation = self._match_valid_url(url).group('slug', 'relation')

        track = self._call_api(
            self._resolv_url(self._BASE_URL + slug),
            slug, 'Downloading track info', headers=self._HEADERS)

        if track.get('errors'):
            raise ExtractorError(f'{self.IE_NAME} said: %s' % ','.join(
                str(err['error_message']) for err in track['errors']), expected=True)

        return self._extract_playlist(
            self._API_V2_BASE + self._BASE_URL_MAP[relation] % track['id'], str(track['id']),
            '{} ({})'.format(track.get('title') or slug, relation.capitalize()))


class SoundcloudPlaylistIE(SoundcloudPlaylistBaseIE):
    _VALID_URL = r'https?://api(?:-v2)?\.soundcloud\.com/playlists/(?P<id>[0-9]+)(?:/?\?secret_token=(?P<token>[^&]+?))?$'
    IE_NAME = 'soundcloud:playlist'
    _TESTS = [{
        'url': 'https://api.soundcloud.com/playlists/4110309',
        'info_dict': {
            'id': '4110309',
            'title': 'TILT Brass - Bowery Poetry Club, August \'03 [Non-Site SCR 02]',
            'description': 're:.*?TILT Brass - Bowery Poetry Club',
        },
        'playlist_count': 6,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        playlist_id = mobj.group('id')

        query = {}
        token = mobj.group('token')
        if token:
            query['secret_token'] = token

        data = self._call_api(
            self._API_V2_BASE + 'playlists/' + playlist_id,
            playlist_id, 'Downloading playlist', query=query, headers=self._HEADERS)

        return self._extract_set(data, token)


class SoundcloudSearchIE(SoundcloudBaseIE, SearchInfoExtractor):
    IE_NAME = 'soundcloud:search'
    IE_DESC = 'Soundcloud search'
    _SEARCH_KEY = 'scsearch'
    _TESTS = [{
        'url': 'scsearch15:post-avant jazzcore',
        'info_dict': {
            'id': 'post-avant jazzcore',
            'title': 'post-avant jazzcore',
        },
        'playlist_count': 15,
    }]

    _MAX_RESULTS_PER_PAGE = 200
    _DEFAULT_RESULTS_PER_PAGE = 50

    def _get_collection(self, endpoint, collection_id, **query):
        limit = min(
            query.get('limit', self._DEFAULT_RESULTS_PER_PAGE),
            self._MAX_RESULTS_PER_PAGE)
        query.update({
            'limit': limit,
            'linked_partitioning': 1,
            'offset': 0,
        })
        next_url = update_url_query(self._API_V2_BASE + endpoint, query)

        for i in itertools.count(1):
            response = self._call_api(
                next_url, collection_id, f'Downloading page {i}',
                'Unable to download API page', headers=self._HEADERS)

            for item in response.get('collection') or []:
                if item:
                    yield self.url_result(
                        item['uri'], SoundcloudIE.ie_key(), **self._extract_info_dict(item, extract_flat=True))

            next_url = response.get('next_href')
            if not next_url:
                break

    def _get_n_results(self, query, n):
        return self.playlist_result(itertools.islice(
            self._get_collection('search/tracks', query, limit=n, q=query),
            0, None if n == float('inf') else n), query, query)
