import datetime as dt
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    clean_html,
    join_nonempty,
    js_to_json,
    strip_or_none,
    try_get,
    update_url_query,
)


def is_dst(date):
    last_march = dt.datetime(date.year, 3, 31)
    last_october = dt.datetime(date.year, 10, 31)
    last_sunday_march = last_march - dt.timedelta(days=last_march.isoweekday() % 7)
    last_sunday_october = last_october - dt.timedelta(days=last_october.isoweekday() % 7)
    return last_sunday_march.replace(hour=2) <= date <= last_sunday_october.replace(hour=3)


def rfc3339_to_atende(date):
    date = dt.datetime.fromisoformat(date)
    date = date + dt.timedelta(hours=1 if is_dst(date) else 0)
    return int((date.timestamp() - 978307200) * 1000)


class SejmIE(InfoExtractor):
    _VALID_URL = (
        r'https?://(?:www\.)?sejm\.gov\.pl/[Ss]ejm(?P<term>\d+)\.nsf/transmisje(?:_arch)?\.xsp(?:\?[^#]*)?#(?P<id>[\dA-F]+)',
        r'https?://(?:www\.)?sejm\.gov\.pl/[Ss]ejm(?P<term>\d+)\.nsf/transmisje(?:_arch)?\.xsp\?(?:[^#]+&)?unid=(?P<id>[\dA-F]+)',
        r'https?://(?:(?:www\.)?sejm\.gov\.pl|sejm-embed\.redcdn\.pl)/[Ss]ejm(?P<term>\d+)\.nsf/VideoFrame\.xsp/(?P<id>[\dA-F]+)',
    )
    IE_NAME = 'sejm'

    _TESTS = [{
        # multiple cameras, polish SL iterpreter
        'url': 'https://www.sejm.gov.pl/Sejm10.nsf/transmisje_arch.xsp#6181EF1AD9CEEBB5C1258A6D006452B5',
        'info_dict': {
            'id': '6181EF1AD9CEEBB5C1258A6D006452B5',
            'title': '1. posiedzenie Sejmu X kadencji',
            'duration': 20145,
            'live_status': 'was_live',
            'location': 'Sala Posiedzeń',
        },
        'playlist': [{
            'info_dict': {
                'id': 'ENC01-6181EF1AD9CEEBB5C1258A6D006452B5-722340000000-722360145000',
                'ext': 'mp4',
                'duration': 20145,
                'title': '1. posiedzenie Sejmu X kadencji - ENC01',
                'live_status': 'was_live',
            },
        }, {
            'info_dict': {
                'id': 'ENC30-6181EF1AD9CEEBB5C1258A6D006452B5-722340000000-722360145000',
                'ext': 'mp4',
                'duration': 20145,
                'title': '1. posiedzenie Sejmu X kadencji - ENC30',
                'live_status': 'was_live',
            },
        }, {
            'info_dict': {
                'id': 'ENC31-6181EF1AD9CEEBB5C1258A6D006452B5-722340000000-722360145000',
                'ext': 'mp4',
                'duration': 20145,
                'title': '1. posiedzenie Sejmu X kadencji - ENC31',
                'live_status': 'was_live',
            },
        }, {
            'info_dict': {
                'id': 'ENC32-6181EF1AD9CEEBB5C1258A6D006452B5-722340000000-722360145000',
                'ext': 'mp4',
                'duration': 20145,
                'title': '1. posiedzenie Sejmu X kadencji - ENC32',
                'live_status': 'was_live',
            },
        }, {
            # sign lang interpreter
            'info_dict': {
                'id': 'Migacz-ENC01-6181EF1AD9CEEBB5C1258A6D006452B5-722340000000-722360145000',
                'ext': 'mp4',
                'duration': 20145,
                'title': '1. posiedzenie Sejmu X kadencji - Migacz-ENC01',
                'live_status': 'was_live',
            },
        }],
    }, {
        'url': 'https://www.sejm.gov.pl/Sejm8.nsf/transmisje.xsp?unid=9377A9D65518E9A5C125808E002E9FF2',
        'info_dict': {
            'id': '9377A9D65518E9A5C125808E002E9FF2',
            'title': 'Debata "Lepsza Polska: obywatelska"',
            'description': 'KP .Nowoczesna',
            'duration': 8770,
            'live_status': 'was_live',
            'location': 'sala kolumnowa im. Kazimierza Pużaka (bud. C-D)',
        },
        'playlist': [{
            'info_dict': {
                'id': 'ENC08-9377A9D65518E9A5C125808E002E9FF2-503831270000-503840040000',
                'ext': 'mp4',
                'duration': 8770,
                'title': 'Debata "Lepsza Polska: obywatelska" - ENC08',
                'live_status': 'was_live',
            },
        }],
    }, {
        # 7th term is very special, since it does not use redcdn livx
        'url': 'https://www.sejm.gov.pl/sejm7.nsf/transmisje_arch.xsp?rok=2015&month=11#A6E6D475ECCC6FE5C1257EF90034817F',
        'info_dict': {
            'id': 'A6E6D475ECCC6FE5C1257EF90034817F',
            'title': 'Konferencja prasowa - Stanowisko SLD ws. składu nowego rządu',
            'description': 'SLD - Biuro Prasowe Klubu',
            'duration': 514,
            'location': 'sala 101/bud. C',
            'live_status': 'was_live',
        },
        'playlist': [{
            'info_dict': {
                'id': 'A6E6D475ECCC6FE5C1257EF90034817F',
                'ext': 'mp4',
                'title': 'Konferencja prasowa - Stanowisko SLD ws. składu nowego rządu',
                'duration': 514,
            },
        }],
    }, {
        'url': 'https://sejm-embed.redcdn.pl/Sejm10.nsf/VideoFrame.xsp/FED58EABB97FBD53C1258A7400386492',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        # API (publicly documented) provides some metadata, and starting at 10th term, m3u8 URLs. Before then it's broken.
        # Frame provides timeframe and cameras available (including SLI; except for 7th term, where it provides a URL),
        # but is missing other necessary metadata (live_status, title).
        # Transmisje_arch JSON provides useful metadata (only place with live_status!), but not URLs/cameras.
        term, video_id = self._match_valid_url(url).group('term', 'id')
        frame = self._download_webpage(
            f'https://www.sejm.gov.pl/Sejm{term}.nsf/VideoFrame.xsp/{video_id}',
            video_id)
        player_config = self._search_json(r'var\splayerConfig\s*=\s*', frame, 'player config', video_id, transform_source=js_to_json)
        data = self._download_json(
            f'https://www.sejm.gov.pl/Sejm{term}.nsf/transmisje_arch.xsp/json/{video_id}',
            video_id)
        params = data['params']

        title = strip_or_none(data.get('title'))

        if data.get('status') == 'VIDEO_ENDED':
            live_status = 'was_live'
        elif data.get('status') == 'VIDEO_PLAYING':
            live_status = 'is_live'
        else:
            live_status = None
            self.report_warning(f'unknown status: {data.get("status")}')

        start_time = rfc3339_to_atende(params['start'])
        # current streams have a stop time of *expected* end of session, but actual times
        # can change during the transmission. setting a stop_time would artificially
        # end the stream at that time, while the session actually keeps going.
        if live_status == 'was_live':
            stop_time = rfc3339_to_atende(params['stop'])
            duration = (stop_time - start_time) // 1000
        else:
            stop_time, duration = None, None

        entries = []

        def add_entry(camera):
            if player_config.get('isMP4'):
                # Special case in 7th term. Instead of a camera name, this is a URL to a simple MP4 file.
                entries.append({
                    'url': self._proto_relative_url(camera),
                    'id': video_id,
                    'title': title,
                    'duration': duration,
                    'live_status': live_status,
                })
                return
            url = f'https://sejm.c.blueonline.tv/stream/{camera}/{video_id}/manifest.mpd?start={start_time}'
            if stop_time is not None:
                url = update_url_query(url, {'stop': stop_time})
            entries.append({
                '_type': 'url_transparent',
                'url': url,
                'ie_key': SejmBlueonlineIE.ie_key(),
                'id': camera,
                'duration': duration,
                'title': join_nonempty(title, camera, delim=' - '),
                'live_status': live_status,
            })

        for camera in player_config['cameras']:
            add_entry(camera)

        if params.get('mig'):
            add_entry(player_config['sli'])

        return {
            '_type': 'playlist',
            'entries': entries,
            'id': video_id,
            'title': title,
            'description': clean_html(data.get('desc')) or None,
            'duration': duration,
            'live_status': live_status,
            'location': strip_or_none(data.get('location')),
        }


class SejmBlueonlineIE(InfoExtractor):
    IE_DESC = False
    _VALID_URL = r'https?://sejm\.c\.blueonline\.tv//?stream/(?P<camera>[\dA-Za-z-]+)/(?P<id>[\dA-F]+)/(?:playlist.m3u8|manifest.mpd)\?'
    _TESTS = [{
        'url': 'https://sejm.c.blueonline.tv/stream/Migacz-ENC01/6181EF1AD9CEEBB5C1258A6D006452B5/manifest.mpd?start=722340000000&stop=722360145000',
        'info_dict': {
            'id': 'Migacz-ENC01-6181EF1AD9CEEBB5C1258A6D006452B5-722340000000-722360145000',
            'ext': 'mp4',
            'title': '_',
        },
    }]

    def _real_extract(self, url):
        camera, video_id = self._match_valid_url(url).group('camera', 'id')
        qs = urllib.parse.urlparse(url).query
        query = urllib.parse.parse_qs(qs)
        start_time = try_get(query, lambda q: q['start'][0])
        stop_time = try_get(query, lambda q: q['stop'][0])
        formats = []
        formats.extend(self._extract_m3u8_formats(f'https://sejm.c.blueonline.tv/stream/{camera}/{video_id}/playlist.m3u8?{qs}', video_id, live=stop_time is None))
        formats.extend(self._extract_mpd_formats(f'https://sejm.c.blueonline.tv/stream/{camera}/{video_id}/manifest.mpd?{qs}', video_id))
        return {
            'id': join_nonempty(camera, video_id, start_time, stop_time),
            'title': '_',
            'formats': formats,
        }
