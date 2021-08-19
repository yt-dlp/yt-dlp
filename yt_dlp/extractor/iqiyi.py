# coding: utf-8
from __future__ import unicode_literals

import hashlib
import itertools
import re
import time

from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urllib_parse_urlencode,
)
from ..utils import (
    clean_html,
    decode_packed_codes,
    get_element_by_id,
    get_element_by_attribute,
    ExtractorError,
    ohdave_rsa_encrypt,
    remove_start,
)


def md5_text(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()


class IqiyiSDK(object):
    def __init__(self, target, ip, timestamp):
        self.target = target
        self.ip = ip
        self.timestamp = timestamp

    @staticmethod
    def split_sum(data):
        return compat_str(sum(map(lambda p: int(p, 16), list(data))))

    @staticmethod
    def digit_sum(num):
        if isinstance(num, int):
            num = compat_str(num)
        return compat_str(sum(map(int, num)))

    def even_odd(self):
        even = self.digit_sum(compat_str(self.timestamp)[::2])
        odd = self.digit_sum(compat_str(self.timestamp)[1::2])
        return even, odd

    def preprocess(self, chunksize):
        self.target = md5_text(self.target)
        chunks = []
        for i in range(32 // chunksize):
            chunks.append(self.target[chunksize * i:chunksize * (i + 1)])
        if 32 % chunksize:
            chunks.append(self.target[32 - 32 % chunksize:])
        return chunks, list(map(int, self.ip.split('.')))

    def mod(self, modulus):
        chunks, ip = self.preprocess(32)
        self.target = chunks[0] + ''.join(map(lambda p: compat_str(p % modulus), ip))

    def split(self, chunksize):
        modulus_map = {
            4: 256,
            5: 10,
            8: 100,
        }

        chunks, ip = self.preprocess(chunksize)
        ret = ''
        for i in range(len(chunks)):
            ip_part = compat_str(ip[i] % modulus_map[chunksize]) if i < 4 else ''
            if chunksize == 8:
                ret += ip_part + chunks[i]
            else:
                ret += chunks[i] + ip_part
        self.target = ret

    def handle_input16(self):
        self.target = md5_text(self.target)
        self.target = self.split_sum(self.target[:16]) + self.target + self.split_sum(self.target[16:])

    def handle_input8(self):
        self.target = md5_text(self.target)
        ret = ''
        for i in range(4):
            part = self.target[8 * i:8 * (i + 1)]
            ret += self.split_sum(part) + part
        self.target = ret

    def handleSum(self):
        self.target = md5_text(self.target)
        self.target = self.split_sum(self.target) + self.target

    def date(self, scheme):
        self.target = md5_text(self.target)
        d = time.localtime(self.timestamp)
        strings = {
            'y': compat_str(d.tm_year),
            'm': '%02d' % d.tm_mon,
            'd': '%02d' % d.tm_mday,
        }
        self.target += ''.join(map(lambda c: strings[c], list(scheme)))

    def split_time_even_odd(self):
        even, odd = self.even_odd()
        self.target = odd + md5_text(self.target) + even

    def split_time_odd_even(self):
        even, odd = self.even_odd()
        self.target = even + md5_text(self.target) + odd

    def split_ip_time_sum(self):
        chunks, ip = self.preprocess(32)
        self.target = compat_str(sum(ip)) + chunks[0] + self.digit_sum(self.timestamp)

    def split_time_ip_sum(self):
        chunks, ip = self.preprocess(32)
        self.target = self.digit_sum(self.timestamp) + chunks[0] + compat_str(sum(ip))


class IqiyiSDKInterpreter(object):
    def __init__(self, sdk_code):
        self.sdk_code = sdk_code

    def run(self, target, ip, timestamp):
        self.sdk_code = decode_packed_codes(self.sdk_code)

        functions = re.findall(r'input=([a-zA-Z0-9]+)\(input', self.sdk_code)

        sdk = IqiyiSDK(target, ip, timestamp)

        other_functions = {
            'handleSum': sdk.handleSum,
            'handleInput8': sdk.handle_input8,
            'handleInput16': sdk.handle_input16,
            'splitTimeEvenOdd': sdk.split_time_even_odd,
            'splitTimeOddEven': sdk.split_time_odd_even,
            'splitIpTimeSum': sdk.split_ip_time_sum,
            'splitTimeIpSum': sdk.split_time_ip_sum,
        }
        for function in functions:
            if re.match(r'mod\d+', function):
                sdk.mod(int(function[3:]))
            elif re.match(r'date[ymd]{3}', function):
                sdk.date(function[4:])
            elif re.match(r'split\d+', function):
                sdk.split(int(function[5:]))
            elif function in other_functions:
                other_functions[function]()
            else:
                raise ExtractorError('Unknown function %s' % function)

        return sdk.target


class IqiyiIE(InfoExtractor):
    IE_NAME = 'iqiyi'
    IE_DESC = '爱奇艺'

    _VALID_URL = r'https?://(?:(?:[^.]+\.)?iqiyi\.com|www\.pps\.tv)/.+\.html'

    _NETRC_MACHINE = 'iqiyi'

    _TESTS = [{
        'url': 'http://www.iqiyi.com/v_19rrojlavg.html',
        # MD5 checksum differs on my machine and Travis CI
        'info_dict': {
            'id': '9c1fb1b99d192b21c559e5a1a2cb3c73',
            'ext': 'mp4',
            'title': '美国德州空中惊现奇异云团 酷似UFO',
        }
    }, {
        'url': 'http://www.iqiyi.com/v_19rrhnnclk.html',
        'md5': 'b7dc800a4004b1b57749d9abae0472da',
        'info_dict': {
            'id': 'e3f585b550a280af23c98b6cb2be19fb',
            'ext': 'mp4',
            # This can be either Simplified Chinese or Traditional Chinese
            'title': r're:^(?:名侦探柯南 国语版：第752集 迫近灰原秘密的黑影 下篇|名偵探柯南 國語版：第752集 迫近灰原秘密的黑影 下篇)$',
        },
        'skip': 'Geo-restricted to China',
    }, {
        'url': 'http://www.iqiyi.com/w_19rt6o8t9p.html',
        'only_matching': True,
    }, {
        'url': 'http://www.iqiyi.com/a_19rrhbc6kt.html',
        'only_matching': True,
    }, {
        'url': 'http://yule.iqiyi.com/pcb.html',
        'info_dict': {
            'id': '4a0af228fddb55ec96398a364248ed7f',
            'ext': 'mp4',
            'title': '第2017-04-21期 女艺人频遭极端粉丝骚扰',
        },
    }, {
        # VIP-only video. The first 2 parts (6 minutes) are available without login
        # MD5 sums omitted as values are different on Travis CI and my machine
        'url': 'http://www.iqiyi.com/v_19rrny4w8w.html',
        'info_dict': {
            'id': 'f3cf468b39dddb30d676f89a91200dc1',
            'ext': 'mp4',
            'title': '泰坦尼克号',
        },
        'skip': 'Geo-restricted to China',
    }, {
        'url': 'http://www.iqiyi.com/a_19rrhb8ce1.html',
        'info_dict': {
            'id': '202918101',
            'title': '灌篮高手 国语版',
        },
        'playlist_count': 101,
    }, {
        'url': 'http://www.pps.tv/w_19rrbav0ph.html',
        'only_matching': True,
    }]

    _FORMATS_MAP = {
        '96': 1,    # 216p, 240p
        '1': 2,     # 336p, 360p
        '2': 3,     # 480p, 504p
        '21': 4,    # 504p
        '4': 5,     # 720p
        '17': 5,    # 720p
        '5': 6,     # 1072p, 1080p
        '18': 7,    # 1080p
    }

    def _real_initialize(self):
        self._login()

    @staticmethod
    def _rsa_fun(data):
        # public key extracted from http://static.iqiyi.com/js/qiyiV2/20160129180840/jobs/i18n/i18nIndex.js
        N = 0xab86b6371b5318aaa1d3c9e612a9f1264f372323c8c0f19875b5fc3b3fd3afcc1e5bec527aa94bfa85bffc157e4245aebda05389a5357b75115ac94f074aefcd
        e = 65537

        return ohdave_rsa_encrypt(data, e, N)

    def _login(self):
        username, password = self._get_login_info()

        # No authentication to be performed
        if not username:
            return True

        data = self._download_json(
            'http://kylin.iqiyi.com/get_token', None,
            note='Get token for logging', errnote='Unable to get token for logging')
        sdk = data['sdk']
        timestamp = int(time.time())
        target = '/apis/reglogin/login.action?lang=zh_TW&area_code=null&email=%s&passwd=%s&agenttype=1&from=undefined&keeplogin=0&piccode=&fromurl=&_pos=1' % (
            username, self._rsa_fun(password.encode('utf-8')))

        interp = IqiyiSDKInterpreter(sdk)
        sign = interp.run(target, data['ip'], timestamp)

        validation_params = {
            'target': target,
            'server': 'BEA3AA1908656AABCCFF76582C4C6660',
            'token': data['token'],
            'bird_src': 'f8d91d57af224da7893dd397d52d811a',
            'sign': sign,
            'bird_t': timestamp,
        }
        validation_result = self._download_json(
            'http://kylin.iqiyi.com/validate?' + compat_urllib_parse_urlencode(validation_params), None,
            note='Validate credentials', errnote='Unable to validate credentials')

        MSG_MAP = {
            'P00107': 'please login via the web interface and enter the CAPTCHA code',
            'P00117': 'bad username or password',
        }

        code = validation_result['code']
        if code != 'A00000':
            msg = MSG_MAP.get(code)
            if not msg:
                msg = 'error %s' % code
                if validation_result.get('msg'):
                    msg += ': ' + validation_result['msg']
            self.report_warning('unable to log in: ' + msg)
            return False

        return True

    def get_raw_data(self, tvid, video_id):
        tm = int(time.time() * 1000)

        key = 'd5fb4bd9d50c4be6948c97edd7254b0e'
        sc = md5_text(compat_str(tm) + key + tvid)
        params = {
            'tvid': tvid,
            'vid': video_id,
            'src': '76f90cbd92f94a2e925d83e8ccd22cb7',
            'sc': sc,
            't': tm,
        }

        return self._download_json(
            'http://cache.m.iqiyi.com/jp/tmts/%s/%s/' % (tvid, video_id),
            video_id, transform_source=lambda s: remove_start(s, 'var tvInfoJs='),
            query=params, headers=self.geo_verification_headers())

    def _extract_playlist(self, webpage):
        PAGE_SIZE = 50

        links = re.findall(
            r'<a[^>]+class="site-piclist_pic_link"[^>]+href="(http://www\.iqiyi\.com/.+\.html)"',
            webpage)
        if not links:
            return

        album_id = self._search_regex(
            r'albumId\s*:\s*(\d+),', webpage, 'album ID')
        album_title = self._search_regex(
            r'data-share-title="([^"]+)"', webpage, 'album title', fatal=False)

        entries = list(map(self.url_result, links))

        # Start from 2 because links in the first page are already on webpage
        for page_num in itertools.count(2):
            pagelist_page = self._download_webpage(
                'http://cache.video.qiyi.com/jp/avlist/%s/%d/%d/' % (album_id, page_num, PAGE_SIZE),
                album_id,
                note='Download playlist page %d' % page_num,
                errnote='Failed to download playlist page %d' % page_num)
            pagelist = self._parse_json(
                remove_start(pagelist_page, 'var tvInfoJs='), album_id)
            vlist = pagelist['data']['vlist']
            for item in vlist:
                entries.append(self.url_result(item['vurl']))
            if len(vlist) < PAGE_SIZE:
                break

        return self.playlist_result(entries, album_id, album_title)

    def _real_extract(self, url):
        webpage = self._download_webpage(
            url, 'temp_id', note='download video page')

        # There's no simple way to determine whether an URL is a playlist or not
        # Sometimes there are playlist links in individual videos, so treat it
        # as a single video first
        tvid = self._search_regex(
            r'data-(?:player|shareplattrigger)-tvid\s*=\s*[\'"](\d+)', webpage, 'tvid', default=None)
        if tvid is None:
            playlist_result = self._extract_playlist(webpage)
            if playlist_result:
                return playlist_result
            raise ExtractorError('Can\'t find any video')

        video_id = self._search_regex(
            r'data-(?:player|shareplattrigger)-videoid\s*=\s*[\'"]([a-f\d]+)', webpage, 'video_id')

        formats = []
        for _ in range(5):
            raw_data = self.get_raw_data(tvid, video_id)

            if raw_data['code'] != 'A00000':
                if raw_data['code'] == 'A00111':
                    self.raise_geo_restricted()
                raise ExtractorError('Unable to load data. Error code: ' + raw_data['code'])

            data = raw_data['data']

            for stream in data['vidl']:
                if 'm3utx' not in stream:
                    continue
                vd = compat_str(stream['vd'])
                formats.append({
                    'url': stream['m3utx'],
                    'format_id': vd,
                    'ext': 'mp4',
                    'quality': self._FORMATS_MAP.get(vd, -1),
                    'protocol': 'm3u8_native',
                })

            if formats:
                break

            self._sleep(5, video_id)

        self._sort_formats(formats)
        title = (get_element_by_id('widget-videotitle', webpage)
                 or clean_html(get_element_by_attribute('class', 'mod-play-tit', webpage))
                 or self._html_search_regex(r'<span[^>]+data-videochanged-title="word"[^>]*>([^<]+)</span>', webpage, 'title'))

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
        }
