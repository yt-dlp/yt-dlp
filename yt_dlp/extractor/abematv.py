import io
import json
import time
import hashlib
import hmac
import re
import struct
from base64 import urlsafe_b64encode
from binascii import unhexlify

from .common import InfoExtractor
from ..aes import aes_ecb_decrypt
from ..compat import compat_urllib_response, compat_urllib_parse_urlparse
from ..utils import (
    ExtractorError,
    decode_base,
    int_or_none,
    random_uuidv4,
    request_to_url,
    time_seconds,
    update_url_query,
    traverse_obj,
    YoutubeDLExtractorHandler,
    intlist_to_bytes,
    bytes_to_intlist,
    urljoin,
)


class AbemaLicenseHandler(YoutubeDLExtractorHandler):
    STRTABLE = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    HKEY = b'3AF0298C219469522A313570E8583005A642E73EDD58E3EA2FB7339D3DF1597E'

    def __init__(self, ie: 'AbemaTVIE'):
        # the protcol that this should really handle is 'abematv-license://'
        # abematv_license_open is just a placeholder for development purposes
        # ref. https://github.com/python/cpython/blob/f4c03484da59049eb62a9bf7777b963e2267d187/Lib/urllib/request.py#L510
        setattr(self, 'abematv-license_open', getattr(self, 'abematv_license_open'))
        self.ie = ie

    def _get_videokey_from_ticket(self, ticket):
        to_show = self.ie._downloader.params.get('verbose', False)
        media_token_response = self.ie._download_json(
            'https://api.abema.io/v1/media/token', None, note='Fetching media token' if to_show else False,
            query={
                'osName': 'android',
                'osVersion': '6.0.1',
                'osLang': 'ja_JP',
                'osTimezone': 'Asia/Tokyo',
                'appId': 'tv.abema',
                'appVersion': '3.27.1'
            },
            headers={'Authorization': 'Bearer ' + self.ie._USERTOKEN})

        license_response = self.ie._download_json(
            'https://license.abema.io/abematv-hls', None, note='Requesting playback license' if to_show else False,
            query={'t': media_token_response['token']},
            data=json.dumps({
                'kv': 'a',
                'lt': ticket
            }).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
            })

        res = decode_base(license_response['k'], self.STRTABLE)
        encvideokey = bytes_to_intlist(struct.pack('>QQ', res >> 64, res & 0xffffffffffffffff))

        h = hmac.new(
            unhexlify(self.HKEY),
            (license_response['cid'] + self.ie._DEVICE_ID).encode('utf-8'),
            digestmod=hashlib.sha256)
        enckey = bytes_to_intlist(h.digest())

        return intlist_to_bytes(aes_ecb_decrypt(encvideokey, enckey))

    def abematv_license_open(self, url):
        url = request_to_url(url)
        ticket = compat_urllib_parse_urlparse(url).netloc
        response_data = self._get_videokey_from_ticket(ticket)
        return compat_urllib_response.addinfourl(io.BytesIO(response_data), headers={
            'Content-Length': len(response_data),
        }, url=url, code=200)


class AbemaTVBaseIE(InfoExtractor):
    def _extract_breadcrumb_list(self, webpage, video_id):
        for jld in re.finditer(
                r'(?is)</span></li></ul><script[^>]+type=(["\']?)application/ld\+json\1[^>]*>(?P<json_ld>.+?)</script>',
                webpage):
            jsonld = self._parse_json(jld.group('json_ld'), video_id, fatal=False)
            if jsonld:
                if jsonld.get('@type') != 'BreadcrumbList':
                    continue
                trav = traverse_obj(jsonld, ('itemListElement', ..., 'name'))
                if trav:
                    return trav
        return []


class AbemaTVIE(AbemaTVBaseIE):
    _VALID_URL = r'https?://abema\.tv/(?P<type>now-on-air|video/episode|channels/.+?/slots)/(?P<id>[^?/]+)'
    _TESTS = [{
        'url': 'https://abema.tv/video/episode/194-25_s2_p1',
        'info_dict': {
            'id': '194-25_s2_p1',
            'title': '第1話 「チーズケーキ」　「モーニング再び」',
            'series': '異世界食堂２',
            'series_number': 2,
            'episode': '第1話 「チーズケーキ」　「モーニング再び」',
            'episode_number': 1,
        }
    }, {
        'url': 'https://abema.tv/channels/anime-live2/slots/E8tvAnMJ7a9a5d',
        'info_dict': {
            'id': 'E8tvAnMJ7a9a5d',
            'title': 'ゆるキャン△ SEASON２ 全話一挙【無料ビデオ72時間】',
            'series': 'ゆるキャン△ SEASON２',
            'episode': 'ゆるキャン△ SEASON２ 全話一挙【無料ビデオ72時間】',
            'series_number': 2,
            'episode_number': 1,
            'description': 'md5:9c5a3172ae763278f9303922f0ea5b17',
        }
    }, {
        'url': 'https://abema.tv/video/episode/87-877_s1282_p31047',
        'info_dict': {
            'id': 'E8tvAnMJ7a9a5d',
            'title': '第5話『光射す』',
            'description': 'md5:56d4fc1b4f7769ded5f923c55bb4695d',
            'thumbnail': r're:https://hayabusa\.io/.+',
            'series': '相棒',
            'episode': '第5話『光射す』',
        }
    }, {
        'url': 'https://abema.tv/now-on-air/abema-anime',
        'info_dict': {
            'id': 'abema-anime',
            # this varies
            # 'title': '女子高生の無駄づかい 全話一挙【無料ビデオ72時間】',
            'description': '24時間アニメを放送中！ABEMA アニメチャンネルでは、今期のアニメ最新作から懐かしの名作、ABEMAオリジナルの声優番組まで充実なラインナップを無料で視聴できます。その他にもABEMAでは、ニュースやオリジナルドラマ、恋愛番組、アニメ、スポーツなど、多彩な番組をいつでもお楽しみいただけます。',
            'is_live': True,
        }
    }]
    _USERTOKEN = None
    _DEVICE_ID = None
    _TIMETABLE = None

    _SECRETKEY = b'v+Gjs=25Aw5erR!J8ZuvRrCx*rGswhB&qdHd_SYerEWdU&a?3DzN9BRbp5KwY4hEmcj5#fykMjJ=AuWz5GSMY-d@H7DMEh3M@9n2G552Us$$k9cD=3TxwWe86!x#Zyhe'

    def _generate_aks(self, deviceid):
        deviceid = deviceid.encode('utf-8')
        # add 1 hour and then drop minute and secs
        ts_1hour = int((time_seconds(hours=9) // 3600 + 1) * 3600)
        time_struct = time.gmtime(ts_1hour)
        ts_1hour_str = str(ts_1hour).encode('utf-8')

        tmp = None

        def mix_once(nonce):
            nonlocal tmp
            h = hmac.new(self._SECRETKEY, digestmod=hashlib.sha256)
            h.update(nonce)
            tmp = h.digest()

        def mix_tmp(count):
            nonlocal tmp
            for i in range(count):
                mix_once(tmp)

        def mix_twist(nonce):
            nonlocal tmp
            mix_once(urlsafe_b64encode(tmp).rstrip(b'=') + nonce)

        mix_once(self._SECRETKEY)
        mix_tmp(time_struct.tm_mon)
        mix_twist(deviceid)
        mix_tmp(time_struct.tm_mday % 5)
        mix_twist(ts_1hour_str)
        mix_tmp(time_struct.tm_hour % 5)

        return urlsafe_b64encode(tmp).rstrip(b'=').decode('utf-8')

    def _get_device_token(self):
        if self._USERTOKEN:
            return self._USERTOKEN

        self._DEVICE_ID = random_uuidv4()
        aks = self._generate_aks(self._DEVICE_ID)
        user_data = self._download_json(
            'https://api.abema.io/v1/users', None, note='Authorizing',
            data=json.dumps({
                'deviceId': self._DEVICE_ID,
                'applicationKeySecret': aks,
            }).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
            })
        self._USERTOKEN = user_data['token']

        # don't allow adding it 2 times or more, though it's guarded
        self._downloader.remove_opener(AbemaLicenseHandler)
        self._downloader.add_opener(AbemaLicenseHandler(self))

        return self._USERTOKEN

    def _real_extract(self, url):
        # starting download using infojson from this extractor is undefined behavior,
        # and never be fixed in the future; you must trigger downloads by directly specifing URL.
        # (unless there's a way to hook before downloading by extractor)
        video_id, video_type = self._match_valid_url(url).group('id', 'type')
        headers = {
            'Authorization': 'Bearer ' + self._get_device_token(),
        }
        video_type = video_type.split('/')[-1]

        webpage = self._download_webpage(url, video_id)
        canonical_url = self._search_regex(
            r'<link\s+rel="canonical"\s*href="(.+?)"', webpage, 'canonical URL',
            default=url)
        info = self._search_json_ld(webpage, video_id, default={})

        title = self._search_regex(
            r'<span\s*class=".+?EpisodeTitleBlock__title">(.+?)</span>', webpage, 'title', default=None)
        if not title:
            jsonld = None
            for jld in re.finditer(
                    r'(?is)<span\s*class="com-m-Thumbnail__image">(?:</span>)?<script[^>]+type=(["\']?)application/ld\+json\1[^>]*>(?P<json_ld>.+?)</script>',
                    webpage):
                jsonld = self._parse_json(jld.group('json_ld'), video_id, fatal=False)
                if jsonld:
                    break
            if jsonld:
                title = jsonld.get('caption')
        if not title and video_type == 'now-on-air':
            if not self._TIMETABLE:
                # cache the timetable because it goes to 5MiB in size (!!)
                self._TIMETABLE = self._download_json(
                    'https://api.abema.io/v1/timetable/dataSet?debug=false', video_id,
                    headers=headers)
            now = time_seconds(hours=9)
            for slot in self._TIMETABLE.get('slots', []):
                if slot.get('channelId') != video_id:
                    continue
                if slot['startAt'] <= now and now < slot['endAt']:
                    title = slot['title']
                    break

        # read breadcrumb on top of page
        breadcrumb = self._extract_breadcrumb_list(webpage, video_id)
        if breadcrumb:
            # breadcrumb list translates to: (example is 1st test for this IE)
            # Home > Anime (genre) > Isekai Shokudo 2 (series name) > Episode 1 "Cheese cakes" "Morning again" (episode title)
            # hence this works
            info['series'] = breadcrumb[-2]
            info['episode'] = breadcrumb[-1]
            if not title:
                title = info['episode']

        description = self._html_search_regex(
            (r'<p\s+class="com-video-EpisodeDetailsBlock__content"><span\s+class=".+?">(.+?)</span></p><div',
             r'<span\s+class=".+?SlotSummary.+?">(.+?)</span></div><div',),
            webpage, 'description', default=None, group=1)
        if not description:
            og_desc = self._html_search_meta(
                ('description', 'og:description', 'twitter:description'), webpage)
            if og_desc:
                description = re.sub(r'''(?sx)
                    ^(.+?)(?:
                        アニメの動画を無料で見るならABEMA！| # anime
                        等、ABEMAでは韓流・華流番組| # korean drama
                        等、女子高生の3人に1人が|  # romance
                        等、今期の最新ドラマ # drama
                        # TODO: add more
                    )
                ''', r'\1', og_desc)

        # canonical URL may contain series and episode number
        mobj = re.search(r's(\d+)_p(\d+)$', canonical_url)
        if mobj:
            seri = int_or_none(mobj.group(1), default=float('inf'))
            epis = int_or_none(mobj.group(2), default=float('inf'))
            info['series_number'] = seri if seri < 100 else None
            # some anime like Detective Conan (though not available in AbemaTV)
            # has more than 1000 episodes (1026 as of 2021/11/15)
            info['episode_number'] = epis if epis < 2000 else None

        is_live, m3u8_url = False, None
        if video_type == 'now-on-air':
            is_live = True
            channel_url = 'https://api.abema.io/v1/channels'
            if video_id == 'news-global':
                channel_url = update_url_query(channel_url, {'division': '1'})
            onair_channels = self._download_json(channel_url, video_id)
            for ch in onair_channels['channels']:
                if video_id == ch['id']:
                    m3u8_url = ch['playback']['hls']
                    break
            else:
                raise ExtractorError(f'Cannot find on-air {video_id} channel.', expected=True)
        elif video_type == 'episode':
            api_response = self._download_json(
                f'https://api.abema.io/v1/video/programs/{video_id}', video_id,
                note='Checking playability',
                headers=headers)
            ondemand_types = traverse_obj(api_response, ('terms', ..., 'onDemandType'), default=[])
            if 3 not in ondemand_types:
                # --allow-unplayable-formats is a devil; we don't care about it
                raise ExtractorError("Premium stream is not supported", expected=True)

            m3u8_url = f'https://vod-abematv.akamaized.net/program/{video_id}/playlist.m3u8'
        elif video_type == 'slots':
            api_response = self._download_json(
                f'https://api.abema.io/v1/media/slots/{video_id}', video_id,
                note='Checking playability',
                headers=headers)
            if not traverse_obj(api_response, ('slot', 'flags', 'timeshiftFree'), default=False):
                raise ExtractorError("Premium stream is not supported", expected=True)

            m3u8_url = f'https://vod-abematv.akamaized.net/slot/{video_id}/playlist.m3u8'
        else:
            raise ExtractorError('Unreachable')

        if is_live:
            self.report_warning("This is a livestream; yt-dlp doesn't support downloading natively, but FFmpeg cannot handle m3u8 manifests from AbemaTV")
            self.report_warning('Please consider using Streamlink to download these streams (https://github.com/streamlink/streamlink)')
        formats = self._extract_m3u8_formats(
            m3u8_url, video_id, ext='mp4', live=is_live)

        info.update({
            'id': video_id,
            'title': title,
            'description': description,
            'formats': formats,
            'is_live': is_live,
        })
        return info


class AbemaTVTitleIE(AbemaTVBaseIE):
    _VALID_URL = r'https?://abema\.tv/video/title/(?P<id>[^?/]+)'

    _TESTS = [{
        'url': 'https://abema.tv/video/title/90-1597',
        'info_dict': {
            'id': '90-1597',
            'title': 'シャッフルアイランド',
        },
        'playlist_mincount': 2,
    }, {
        'url': 'https://abema.tv/video/title/193-132',
        'info_dict': {
            'id': '193-132',
            'title': '真心が届く~僕とスターのオフィス・ラブ!?~',
        },
        'playlist_mincount': 16,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        playlist_title, breadcrumb = None, self._extract_breadcrumb_list(webpage, video_id)
        if breadcrumb:
            playlist_title = breadcrumb[-1]

        playlist = []
        for mobj in re.finditer(r'<li\s*class=".+?EpisodeList.+?"><a\s*href="(/[^"]+?)"', webpage):
            playlist.append(self.url_result(urljoin('https://abema.tv/', mobj.group(1))))

        return self.playlist_result(playlist, playlist_title=playlist_title, playlist_id=video_id)
