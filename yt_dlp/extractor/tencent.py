import functools
import random
import re
import string
import time

from .common import InfoExtractor
from ..aes import aes_cbc_encrypt_bytes
from ..utils import (
    ExtractorError,
    determine_ext,
    float_or_none,
    int_or_none,
    js_to_json,
    traverse_obj,
    urljoin,
)


class TencentBaseIE(InfoExtractor):
    """Subclasses must set _API_URL, _APP_VERSION, _PLATFORM, _HOST, _REFERER"""

    def _check_api_response(self, api_response):
        msg = api_response.get('msg')
        if api_response.get('code') != '0.0' and msg is not None:
            if msg in (
                '您所在区域暂无此内容版权（如设置VPN请关闭后重试）',
                'This content is not available in your area due to copyright restrictions. Please choose other videos.'
            ):
                self.raise_geo_restricted()
            raise ExtractorError(f'Tencent said: {msg}')

    def _get_ckey(self, video_id, url, guid):
        ua = self.get_param('http_headers')['User-Agent']

        payload = (f'{video_id}|{int(time.time())}|mg3c3b04ba|{self._APP_VERSION}|{guid}|'
                   f'{self._PLATFORM}|{url[:48]}|{ua.lower()[:48]}||Mozilla|Netscape|Windows x86_64|00|')

        return aes_cbc_encrypt_bytes(
            bytes(f'|{sum(map(ord, payload))}|{payload}', 'utf-8'),
            b'Ok\xda\xa3\x9e/\x8c\xb0\x7f^r-\x9e\xde\xf3\x14',
            b'\x01PJ\xf3V\xe6\x19\xcf.B\xbb\xa6\x8c?p\xf9',
            padding_mode='whitespace').hex().upper()

    def _get_video_api_response(self, video_url, video_id, series_id, subtitle_format, video_format, video_quality):
        guid = ''.join(random.choices(string.digits + string.ascii_lowercase, k=16))
        ckey = self._get_ckey(video_id, video_url, guid)
        query = {
            'vid': video_id,
            'cid': series_id,
            'cKey': ckey,
            'encryptVer': '8.1',
            'spcaptiontype': '1' if subtitle_format == 'vtt' else '0',
            'sphls': '2' if video_format == 'hls' else '0',
            'dtype': '3' if video_format == 'hls' else '0',
            'defn': video_quality,
            'spsrt': '2',  # Enable subtitles
            'sphttps': '1',  # Enable HTTPS
            'otype': 'json',
            'spwm': '1',
            'hevclv': '28',  # Enable HEVC
            'drm': '40',  # Enable DRM
            # For HDR
            'spvideo': '4',
            'spsfrhdr': '100',
            # For SHD
            'host': self._HOST,
            'referer': self._REFERER,
            'ehost': video_url,
            'appVer': self._APP_VERSION,
            'platform': self._PLATFORM,
            # For VQQ
            'guid': guid,
            'flowid': ''.join(random.choices(string.digits + string.ascii_lowercase, k=32)),
        }

        return self._search_json(r'QZOutputJson=', self._download_webpage(
            self._API_URL, video_id, query=query), 'api_response', video_id)

    def _extract_video_formats_and_subtitles(self, api_response, video_id):
        video_response = api_response['vl']['vi'][0]

        formats, subtitles = [], {}
        for video_format in video_response['ul']['ui']:
            if video_format.get('hls') or determine_ext(video_format['url']) == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    video_format['url'] + traverse_obj(video_format, ('hls', 'pt'), default=''),
                    video_id, 'mp4', fatal=False)

                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            else:
                formats.append({
                    'url': f'{video_format["url"]}{video_response["fn"]}?vkey={video_response["fvkey"]}',
                    'ext': 'mp4',
                })

        identifier = video_response.get('br')
        format_response = traverse_obj(
            api_response, ('fl', 'fi', lambda _, v: v['br'] == identifier),
            expected_type=dict, get_all=False) or {}
        common_info = {
            'width': video_response.get('vw'),
            'height': video_response.get('vh'),
            'abr': float_or_none(format_response.get('audiobandwidth'), scale=1000),
            'vbr': float_or_none(format_response.get('bandwidth'), scale=1000),
            'fps': format_response.get('vfps'),
            'format': format_response.get('sname'),
            'format_id': format_response.get('name'),
            'format_note': format_response.get('resolution'),
            'dynamic_range': {'hdr10': 'hdr10'}.get(format_response.get('name'), 'sdr'),
            'has_drm': format_response.get('drm', 0) != 0,
        }
        for f in formats:
            f.update(common_info)

        return formats, subtitles

    def _extract_video_native_subtitles(self, api_response):
        subtitles = {}
        for subtitle in traverse_obj(api_response, ('sfl', 'fi')) or ():
            subtitles.setdefault(subtitle['lang'].lower(), []).append({
                'url': subtitle['url'],
                'ext': 'srt' if subtitle.get('captionType') == 1 else 'vtt',
                'protocol': 'm3u8_native' if determine_ext(subtitle['url']) == 'm3u8' else 'http',
            })

        return subtitles

    def _extract_all_video_formats_and_subtitles(self, url, video_id, series_id):
        api_responses = [self._get_video_api_response(url, video_id, series_id, 'srt', 'hls', 'hd')]
        self._check_api_response(api_responses[0])
        qualities = traverse_obj(api_responses, (0, 'fl', 'fi', ..., 'name')) or ('shd', 'fhd')
        for q in qualities:
            if q not in ('ld', 'sd', 'hd'):
                api_responses.append(self._get_video_api_response(
                    url, video_id, series_id, 'vtt', 'hls', q))
                self._check_api_response(api_responses[-1])

        formats, subtitles = [], {}
        for api_response in api_responses:
            fmts, subs = self._extract_video_formats_and_subtitles(api_response, video_id)
            native_subtitles = self._extract_video_native_subtitles(api_response)

            formats.extend(fmts)
            self._merge_subtitles(subs, native_subtitles, target=subtitles)

        return formats, subtitles

    def _get_clean_title(self, title):
        return re.sub(
            r'\s*[_\-]\s*(?:Watch online|Watch HD Video Online|WeTV|腾讯视频|(?:高清)?1080P在线观看平台).*?$',
            '', title or '').strip() or None


class VQQBaseIE(TencentBaseIE):
    _VALID_URL_BASE = r'https?://v\.qq\.com'

    _API_URL = 'https://h5vv6.video.qq.com/getvinfo'
    _APP_VERSION = '3.5.57'
    _PLATFORM = '10901'
    _HOST = 'v.qq.com'
    _REFERER = 'v.qq.com'

    def _get_webpage_metadata(self, webpage, video_id):
        return self._search_json(
            r'<script[^>]*>[^<]*window\.__(?:pinia|PINIA__)\s*=',
            webpage, 'pinia data', video_id, transform_source=js_to_json, fatal=False)


class VQQVideoIE(VQQBaseIE):
    IE_NAME = 'vqq:video'
    _VALID_URL = VQQBaseIE._VALID_URL_BASE + r'/x/(?:page|cover/(?P<series_id>\w+))/(?P<id>\w+)'

    _TESTS = [{
        'url': 'https://v.qq.com/x/page/q326831cny0.html',
        'md5': 'b11c9cb781df710d686b950376676e2a',
        'info_dict': {
            'id': 'q326831cny0',
            'ext': 'mp4',
            'title': '我是选手：雷霆裂阵，终极时刻',
            'description': 'md5:e7ed70be89244017dac2a835a10aeb1e',
            'thumbnail': r're:^https?://[^?#]+q326831cny0',
            'format_id': r're:^shd',
        },
    }, {
        'url': 'https://v.qq.com/x/page/o3013za7cse.html',
        'md5': 'a1bcf42c6d28c189bd2fe2d468abb287',
        'info_dict': {
            'id': 'o3013za7cse',
            'ext': 'mp4',
            'title': '欧阳娜娜VLOG',
            'description': 'md5:29fe847497a98e04a8c3826e499edd2e',
            'thumbnail': r're:^https?://[^?#]+o3013za7cse',
            'format_id': r're:^shd',
        },
    }, {
        'url': 'https://v.qq.com/x/cover/7ce5noezvafma27/a00269ix3l8.html',
        'md5': '87968df6238a65d2478f19c25adf850b',
        'info_dict': {
            'id': 'a00269ix3l8',
            'ext': 'mp4',
            'title': '鸡毛飞上天 第01集',
            'description': 'md5:8cae3534327315b3872fbef5e51b5c5b',
            'thumbnail': r're:^https?://[^?#]+7ce5noezvafma27',
            'series': '鸡毛飞上天',
            'format_id': r're:^shd',
        },
        'skip': '404',
    }, {
        'url': 'https://v.qq.com/x/cover/mzc00200p29k31e/s0043cwsgj0.html',
        'md5': 'fadd10bf88aec3420f06f19ee1d24c5b',
        'info_dict': {
            'id': 's0043cwsgj0',
            'ext': 'mp4',
            'title': '第1集：如何快乐吃糖？',
            'description': 'md5:1d8c3a0b8729ae3827fa5b2d3ebd5213',
            'thumbnail': r're:^https?://[^?#]+s0043cwsgj0',
            'series': '青年理工工作者生活研究所',
            'format_id': r're:^shd',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # Geo-restricted to China
        'url': 'https://v.qq.com/x/cover/mcv8hkc8zk8lnov/x0036x5qqsr.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id, series_id = self._match_valid_url(url).group('id', 'series_id')
        webpage = self._download_webpage(url, video_id)
        webpage_metadata = self._get_webpage_metadata(webpage, video_id)

        formats, subtitles = self._extract_all_video_formats_and_subtitles(url, video_id, series_id)
        return {
            'id': video_id,
            'title': self._get_clean_title(self._og_search_title(webpage)
                                           or traverse_obj(webpage_metadata, ('global', 'videoInfo', 'title'))),
            'description': (self._og_search_description(webpage)
                            or traverse_obj(webpage_metadata, ('global', 'videoInfo', 'desc'))),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': (self._og_search_thumbnail(webpage)
                          or traverse_obj(webpage_metadata, ('global', 'videoInfo', 'pic160x90'))),
            'series': traverse_obj(webpage_metadata, ('global', 'coverInfo', 'title')),
        }


class VQQSeriesIE(VQQBaseIE):
    IE_NAME = 'vqq:series'
    _VALID_URL = VQQBaseIE._VALID_URL_BASE + r'/x/cover/(?P<id>\w+)\.html/?(?:[?#]|$)'

    _TESTS = [{
        'url': 'https://v.qq.com/x/cover/7ce5noezvafma27.html',
        'info_dict': {
            'id': '7ce5noezvafma27',
            'title': '鸡毛飞上天',
            'description': 'md5:8cae3534327315b3872fbef5e51b5c5b',
        },
        'playlist_count': 55,
    }, {
        'url': 'https://v.qq.com/x/cover/oshd7r0vy9sfq8e.html',
        'info_dict': {
            'id': 'oshd7r0vy9sfq8e',
            'title': '恋爱细胞2',
            'description': 'md5:9d8a2245679f71ca828534b0f95d2a03',
        },
        'playlist_count': 12,
    }]

    def _real_extract(self, url):
        series_id = self._match_id(url)
        webpage = self._download_webpage(url, series_id)
        webpage_metadata = self._get_webpage_metadata(webpage, series_id)

        episode_paths = [f'/x/cover/{series_id}/{video_id}.html' for video_id in re.findall(
            r'<div[^>]+data-vid="(?P<video_id>[^"]+)"[^>]+class="[^"]+episode-item-rect--number',
            webpage)]

        return self.playlist_from_matches(
            episode_paths, series_id, ie=VQQVideoIE, getter=functools.partial(urljoin, url),
            title=self._get_clean_title(traverse_obj(webpage_metadata, ('coverInfo', 'title'))
                                        or self._og_search_title(webpage)),
            description=(traverse_obj(webpage_metadata, ('coverInfo', 'description'))
                         or self._og_search_description(webpage)))


class WeTvBaseIE(TencentBaseIE):
    _VALID_URL_BASE = r'https?://(?:www\.)?wetv\.vip/(?:[^?#]+/)?play'

    _API_URL = 'https://play.wetv.vip/getvinfo'
    _APP_VERSION = '3.5.57'
    _PLATFORM = '4830201'
    _HOST = 'wetv.vip'
    _REFERER = 'wetv.vip'

    def _get_webpage_metadata(self, webpage, video_id):
        return self._parse_json(
            traverse_obj(self._search_nextjs_data(webpage, video_id), ('props', 'pageProps', 'data')),
            video_id, fatal=False)

    def _extract_episode(self, url):
        video_id, series_id = self._match_valid_url(url).group('id', 'series_id')
        webpage = self._download_webpage(url, video_id)
        webpage_metadata = self._get_webpage_metadata(webpage, video_id)

        formats, subtitles = self._extract_all_video_formats_and_subtitles(url, video_id, series_id)
        return {
            'id': video_id,
            'title': self._get_clean_title(self._og_search_title(webpage)
                                           or traverse_obj(webpage_metadata, ('coverInfo', 'title'))),
            'description': (traverse_obj(webpage_metadata, ('coverInfo', 'description'))
                            or self._og_search_description(webpage)),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': self._og_search_thumbnail(webpage),
            'duration': int_or_none(traverse_obj(webpage_metadata, ('videoInfo', 'duration'))),
            'series': traverse_obj(webpage_metadata, ('coverInfo', 'title')),
            'episode_number': int_or_none(traverse_obj(webpage_metadata, ('videoInfo', 'episode'))),
        }

    def _extract_series(self, url, ie):
        series_id = self._match_id(url)
        webpage = self._download_webpage(url, series_id)
        webpage_metadata = self._get_webpage_metadata(webpage, series_id)

        episode_paths = ([f'/play/{series_id}/{episode["vid"]}' for episode in webpage_metadata.get('videoList')]
                         or re.findall(r'<a[^>]+class="play-video__link"[^>]+href="(?P<path>[^"]+)', webpage))

        return self.playlist_from_matches(
            episode_paths, series_id, ie=ie, getter=functools.partial(urljoin, url),
            title=self._get_clean_title(traverse_obj(webpage_metadata, ('coverInfo', 'title'))
                                        or self._og_search_title(webpage)),
            description=(traverse_obj(webpage_metadata, ('coverInfo', 'description'))
                         or self._og_search_description(webpage)))


class WeTvEpisodeIE(WeTvBaseIE):
    IE_NAME = 'wetv:episode'
    _VALID_URL = WeTvBaseIE._VALID_URL_BASE + r'/(?P<series_id>\w+)(?:-[^?#]+)?/(?P<id>\w+)(?:-[^?#]+)?'

    _TESTS = [{
        'url': 'https://wetv.vip/en/play/air11ooo2rdsdi3-Cute-Programmer/v0040pr89t9-EP1-Cute-Programmer',
        'md5': '0c70fdfaa5011ab022eebc598e64bbbe',
        'info_dict': {
            'id': 'v0040pr89t9',
            'ext': 'mp4',
            'title': 'EP1: Cute Programmer',
            'description': 'md5:e87beab3bf9f392d6b9e541a63286343',
            'thumbnail': r're:^https?://[^?#]+air11ooo2rdsdi3',
            'series': 'Cute Programmer',
            'episode': 'Episode 1',
            'episode_number': 1,
            'duration': 2835,
            'format_id': r're:^shd',
        },
    }, {
        'url': 'https://wetv.vip/en/play/u37kgfnfzs73kiu/p0039b9nvik',
        'md5': '3b3c15ca4b9a158d8d28d5aa9d7c0a49',
        'info_dict': {
            'id': 'p0039b9nvik',
            'ext': 'mp4',
            'title': 'EP1: You Are My Glory',
            'description': 'md5:831363a4c3b4d7615e1f3854be3a123b',
            'thumbnail': r're:^https?://[^?#]+u37kgfnfzs73kiu',
            'series': 'You Are My Glory',
            'episode': 'Episode 1',
            'episode_number': 1,
            'duration': 2454,
            'format_id': r're:^shd',
        },
    }, {
        'url': 'https://wetv.vip/en/play/lcxgwod5hapghvw-WeTV-PICK-A-BOO/i0042y00lxp-Zhao-Lusi-Describes-The-First-Experiences-She-Had-In-Who-Rules-The-World-%7C-WeTV-PICK-A-BOO',
        'md5': '71133f5c2d5d6cad3427e1b010488280',
        'info_dict': {
            'id': 'i0042y00lxp',
            'ext': 'mp4',
            'title': 'md5:f7a0857dbe5fbbe2e7ad630b92b54e6a',
            'description': 'md5:76260cb9cdc0ef76826d7ca9d92fadfa',
            'thumbnail': r're:^https?://[^?#]+i0042y00lxp',
            'series': 'WeTV PICK-A-BOO',
            'episode': 'Episode 0',
            'episode_number': 0,
            'duration': 442,
            'format_id': r're:^shd',
        },
    }]

    def _real_extract(self, url):
        return self._extract_episode(url)


class WeTvSeriesIE(WeTvBaseIE):
    _VALID_URL = WeTvBaseIE._VALID_URL_BASE + r'/(?P<id>\w+)(?:-[^/?#]+)?/?(?:[?#]|$)'

    _TESTS = [{
        'url': 'https://wetv.vip/play/air11ooo2rdsdi3-Cute-Programmer',
        'info_dict': {
            'id': 'air11ooo2rdsdi3',
            'title': 'Cute Programmer',
            'description': 'md5:e87beab3bf9f392d6b9e541a63286343',
        },
        'playlist_count': 30,
    }, {
        'url': 'https://wetv.vip/en/play/u37kgfnfzs73kiu-You-Are-My-Glory',
        'info_dict': {
            'id': 'u37kgfnfzs73kiu',
            'title': 'You Are My Glory',
            'description': 'md5:831363a4c3b4d7615e1f3854be3a123b',
        },
        'playlist_count': 32,
    }]

    def _real_extract(self, url):
        return self._extract_series(url, WeTvEpisodeIE)


class IflixBaseIE(WeTvBaseIE):
    _VALID_URL_BASE = r'https?://(?:www\.)?iflix\.com/(?:[^?#]+/)?play'

    _API_URL = 'https://vplay.iflix.com/getvinfo'
    _APP_VERSION = '3.5.57'
    _PLATFORM = '330201'
    _HOST = 'www.iflix.com'
    _REFERER = 'www.iflix.com'


class IflixEpisodeIE(IflixBaseIE):
    IE_NAME = 'iflix:episode'
    _VALID_URL = IflixBaseIE._VALID_URL_BASE + r'/(?P<series_id>\w+)(?:-[^?#]+)?/(?P<id>\w+)(?:-[^?#]+)?'

    _TESTS = [{
        'url': 'https://www.iflix.com/en/play/daijrxu03yypu0s/a0040kvgaza',
        'md5': '9740f9338c3a2105290d16b68fb3262f',
        'info_dict': {
            'id': 'a0040kvgaza',
            'ext': 'mp4',
            'title': 'EP1: Put Your Head On My Shoulder 2021',
            'description': 'md5:c095a742d3b7da6dfedd0c8170727a42',
            'thumbnail': r're:^https?://[^?#]+daijrxu03yypu0s',
            'series': 'Put Your Head On My Shoulder 2021',
            'episode': 'Episode 1',
            'episode_number': 1,
            'duration': 2639,
            'format_id': r're:^shd',
        },
    }, {
        'url': 'https://www.iflix.com/en/play/fvvrcc3ra9lbtt1-Take-My-Brother-Away/i0029sd3gm1-EP1%EF%BC%9ATake-My-Brother-Away',
        'md5': '375c9b8478fdedca062274b2c2f53681',
        'info_dict': {
            'id': 'i0029sd3gm1',
            'ext': 'mp4',
            'title': 'EP1：Take My Brother Away',
            'description': 'md5:f0f7be1606af51cd94d5627de96b0c76',
            'thumbnail': r're:^https?://[^?#]+fvvrcc3ra9lbtt1',
            'series': 'Take My Brother Away',
            'episode': 'Episode 1',
            'episode_number': 1,
            'duration': 228,
            'format_id': r're:^shd',
        },
    }]

    def _real_extract(self, url):
        return self._extract_episode(url)


class IflixSeriesIE(IflixBaseIE):
    _VALID_URL = IflixBaseIE._VALID_URL_BASE + r'/(?P<id>\w+)(?:-[^/?#]+)?/?(?:[?#]|$)'

    _TESTS = [{
        'url': 'https://www.iflix.com/en/play/g21a6qk4u1s9x22-You-Are-My-Hero',
        'info_dict': {
            'id': 'g21a6qk4u1s9x22',
            'title': 'You Are My Hero',
            'description': 'md5:9c4d844bc0799cd3d2b5aed758a2050a',
        },
        'playlist_count': 40,
    }, {
        'url': 'https://www.iflix.com/play/0s682hc45t0ohll',
        'info_dict': {
            'id': '0s682hc45t0ohll',
            'title': 'Miss Gu Who Is Silent',
            'description': 'md5:a9651d0236f25af06435e845fa2f8c78',
        },
        'playlist_count': 20,
    }]

    def _real_extract(self, url):
        return self._extract_series(url, IflixEpisodeIE)
