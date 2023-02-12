import hashlib
import itertools
import re
import time

from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urllib_parse_urlencode,
    compat_urllib_parse_unquote
)
from .openload import PhantomJSwrapper
from ..utils import (
    clean_html,
    decode_packed_codes,
    ExtractorError,
    float_or_none,
    format_field,
    get_element_by_id,
    get_element_by_attribute,
    int_or_none,
    js_to_json,
    ohdave_rsa_encrypt,
    parse_age_limit,
    parse_duration,
    parse_iso8601,
    parse_resolution,
    qualities,
    remove_start,
    str_or_none,
    traverse_obj,
    urljoin,
)


def md5_text(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()


class IqiyiSDK:
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


class IqiyiSDKInterpreter:
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

    @staticmethod
    def _rsa_fun(data):
        # public key extracted from http://static.iqiyi.com/js/qiyiV2/20160129180840/jobs/i18n/i18nIndex.js
        N = 0xab86b6371b5318aaa1d3c9e612a9f1264f372323c8c0f19875b5fc3b3fd3afcc1e5bec527aa94bfa85bffc157e4245aebda05389a5357b75115ac94f074aefcd
        e = 65537

        return ohdave_rsa_encrypt(data, e, N)

    def _perform_login(self, username, password):

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

        title = (get_element_by_id('widget-videotitle', webpage)
                 or clean_html(get_element_by_attribute('class', 'mod-play-tit', webpage))
                 or self._html_search_regex(r'<span[^>]+data-videochanged-title="word"[^>]*>([^<]+)</span>', webpage, 'title'))

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
        }


class IqIE(InfoExtractor):
    IE_NAME = 'iq.com'
    IE_DESC = 'International version of iQiyi'
    _VALID_URL = r'https?://(?:www\.)?iq\.com/play/(?:[\w%-]*-)?(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://www.iq.com/play/one-piece-episode-1000-1ma1i6ferf4',
        'md5': '2d7caf6eeca8a32b407094b33b757d39',
        'info_dict': {
            'ext': 'mp4',
            'id': '1ma1i6ferf4',
            'title': '航海王 第1000集',
            'description': 'Subtitle available on Sunday 4PM（GMT+8）.',
            'duration': 1430,
            'timestamp': 1637488203,
            'upload_date': '20211121',
            'episode_number': 1000,
            'episode': 'Episode 1000',
            'series': 'One Piece',
            'age_limit': 13,
            'average_rating': float,
        },
        'params': {
            'format': '500',
        },
        'expected_warnings': ['format is restricted']
    }, {
        # VIP-restricted video
        'url': 'https://www.iq.com/play/mermaid-in-the-fog-2021-gbdpx13bs4',
        'only_matching': True
    }]
    _BID_TAGS = {
        '100': '240P',
        '200': '360P',
        '300': '480P',
        '500': '720P',
        '600': '1080P',
        '610': '1080P50',
        '700': '2K',
        '800': '4K',
    }
    _LID_TAGS = {
        '1': 'zh_CN',
        '2': 'zh_TW',
        '3': 'en',
        '4': 'kor',
        '18': 'th',
        '21': 'my',
        '23': 'vi',
        '24': 'id',
        '26': 'es',
        '28': 'ar',
    }

    _DASH_JS = '''
        console.log(page.evaluate(function() {
            var tvid = "%(tvid)s"; var vid = "%(vid)s"; var src = "%(src)s";
            var uid = "%(uid)s"; var dfp = "%(dfp)s"; var mode = "%(mode)s"; var lang = "%(lang)s";
            var bid_list = %(bid_list)s; var ut_list = %(ut_list)s; var tm = new Date().getTime();
            var cmd5x_func = %(cmd5x_func)s; var cmd5x_exporter = {}; cmd5x_func({}, cmd5x_exporter, {}); var cmd5x = cmd5x_exporter.cmd5x;
            var authKey = cmd5x(cmd5x('') + tm + '' + tvid);
            var k_uid = Array.apply(null, Array(32)).map(function() {return Math.floor(Math.random() * 15).toString(16)}).join('');
            var dash_paths = {};
            bid_list.forEach(function(bid) {
                var query = {
                    'tvid': tvid,
                    'bid': bid,
                    'ds': 1,
                    'vid': vid,
                    'src': src,
                    'vt': 0,
                    'rs': 1,
                    'uid': uid,
                    'ori': 'pcw',
                    'ps': 1,
                    'k_uid': k_uid,
                    'pt': 0,
                    'd': 0,
                    's': '',
                    'lid': '',
                    'slid': 0,
                    'cf': '',
                    'ct': '',
                    'authKey': authKey,
                    'k_tag': 1,
                    'ost': 0,
                    'ppt': 0,
                    'dfp': dfp,
                    'prio': JSON.stringify({
                        'ff': 'f4v',
                        'code': 2
                    }),
                    'k_err_retries': 0,
                    'up': '',
                    'su': 2,
                    'applang': lang,
                    'sver': 2,
                    'X-USER-MODE': mode,
                    'qd_v': 2,
                    'tm': tm,
                    'qdy': 'a',
                    'qds': 0,
                    'k_ft1': 141287244169348,
                    'k_ft4': 34359746564,
                    'k_ft5': 1,
                    'bop': JSON.stringify({
                        'version': '10.0',
                        'dfp': dfp
                    }),
                };
                var enc_params = [];
                for (var prop in query) {
                    enc_params.push(encodeURIComponent(prop) + '=' + encodeURIComponent(query[prop]));
                }
                ut_list.forEach(function(ut) {
                    enc_params.push('ut=' + ut);
                })
                var dash_path = '/dash?' + enc_params.join('&'); dash_path += '&vf=' + cmd5x(dash_path);
                dash_paths[bid] = dash_path;
            });
            return JSON.stringify(dash_paths);
        }));
        saveAndExit();
    '''

    def _extract_vms_player_js(self, webpage, video_id):
        player_js_cache = self.cache.load('iq', 'player_js')
        if player_js_cache:
            return player_js_cache
        webpack_js_url = self._proto_relative_url(self._search_regex(
            r'<script src="((?:https?)?//stc.iqiyipic.com/_next/static/chunks/webpack-\w+\.js)"', webpage, 'webpack URL'))
        webpack_js = self._download_webpage(webpack_js_url, video_id, note='Downloading webpack JS', errnote='Unable to download webpack JS')
        webpack_map = self._search_json(
            r'["\']\s*\+\s*', webpack_js, 'JS locations', video_id,
            contains_pattern=r'{\s*(?:\d+\s*:\s*["\'][\da-f]+["\']\s*,?\s*)+}',
            end_pattern=r'\[\w+\]\+["\']\.js', transform_source=js_to_json)

        for module_index in reversed(webpack_map):
            module_js = self._download_webpage(
                f'https://stc.iqiyipic.com/_next/static/chunks/{module_index}.{webpack_map[module_index]}.js',
                video_id, note=f'Downloading #{module_index} module JS', errnote='Unable to download module JS', fatal=False) or ''
            if 'vms request' in module_js:
                self.cache.store('iq', 'player_js', module_js)
                return module_js
        raise ExtractorError('Unable to extract player JS')

    def _extract_cmd5x_function(self, webpage, video_id):
        return self._search_regex(r',\s*(function\s*\([^\)]*\)\s*{\s*var _qda.+_qdc\(\)\s*})\s*,',
                                  self._extract_vms_player_js(webpage, video_id), 'signature function')

    def _update_bid_tags(self, webpage, video_id):
        extracted_bid_tags = self._search_json(
            r'function\s*\([^)]*\)\s*\{\s*"use strict";?\s*var \w\s*=\s*',
            self._extract_vms_player_js(webpage, video_id), 'video tags', video_id,
            contains_pattern=r'{\s*\d+\s*:\s*\{\s*nbid\s*:.+}\s*}',
            end_pattern=r'\s*,\s*\w\s*=\s*\{\s*getNewVd', fatal=False, transform_source=js_to_json)
        if not extracted_bid_tags:
            return
        self._BID_TAGS = {
            bid: traverse_obj(extracted_bid_tags, (bid, 'value'), expected_type=str, default=self._BID_TAGS.get(bid))
            for bid in extracted_bid_tags.keys()
        }

    def _get_cookie(self, name, default=None):
        cookie = self._get_cookies('https://iq.com/').get(name)
        return cookie.value if cookie else default

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        self._update_bid_tags(webpage, video_id)

        next_props = self._search_nextjs_data(webpage, video_id)['props']
        page_data = next_props['initialState']['play']
        video_info = page_data['curVideoInfo']

        uid = traverse_obj(
            self._parse_json(
                self._get_cookie('I00002', '{}'), video_id, transform_source=compat_urllib_parse_unquote, fatal=False),
            ('data', 'uid'), default=0)

        if uid:
            vip_data = self._download_json(
                'https://pcw-api.iq.com/api/vtype', video_id, note='Downloading VIP data', errnote='Unable to download VIP data', query={
                    'batch': 1,
                    'platformId': 3,
                    'modeCode': self._get_cookie('mod', 'intl'),
                    'langCode': self._get_cookie('lang', 'en_us'),
                    'deviceId': self._get_cookie('QC005', '')
                }, fatal=False)
            ut_list = traverse_obj(vip_data, ('data', 'all_vip', ..., 'vipType'), expected_type=str_or_none)
        else:
            ut_list = ['0']

        # bid 0 as an initial format checker
        dash_paths = self._parse_json(PhantomJSwrapper(self, timeout=120_000).get(
            url, note2='Executing signature code (this may take a couple minutes)',
            html='<!DOCTYPE html>', video_id=video_id, jscode=self._DASH_JS % {
                'tvid': video_info['tvId'],
                'vid': video_info['vid'],
                'src': traverse_obj(next_props, ('initialProps', 'pageProps', 'ptid'),
                                    expected_type=str, default='04022001010011000000'),
                'uid': uid,
                'dfp': self._get_cookie('dfp', ''),
                'mode': self._get_cookie('mod', 'intl'),
                'lang': self._get_cookie('lang', 'en_us'),
                'bid_list': '[' + ','.join(['0', *self._BID_TAGS.keys()]) + ']',
                'ut_list': '[' + ','.join(ut_list) + ']',
                'cmd5x_func': self._extract_cmd5x_function(webpage, video_id),
            })[1].strip(), video_id)

        formats, subtitles = [], {}
        initial_format_data = self._download_json(
            urljoin('https://cache-video.iq.com', dash_paths['0']), video_id,
            note='Downloading initial video format info', errnote='Unable to download initial video format info')['data']

        preview_time = traverse_obj(
            initial_format_data, ('boss_ts', (None, 'data'), ('previewTime', 'rtime')), expected_type=float_or_none, get_all=False)
        if traverse_obj(initial_format_data, ('boss_ts', 'data', 'prv'), expected_type=int_or_none):
            self.report_warning('This preview video is limited%s' % format_field(preview_time, None, ' to %s seconds'))

        # TODO: Extract audio-only formats
        for bid in set(traverse_obj(initial_format_data, ('program', 'video', ..., 'bid'), expected_type=str_or_none)):
            dash_path = dash_paths.get(bid)
            if not dash_path:
                self.report_warning(f'Unknown format id: {bid}. It is currently not being extracted')
                continue
            format_data = traverse_obj(self._download_json(
                urljoin('https://cache-video.iq.com', dash_path), video_id,
                note=f'Downloading format data for {self._BID_TAGS[bid]}', errnote='Unable to download format data',
                fatal=False), 'data', expected_type=dict)

            video_format = traverse_obj(format_data, ('program', 'video', lambda _, v: str(v['bid']) == bid),
                                        expected_type=dict, get_all=False) or {}
            extracted_formats = []
            if video_format.get('m3u8Url'):
                extracted_formats.extend(self._extract_m3u8_formats(
                    urljoin(format_data.get('dm3u8', 'https://cache-m.iq.com/dc/dt/'), video_format['m3u8Url']),
                    'mp4', m3u8_id=bid, fatal=False))
            if video_format.get('mpdUrl'):
                # TODO: Properly extract mpd hostname
                extracted_formats.extend(self._extract_mpd_formats(
                    urljoin(format_data.get('dm3u8', 'https://cache-m.iq.com/dc/dt/'), video_format['mpdUrl']),
                    mpd_id=bid, fatal=False))
            if video_format.get('m3u8'):
                ff = video_format.get('ff', 'ts')
                if ff == 'ts':
                    m3u8_formats, _ = self._parse_m3u8_formats_and_subtitles(
                        video_format['m3u8'], ext='mp4', m3u8_id=bid, fatal=False)
                    extracted_formats.extend(m3u8_formats)
                elif ff == 'm4s':
                    mpd_data = traverse_obj(
                        self._parse_json(video_format['m3u8'], video_id, fatal=False), ('payload', ..., 'data'), expected_type=str)
                    if not mpd_data:
                        continue
                    mpd_formats, _ = self._parse_mpd_formats_and_subtitles(
                        mpd_data, bid, format_data.get('dm3u8', 'https://cache-m.iq.com/dc/dt/'))
                    extracted_formats.extend(mpd_formats)
                else:
                    self.report_warning(f'{ff} formats are currently not supported')

            if not extracted_formats:
                if video_format.get('s'):
                    self.report_warning(f'{self._BID_TAGS[bid]} format is restricted')
                else:
                    self.report_warning(f'Unable to extract {self._BID_TAGS[bid]} format')
            for f in extracted_formats:
                f.update({
                    'quality': qualities(list(self._BID_TAGS.keys()))(bid),
                    'format_note': self._BID_TAGS[bid],
                    **parse_resolution(video_format.get('scrsz'))
                })
            formats.extend(extracted_formats)

        for sub_format in traverse_obj(initial_format_data, ('program', 'stl', ...), expected_type=dict):
            lang = self._LID_TAGS.get(str_or_none(sub_format.get('lid')), sub_format.get('_name'))
            subtitles.setdefault(lang, []).extend([{
                'ext': format_ext,
                'url': urljoin(initial_format_data.get('dstl', 'http://meta.video.iqiyi.com'), sub_format[format_key])
            } for format_key, format_ext in [('srt', 'srt'), ('webvtt', 'vtt')] if sub_format.get(format_key)])

        extra_metadata = page_data.get('albumInfo') if video_info.get('albumId') and page_data.get('albumInfo') else video_info
        return {
            'id': video_id,
            'title': video_info['name'],
            'formats': formats,
            'subtitles': subtitles,
            'description': video_info.get('mergeDesc'),
            'duration': parse_duration(video_info.get('len')),
            'age_limit': parse_age_limit(video_info.get('rating')),
            'average_rating': traverse_obj(page_data, ('playScoreInfo', 'score'), expected_type=float_or_none),
            'timestamp': parse_iso8601(video_info.get('isoUploadDate')),
            'categories': traverse_obj(extra_metadata, ('videoTagMap', ..., ..., 'name'), expected_type=str),
            'cast': traverse_obj(extra_metadata, ('actorArr', ..., 'name'), expected_type=str),
            'episode_number': int_or_none(video_info.get('order')) or None,
            'series': video_info.get('albumName'),
        }


class IqAlbumIE(InfoExtractor):
    IE_NAME = 'iq.com:album'
    _VALID_URL = r'https?://(?:www\.)?iq\.com/album/(?:[\w%-]*-)?(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://www.iq.com/album/one-piece-1999-1bk9icvr331',
        'info_dict': {
            'id': '1bk9icvr331',
            'title': 'One Piece',
            'description': 'Subtitle available on Sunday 4PM（GMT+8）.'
        },
        'playlist_mincount': 238
    }, {
        # Movie/single video
        'url': 'https://www.iq.com/album/九龙城寨-2021-22yjnij099k',
        'info_dict': {
            'ext': 'mp4',
            'id': '22yjnij099k',
            'title': '九龙城寨',
            'description': 'md5:8a09f50b8ba0db4dc69bc7c844228044',
            'duration': 5000,
            'timestamp': 1641911371,
            'upload_date': '20220111',
            'series': '九龙城寨',
            'cast': ['Shi Yan Neng', 'Yu Lang', 'Peter  lv', 'Sun Zi Jun', 'Yang Xiao Bo'],
            'age_limit': 13,
            'average_rating': float,
        },
        'expected_warnings': ['format is restricted']
    }]

    def _entries(self, album_id_num, page_ranges, album_id=None, mode_code='intl', lang_code='en_us'):
        for page_range in page_ranges:
            page = self._download_json(
                f'https://pcw-api.iq.com/api/episodeListSource/{album_id_num}', album_id,
                note=f'Downloading video list episodes {page_range.get("msg", "")}',
                errnote='Unable to download video list', query={
                    'platformId': 3,
                    'modeCode': mode_code,
                    'langCode': lang_code,
                    'endOrder': page_range['to'],
                    'startOrder': page_range['from']
                })
            for video in page['data']['epg']:
                yield self.url_result('https://www.iq.com/play/%s' % (video.get('playLocSuffix') or video['qipuIdStr']),
                                      IqIE.ie_key(), video.get('qipuIdStr'), video.get('name'))

    def _real_extract(self, url):
        album_id = self._match_id(url)
        webpage = self._download_webpage(url, album_id)
        next_data = self._search_nextjs_data(webpage, album_id)
        album_data = next_data['props']['initialState']['album']['videoAlbumInfo']

        if album_data.get('videoType') == 'singleVideo':
            return self.url_result('https://www.iq.com/play/%s' % album_id, IqIE.ie_key())
        return self.playlist_result(
            self._entries(album_data['albumId'], album_data['totalPageRange'], album_id,
                          traverse_obj(next_data, ('props', 'initialProps', 'pageProps', 'modeCode')),
                          traverse_obj(next_data, ('props', 'initialProps', 'pageProps', 'langCode'))),
            album_id, album_data.get('name'), album_data.get('desc'))
