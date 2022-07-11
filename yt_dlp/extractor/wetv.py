import re
import time
import urllib.parse

from .common import InfoExtractor
from ..aes import aes_cbc_encrypt
from ..compat import compat_ord
from ..utils import bytes_to_intlist, random_user_agent


class WeTvBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://(?:www\.)?wetv\.vip/(?:[^?#]+/)?play'

    def _get_ckey(self, video_id, url, app_version, platform):
        def get_payload_checksum(payload):
            checksum = 0
            for char in payload:
                checksum += compat_ord(char)
            return str(checksum)

        payload_components = [
            '',
            video_id,
            str(int(time.time())),
            'mg3c3b04ba',
            app_version,
            '0000000000000000',  # guid
            platform,
            url[:48],
            random_user_agent().lower()[:48],  # user_agent
            ''[:48],  # referer
            'Mozilla',  # nav_code_name
            'Netscape',  # nav_name
            'Win32',  # nav_platform
            '00',
            ''
        ]

        payload_components.insert(1, get_payload_checksum('|'.join(payload_components)))

        ciphertext_bytes = aes_cbc_encrypt(
            bytes_to_intlist(bytes_to_intlist(bytes('|'.join(payload_components), 'utf-8'))),
            bytes_to_intlist(bytearray.fromhex('4f6bdaa39e2f8cb07f5e722d9edef314')),
            bytes_to_intlist(bytearray.fromhex('01504af356e619cf2e42bba68c3f70f9')),
            'whitespace')

        return ''.join('{:02x}'.format(x) for x in ciphertext_bytes)

    def _get_video_api_response(self, video_url, video_id, series_id, subtitle_format, video_format):
        app_version = '3.5.57'
        platform = '4830201'

        ckey = self._get_ckey(video_id, video_url, app_version, platform)
        query = {
            'vid': video_id,
            'cid': series_id,
            'cKey': ckey,
            'encryptVer': '8.1',
            'spcaptiontype': '1' if subtitle_format == 'vtt' else '0',  # 0 - SRT, 1 - VTT
            'sphls': '1' if video_format == 'hls' else '0',  # 0 - MP4, 1 - HLS
            'defn': 'shd',  # Video quality, '': 480p, 'shd': 720p
            'spsrt': '1',  # Enable subtitles
            'sphttps': '1',  # Enable HTTPS
            'otype': 'json',  # Response format: xml, json,
            'dtype': '1',
            'spwm': '1',
            'host': 'wetv.vip',  # These three values are needed for SHD
            'referer': 'wetv.vip',
            'ehost': video_url,
            'appVer': app_version,
            'platform': platform,
        }

        return self._parse_json(self._download_webpage(
            'https://play.wetv.vip/getvinfo', video_id,
            query=query).replace('QZOutputJson=', '').replace(';', ''), video_id)


class WeTvEpisodeIE(WeTvBaseIE):
    IE_NAME = 'wetv:episode'
    _VALID_URL = WeTvBaseIE._VALID_URL_BASE + r'/(?P<series_id>\w+)(?:-[^?#]+)?/(?P<id>\w+)(?:-[^?#]+)?'

    _TESTS = [{
        'url': 'https://wetv.vip/en/play/air11ooo2rdsdi3-Cute-Programmer/v0040pr89t9-EP1-Cute-Programmer',
        'md5': 'a046f565c9dce9b263a0465a422cd7bf',
        'info_dict': {
            'id': 'v0040pr89t9',
            'ext': 'mp4',
            'title': 'EP1: Cute Programmer',
            'description': 'md5:e87beab3bf9f392d6b9e541a63286343',
            'thumbnail': 'http://puui.wetvinfo.com/vcover_hz_pic/0/air11ooo2rdsdi31630998533838/0',
        },
    }, {
        'url': 'https://wetv.vip/en/play/u37kgfnfzs73kiu/p0039b9nvik',
        'md5': '4d9d69bcfd11da61f4aae64fc6b316b3',
        'info_dict': {
            'id': 'p0039b9nvik',
            'ext': 'mp4',
            'title': 'EP1: You Are My Glory',
            'description': 'md5:831363a4c3b4d7615e1f3854be3a123b',
            'thumbnail': 'http://puui.wetvinfo.com/vcover_hz_pic/0/u37kgfnfzs73kiu1626940017413/0',
        },
    }, {
        'url': 'https://wetv.vip/en/play/lcxgwod5hapghvw-WeTV-PICK-A-BOO/i0042y00lxp-Zhao-Lusi-Describes-The-First-Experiences-She-Had-In-Who-Rules-The-World-%7C-WeTV-PICK-A-BOO',
        'md5': '71133f5c2d5d6cad3427e1b010488280',
        'info_dict': {
            'id': 'i0042y00lxp',
            'ext': 'mp4',
            'title': 'md5:f7a0857dbe5fbbe2e7ad630b92b54e6a',
            'description': 'md5:76260cb9cdc0ef76826d7ca9d92fadfa',
            'thumbnail': 'http://puui.wetvinfo.com/vcover_hz_pic/0/lcxgwod5hapghvw1631668972721/0',
        },
    }]

    def _extract_video_formats_and_subtitles(self, video_id, api_response):
        video_response = api_response['vl']['vi'][0]

        formats, subtitles = [], {}
        for video_format in video_response['ul']['ui']:
            if video_format.get('hls'):
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    video_format['url'] + video_format['hls']['pname'], video_id, 'mp4', fatal=False)

                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            else:
                formats.append({
                    'url': f"{video_format['url']}{video_response['fn']}?vkey={video_response['fvkey']}",
                    'width': video_response.get('vw'),
                    'height': video_response.get('vh'),
                    'ext': 'mp4',
                })

        return formats, subtitles

    def _extract_video_subtitles(self, api_response, subtitles_format):
        subtitles = {}
        for subtitle in api_response['sfl']['fi']:
            subtitles[subtitle['lang'].lower()] = [{
                'url': subtitle['url'],
                'ext': subtitles_format,
                'protocol': 'm3u8_native' if subtitles_format == 'vtt' else 'http'
            }]

        return subtitles

    def _real_extract(self, url):
        video_id, series_id = self._match_valid_url(url).group('id', 'series_id')
        webpage = self._download_webpage(url, video_id)

        formats, subtitles = [], {}
        for video_format, subtitle_format in (('mp4', 'srt'), ('hls', 'vtt')):
            api_response = self._get_video_api_response(url, video_id, series_id, subtitle_format, video_format)

            fmts, subs = self._extract_video_formats_and_subtitles(video_id, api_response)
            native_subtitles = self._extract_video_subtitles(api_response, subtitle_format)

            formats.extend(fmts)
            self._merge_subtitles(native_subtitles, target=subtitles)

        return {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': self._og_search_thumbnail(webpage),
        }


class WeTvSeriesIE(WeTvBaseIE):
    _VALID_URL = WeTvBaseIE._VALID_URL_BASE + r'/(?P<id>\w+)(?:-[^?#]+)?/?(?:[?#]|$)'

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
        series_id = self._match_id(url)
        webpage = self._download_webpage(url, series_id)

        parsed_url = urllib.parse.urlparse(url)

        return self.playlist_result(
            [self.url_result(parsed_url._replace(path=path).geturl(), WeTvEpisodeIE)
             for path in re.findall(r'<a[^>]+class="play-video__link"[^>]+href="(?P<path>[^"]+)', webpage)],
            series_id, self._og_search_title(webpage), self._og_search_description(webpage))
