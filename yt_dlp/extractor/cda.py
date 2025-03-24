import base64
import codecs
import datetime as dt
import hashlib
import hmac
import json
import random
import re
import urllib.parse

from .common import InfoExtractor
from ..compat import compat_ord
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    float_or_none,
    int_or_none,
    merge_dicts,
    multipart_encode,
    parse_duration,
    traverse_obj,
    try_call,
    try_get,
    urljoin,
)


class CDAIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www\.)?cda\.pl/video|ebd\.cda\.pl/[0-9]+x[0-9]+)/(?P<id>[0-9a-z]+)'
    _NETRC_MACHINE = 'cdapl'

    _BASE_URL = 'https://www.cda.pl'
    _BASE_API_URL = 'https://api.cda.pl'
    _API_HEADERS = {
        'Accept': 'application/vnd.cda.public+json',
    }
    # hardcoded in the app
    _LOGIN_REQUEST_AUTH = 'Basic YzU3YzBlZDUtYTIzOC00MWQwLWI2NjQtNmZmMWMxY2Y2YzVlOklBTm95QlhRRVR6U09MV1hnV3MwMW0xT2VyNWJNZzV4clRNTXhpNGZJUGVGZ0lWUlo5UGVYTDhtUGZaR1U1U3Q'
    _BEARER_CACHE = 'cda-bearer'

    _TESTS = [{
        'url': 'http://www.cda.pl/video/5749950c',
        'md5': '6f844bf51b15f31fae165365707ae970',
        'info_dict': {
            'id': '5749950c',
            'ext': 'mp4',
            'height': 720,
            'title': 'Oto dlaczego przed zakrętem należy zwolnić.',
            'description': 'md5:269ccd135d550da90d1662651fcb9772',
            'thumbnail': r're:^https?://.*\.jpg$',
            'average_rating': float,
            'duration': 39,
            'age_limit': 0,
            'upload_date': '20160221',
            'timestamp': 1456078244,
        },
    }, {
        'url': 'http://www.cda.pl/video/57413289',
        'md5': 'a88828770a8310fc00be6c95faf7f4d5',
        'info_dict': {
            'id': '57413289',
            'ext': 'mp4',
            'title': 'Lądowanie na lotnisku na Maderze',
            'description': 'md5:60d76b71186dcce4e0ba6d4bbdb13e1a',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'crash404',
            'average_rating': float,
            'duration': 137,
            'age_limit': 0,
            'upload_date': '20160220',
            'timestamp': 1455968218,
        },
    }, {
        # Age-restricted with vfilm redirection
        'url': 'https://www.cda.pl/video/8753244c4',
        'md5': 'd8eeb83d63611289507010d3df3bb8b3',
        'info_dict': {
            'id': '8753244c4',
            'ext': 'mp4',
            'title': '[18+] Bez Filtra: Rezerwowe Psy czyli...  najwulgarniejsza polska gra?',
            'description': 'md5:ae80bac31bd6a9f077a6cce03c7c077e',
            'height': 1080,
            'uploader': 'arhn eu',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 991,
            'age_limit': 18,
            'average_rating': float,
            'timestamp': 1633888264,
            'upload_date': '20211010',
        },
    }, {
        # Age-restricted without vfilm redirection
        'url': 'https://www.cda.pl/video/17028157b8',
        'md5': 'c1fe5ff4582bace95d4f0ce0fbd0f992',
        'info_dict': {
            'id': '17028157b8',
            'ext': 'mp4',
            'title': 'STENDUPY MICHAŁ OGIŃSKI',
            'description': 'md5:5851f3272bfc31f762d616040a1d609a',
            'height': 480,
            'uploader': 'oginski',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 18855,
            'age_limit': 18,
            'average_rating': float,
            'timestamp': 1699705901,
            'upload_date': '20231111',
        },
    }, {
        'url': 'http://ebd.cda.pl/0x0/5749950c',
        'only_matching': True,
    }]

    def _download_age_confirm_page(self, url, video_id, *args, **kwargs):
        data, content_type = multipart_encode({'age_confirm': ''})
        return self._download_webpage(
            url, video_id, *args,
            data=data, headers={
                'Referer': url,
                'Content-Type': content_type,
            }, **kwargs)

    def _perform_login(self, username, password):
        app_version = '1.2.255 build 21541'
        android_version = random.randrange(8, 14)
        phone_model = random.choice((
            # x-kom.pl top selling Android smartphones, as of 2022-12-26
            # https://www.x-kom.pl/g-4/c/1590-smartfony-i-telefony.html?f201-system-operacyjny=61322-android
            'ASUS ZenFone 8',
            'Motorola edge 20 5G',
            'Motorola edge 30 neo 5G',
            'Motorola moto g22',
            'OnePlus Nord 2T 5G',
            'Samsung Galaxy A32 SM‑A325F',
            'Samsung Galaxy M13',
            'Samsung Galaxy S20 FE 5G',
            'Xiaomi 11T',
            'Xiaomi POCO M4 Pro',
            'Xiaomi Redmi 10',
            'Xiaomi Redmi 10C',
            'Xiaomi Redmi 9C NFC',
            'Xiaomi Redmi Note 10 Pro',
            'Xiaomi Redmi Note 11 Pro',
            'Xiaomi Redmi Note 11',
            'Xiaomi Redmi Note 11S 5G',
            'Xiaomi Redmi Note 11S',
            'realme 10',
            'realme 9 Pro+',
            'vivo Y33s',
        ))
        self._API_HEADERS['User-Agent'] = f'pl.cda 1.0 (version {app_version}; Android {android_version}; {phone_model})'

        cached_bearer = self.cache.load(self._BEARER_CACHE, username) or {}
        if cached_bearer.get('valid_until', 0) > dt.datetime.now().timestamp() + 5:
            self._API_HEADERS['Authorization'] = f'Bearer {cached_bearer["token"]}'
            return

        password_hash = base64.urlsafe_b64encode(hmac.new(
            b's01m1Oer5IANoyBXQETzSOLWXgWs01m1Oer5bMg5xrTMMxRZ9Pi4fIPeFgIVRZ9PeXL8mPfXQETZGUAN5StRZ9P',
            ''.join(f'{bytes((bt & 255, )).hex():0>2}'
                    for bt in hashlib.md5(password.encode()).digest()).encode(),
            hashlib.sha256).digest()).decode().replace('=', '')

        token_res = self._download_json(
            f'{self._BASE_API_URL}/oauth/token', None, 'Logging in', data=b'',
            headers={**self._API_HEADERS, 'Authorization': self._LOGIN_REQUEST_AUTH},
            query={
                'grant_type': 'password',
                'login': username,
                'password': password_hash,
            })
        self.cache.store(self._BEARER_CACHE, username, {
            'token': token_res['access_token'],
            'valid_until': token_res['expires_in'] + dt.datetime.now().timestamp(),
        })
        self._API_HEADERS['Authorization'] = f'Bearer {token_res["access_token"]}'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        if 'Authorization' in self._API_HEADERS:
            return self._api_extract(video_id)
        else:
            return self._web_extract(video_id)

    def _api_extract(self, video_id):
        meta = self._download_json(
            f'{self._BASE_API_URL}/video/{video_id}', video_id, headers=self._API_HEADERS)['video']

        uploader = traverse_obj(meta, ('author', 'login', {str}))

        formats = [{
            'url': quality['file'],
            'format': quality.get('title'),
            'resolution': quality.get('name'),
            'height': try_call(lambda: int(quality['name'][:-1])),
            'filesize': quality.get('length'),
        } for quality in meta['qualities'] if quality.get('file')]

        if meta.get('premium') and not meta.get('premium_free') and not formats:
            raise ExtractorError(
                'Video requires CDA Premium - subscription needed', expected=True)

        return {
            'id': video_id,
            'title': meta.get('title'),
            'description': meta.get('description'),
            'uploader': None if uploader == 'anonim' else uploader,
            'average_rating': float_or_none(meta.get('rating')),
            'thumbnail': meta.get('thumb'),
            'formats': formats,
            'duration': meta.get('duration'),
            'age_limit': 18 if meta.get('for_adults') else 0,
            'view_count': meta.get('views'),
        }

    def _web_extract(self, video_id):
        self._set_cookie('cda.pl', 'cda.player', 'html5')
        webpage, urlh = self._download_webpage_handle(
            f'{self._BASE_URL}/video/{video_id}/vfilm', video_id)

        if 'Ten film jest dostępny dla użytkowników premium' in webpage:
            self.raise_login_required('This video is only available for premium users')

        if re.search(r'niedostępn[ey] w(?:&nbsp;|\s+)Twoim kraju\s*<', webpage):
            self.raise_geo_restricted()

        need_confirm_age = False
        if self._html_search_regex(r'(<button[^>]+name="[^"]*age_confirm[^"]*")',
                                   webpage, 'birthday validate form', default=None):
            webpage = self._download_age_confirm_page(
                urlh.url, video_id, note='Confirming age')
            need_confirm_age = True

        formats = []

        uploader = self._search_regex(r'''(?x)
            <(span|meta)[^>]+itemprop=(["\'])author\2[^>]*>
            (?:<\1[^>]*>[^<]*</\1>|(?!</\1>)(?:.|\n))*?
            <(span|meta)[^>]+itemprop=(["\'])name\4[^>]*>(?P<uploader>[^<]+)</\3>
        ''', webpage, 'uploader', default=None, group='uploader')
        average_rating = self._search_regex(
            (r'<(?:span|meta)[^>]+itemprop=(["\'])ratingValue\1[^>]*>(?P<rating_value>[0-9.]+)',
             r'<span[^>]+\bclass=["\']rating["\'][^>]*>(?P<rating_value>[0-9.]+)'), webpage, 'rating', fatal=False,
            group='rating_value')

        info_dict = {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'uploader': uploader,
            'average_rating': float_or_none(average_rating),
            'thumbnail': self._og_search_thumbnail(webpage),
            'formats': formats,
            'duration': None,
            'age_limit': 18 if need_confirm_age else 0,
        }

        info = self._search_json_ld(webpage, video_id, default={})

        # Source: https://www.cda.pl/js/player.js?t=1606154898
        def decrypt_file(a):
            for p in ('_XDDD', '_CDA', '_ADC', '_CXD', '_QWE', '_Q5', '_IKSDE'):
                a = a.replace(p, '')
            a = urllib.parse.unquote(a)
            b = []
            for c in a:
                f = compat_ord(c)
                b.append(chr(33 + (f + 14) % 94) if 33 <= f <= 126 else chr(f))
            a = ''.join(b)
            a = a.replace('.cda.mp4', '')
            for p in ('.2cda.pl', '.3cda.pl'):
                a = a.replace(p, '.cda.pl')
            if '/upstream' in a:
                a = a.replace('/upstream', '.mp4/upstream')
                return 'https://' + a
            return 'https://' + a + '.mp4'

        def extract_format(page, version):
            json_str = self._html_search_regex(
                r'player_data=(\\?["\'])(?P<player_data>.+?)\1', page,
                f'{version} player_json', fatal=False, group='player_data')
            if not json_str:
                return
            player_data = self._parse_json(
                json_str, f'{version} player_data', fatal=False)
            if not player_data:
                return
            video = player_data.get('video')
            if not video or 'file' not in video:
                self.report_warning(f'Unable to extract {version} version information')
                return
            if video['file'].startswith('uggc'):
                video['file'] = codecs.decode(video['file'], 'rot_13')
                if video['file'].endswith('adc.mp4'):
                    video['file'] = video['file'].replace('adc.mp4', '.mp4')
            elif not video['file'].startswith('http'):
                video['file'] = decrypt_file(video['file'])
            video_quality = video.get('quality')
            qualities = video.get('qualities', {})
            video_quality = next((k for k, v in qualities.items() if v == video_quality), video_quality)
            info_dict['formats'].append({
                'url': video['file'],
                'format_id': video_quality,
                'height': int_or_none(video_quality[:-1]),
            })
            for quality, cda_quality in qualities.items():
                if quality == video_quality:
                    continue
                data = {'jsonrpc': '2.0', 'method': 'videoGetLink', 'id': 2,
                        'params': [video_id, cda_quality, video.get('ts'), video.get('hash2'), {}]}
                data = json.dumps(data).encode()
                video_url = self._download_json(
                    f'https://www.cda.pl/video/{video_id}', video_id, headers={
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                    }, data=data, note=f'Fetching {quality} url',
                    errnote=f'Failed to fetch {quality} url', fatal=False)
                if try_get(video_url, lambda x: x['result']['status']) == 'ok':
                    video_url = try_get(video_url, lambda x: x['result']['resp'])
                    info_dict['formats'].append({
                        'url': video_url,
                        'format_id': quality,
                        'height': int_or_none(quality[:-1]),
                    })

            if not info_dict['duration']:
                info_dict['duration'] = parse_duration(video.get('duration'))

        extract_format(webpage, 'default')

        for href, resolution in re.findall(
                r'<a[^>]+data-quality="[^"]+"[^>]+href="([^"]+)"[^>]+class="quality-btn"[^>]*>([0-9]+p)',
                webpage):
            if need_confirm_age:
                handler = self._download_age_confirm_page
            else:
                handler = self._download_webpage

            webpage = handler(
                urljoin(self._BASE_URL, href), video_id,
                f'Downloading {resolution} version information', fatal=False)
            if not webpage:
                # Manually report warning because empty page is returned when
                # invalid version is requested.
                self.report_warning(f'Unable to download {resolution} version information')
                continue

            extract_format(webpage, resolution)

        return merge_dicts(info_dict, info)


class CDAFolderIE(InfoExtractor):
    _MAX_PAGE_SIZE = 36
    _VALID_URL = r'https?://(?:www\.)?cda\.pl/(?P<channel>\w+)/folder/(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'https://www.cda.pl/domino264/folder/31188385',
            'info_dict': {
                'id': '31188385',
                'title': 'SERIA DRUGA',
            },
            'playlist_mincount': 13,
        },
        {
            'url': 'https://www.cda.pl/smiechawaTV/folder/2664592/vfilm',
            'info_dict': {
                'id': '2664592',
                'title': 'VideoDowcipy - wszystkie odcinki',
            },
            'playlist_mincount': 71,
        },
        {
            'url': 'https://www.cda.pl/DeliciousBeauty/folder/19129979/vfilm',
            'info_dict': {
                'id': '19129979',
                'title': 'TESTY KOSMETYKÓW',
            },
            'playlist_mincount': 139,
        }]

    def _real_extract(self, url):
        folder_id, channel = self._match_valid_url(url).group('id', 'channel')

        webpage = self._download_webpage(url, folder_id)

        def extract_page_entries(page):
            webpage = self._download_webpage(
                f'https://www.cda.pl/{channel}/folder/{folder_id}/vfilm/{page + 1}', folder_id,
                f'Downloading page {page + 1}', expected_status=404)
            items = re.findall(r'<a[^>]+href="/video/([0-9a-z]+)"', webpage)
            for video_id in items:
                yield self.url_result(f'https://www.cda.pl/video/{video_id}', CDAIE, video_id)

        return self.playlist_result(
            OnDemandPagedList(extract_page_entries, self._MAX_PAGE_SIZE),
            folder_id, self._og_search_title(webpage))
