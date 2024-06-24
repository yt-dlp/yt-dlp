import base64
import random
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    time_seconds,
    try_call,
    unified_timestamp,
    update_url_query,
)
from ..utils.traversal import traverse_obj


class RadikoBaseIE(InfoExtractor):
    _GEO_BYPASS = False
    _FULL_KEY = None
    _HOSTS_FOR_TIME_FREE_FFMPEG_UNSUPPORTED = (
        'https://c-rpaa.smartstream.ne.jp',
        'https://si-c-radiko.smartstream.ne.jp',
        'https://tf-f-rpaa-radiko.smartstream.ne.jp',
        'https://tf-c-rpaa-radiko.smartstream.ne.jp',
        'https://si-f-radiko.smartstream.ne.jp',
        'https://rpaa.smartstream.ne.jp',
    )
    _HOSTS_FOR_TIME_FREE_FFMPEG_SUPPORTED = (
        'https://rd-wowza-radiko.radiko-cf.com',
        'https://radiko.jp',
        'https://f-radiko.smartstream.ne.jp',
    )
    # Following URL forcibly connects not Time Free but Live
    _HOSTS_FOR_LIVE = (
        'https://c-radiko.smartstream.ne.jp',
    )

    def _negotiate_token(self):
        _, auth1_handle = self._download_webpage_handle(
            'https://radiko.jp/v2/api/auth1', None, 'Downloading authentication page',
            headers={
                'x-radiko-app': 'pc_html5',
                'x-radiko-app-version': '0.0.1',
                'x-radiko-device': 'pc',
                'x-radiko-user': 'dummy_user',
            })
        auth1_header = auth1_handle.headers

        auth_token = auth1_header['X-Radiko-AuthToken']
        kl = int(auth1_header['X-Radiko-KeyLength'])
        ko = int(auth1_header['X-Radiko-KeyOffset'])
        raw_partial_key = self._extract_full_key()[ko:ko + kl]
        partial_key = base64.b64encode(raw_partial_key).decode()

        area_id = self._download_webpage(
            'https://radiko.jp/v2/api/auth2', None, 'Authenticating',
            headers={
                'x-radiko-device': 'pc',
                'x-radiko-user': 'dummy_user',
                'x-radiko-authtoken': auth_token,
                'x-radiko-partialkey': partial_key,
            }).split(',')[0]

        if area_id == 'OUT':
            self.raise_geo_restricted(countries=['JP'])

        auth_data = (auth_token, area_id)
        self.cache.store('radiko', 'auth_data', auth_data)
        return auth_data

    def _auth_client(self):
        cachedata = self.cache.load('radiko', 'auth_data')
        if cachedata is not None:
            response = self._download_webpage(
                'https://radiko.jp/v2/api/auth_check', None, 'Checking cached token', expected_status=401,
                headers={'X-Radiko-AuthToken': cachedata[0], 'X-Radiko-AreaId': cachedata[1]})
            if response == 'OK':
                return cachedata
        return self._negotiate_token()

    def _extract_full_key(self):
        if self._FULL_KEY:
            return self._FULL_KEY

        jscode = self._download_webpage(
            'https://radiko.jp/apps/js/playerCommon.js', None,
            note='Downloading player js code')
        full_key = self._search_regex(
            (r"RadikoJSPlayer\([^,]*,\s*(['\"])pc_html5\1,\s*(['\"])(?P<fullkey>[0-9a-f]+)\2,\s*{"),
            jscode, 'full key', fatal=False, group='fullkey')

        if full_key:
            full_key = full_key.encode()
        else:  # use only full key ever known
            full_key = b'bcd151073c03b352e1ef2fd66c32209da9ca0afa'

        self._FULL_KEY = full_key
        return full_key

    def _find_program(self, video_id, station, cursor):
        station_program = self._download_xml(
            f'https://radiko.jp/v3/program/station/weekly/{station}.xml', video_id,
            note=f'Downloading radio program for {station} station')

        prog = None
        for p in station_program.findall('.//prog'):
            ft_str, to_str = p.attrib['ft'], p.attrib['to']
            ft = unified_timestamp(ft_str, False)
            to = unified_timestamp(to_str, False)
            if ft <= cursor and cursor < to:
                prog = p
                break
        if not prog:
            raise ExtractorError('Cannot identify radio program to download!')
        assert ft, to
        return prog, station_program, ft, ft_str, to_str

    def _extract_formats(self, video_id, station, is_onair, ft, cursor, auth_token, area_id, query):
        m3u8_playlist_data = self._download_xml(
            f'https://radiko.jp/v3/station/stream/pc_html5/{station}.xml', video_id,
            note='Downloading stream information')

        formats = []
        found = set()

        timefree_int = 0 if is_onair else 1

        for element in m3u8_playlist_data.findall(f'.//url[@timefree="{timefree_int}"]/playlist_create_url'):
            pcu = element.text
            if pcu in found:
                continue
            found.add(pcu)
            playlist_url = update_url_query(pcu, {
                'station_id': station,
                **query,
                'l': '15',
                'lsid': ''.join(random.choices('0123456789abcdef', k=32)),
                'type': 'b',
            })

            time_to_skip = None if is_onair else cursor - ft

            domain = urllib.parse.urlparse(playlist_url).netloc
            subformats = self._extract_m3u8_formats(
                playlist_url, video_id, ext='m4a',
                live=True, fatal=False, m3u8_id=domain,
                note=f'Downloading m3u8 information from {domain}',
                headers={
                    'X-Radiko-AreaId': area_id,
                    'X-Radiko-AuthToken': auth_token,
                })
            for sf in subformats:
                if (is_onair ^ pcu.startswith(self._HOSTS_FOR_LIVE)) or (
                        not is_onair and pcu.startswith(self._HOSTS_FOR_TIME_FREE_FFMPEG_UNSUPPORTED)):
                    sf['preference'] = -100
                    sf['format_note'] = 'not preferred'
                if not is_onair and timefree_int == 1 and time_to_skip:
                    sf['downloader_options'] = {'ffmpeg_args': ['-ss', str(time_to_skip)]}
            formats.extend(subformats)

        return formats

    def _extract_performers(self, prog):
        return traverse_obj(prog, (
            'pfm/text()', ..., {lambda x: re.split(r'[/／、　,，]', x)}, ..., {str.strip})) or None


class RadikoIE(RadikoBaseIE):
    _VALID_URL = r'https?://(?:www\.)?radiko\.jp/#!/ts/(?P<station>[A-Z0-9-]+)/(?P<id>\d+)'

    _TESTS = [{
        # QRR (文化放送) station provides <desc>
        'url': 'https://radiko.jp/#!/ts/QRR/20210425101300',
        'only_matching': True,
    }, {
        # FMT (TOKYO FM) station does not provide <desc>
        'url': 'https://radiko.jp/#!/ts/FMT/20210810150000',
        'only_matching': True,
    }, {
        'url': 'https://radiko.jp/#!/ts/JOAK-FM/20210509090000',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        station, video_id = self._match_valid_url(url).groups()
        vid_int = unified_timestamp(video_id, False)
        prog, station_program, ft, radio_begin, radio_end = self._find_program(video_id, station, vid_int)

        auth_token, area_id = self._auth_client()

        return {
            'id': video_id,
            'title': try_call(lambda: prog.find('title').text),
            'cast': self._extract_performers(prog),
            'description': clean_html(try_call(lambda: prog.find('info').text)),
            'uploader': try_call(lambda: station_program.find('.//name').text),
            'uploader_id': station,
            'timestamp': vid_int,
            'duration': try_call(lambda: unified_timestamp(radio_end, False) - unified_timestamp(radio_begin, False)),
            'is_live': True,
            'formats': self._extract_formats(
                video_id=video_id, station=station, is_onair=False,
                ft=ft, cursor=vid_int, auth_token=auth_token, area_id=area_id,
                query={
                    'start_at': radio_begin,
                    'ft': radio_begin,
                    'end_at': radio_end,
                    'to': radio_end,
                    'seek': video_id,
                },
            ),
        }


class RadikoRadioIE(RadikoBaseIE):
    _VALID_URL = r'https?://(?:www\.)?radiko\.jp/#!/live/(?P<id>[A-Z0-9-]+)'

    _TESTS = [{
        # QRR (文化放送) station provides <desc>
        'url': 'https://radiko.jp/#!/live/QRR',
        'only_matching': True,
    }, {
        # FMT (TOKYO FM) station does not provide <desc>
        'url': 'https://radiko.jp/#!/live/FMT',
        'only_matching': True,
    }, {
        'url': 'https://radiko.jp/#!/live/JOAK-FM',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        station = self._match_id(url)
        self.report_warning('Downloader will not stop at the end of the program! Press Ctrl+C to stop')

        auth_token, area_id = self._auth_client()
        # get current time in JST (GMT+9:00 w/o DST)
        vid_now = time_seconds(hours=9)

        prog, station_program, ft, _, _ = self._find_program(station, station, vid_now)

        title = prog.find('title').text
        description = clean_html(prog.find('info').text)
        station_name = station_program.find('.//name').text

        formats = self._extract_formats(
            video_id=station, station=station, is_onair=True,
            ft=ft, cursor=vid_now, auth_token=auth_token, area_id=area_id,
            query={})

        return {
            'id': station,
            'title': title,
            'cast': self._extract_performers(prog),
            'description': description,
            'uploader': station_name,
            'uploader_id': station,
            'timestamp': ft,
            'formats': formats,
            'is_live': True,
        }
