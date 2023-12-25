from .common import InfoExtractor
from .redge import RedCDNLivxIE
from ..utils import (
    clean_html,
    js_to_json,
    strip_or_none,
)

import datetime
from zoneinfo import ZoneInfo


class SejmIE(InfoExtractor):
    _VALID_URL = (
        r'https?://(?:www\.)?sejm\.gov\.pl/[Ss]ejm(?P<term>\d+)\.nsf/transmisje(?:_arch)?\.xsp(?:\?[^#]*)?#(?P<id>[\dA-F]+)',
        r'https?://(?:www\.)?sejm\.gov\.pl/[Ss]ejm(?P<term>\d+)\.nsf/transmisje(?:_arch)?\.xsp\?(?:[^#]+&)?unid=(?P<id>[\dA-F]+)',
        r'https?://sejm-embed\.redcdn\.pl/[Ss]ejm(?P<term>\d+)\.nsf/VideoFrame\.xsp/(?P<id>[\dA-F]+)',
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
                'id': 'ENC01-722340000000-722360145000',
                'ext': 'mp4',
                'duration': 20145,
                'title': '1. posiedzenie Sejmu X kadencji - ENC01',
                'live_status': 'was_live',
            },
        }, {
            'info_dict': {
                'id': 'ENC30-722340000000-722360145000',
                'ext': 'mp4',
                'duration': 20145,
                'title': '1. posiedzenie Sejmu X kadencji - ENC30',
                'live_status': 'was_live',
            },
        }, {
            'info_dict': {
                'id': 'ENC31-722340000000-722360145000',
                'ext': 'mp4',
                'duration': 20145,
                'title': '1. posiedzenie Sejmu X kadencji - ENC31',
                'live_status': 'was_live',
            },
        }, {
            'info_dict': {
                'id': 'ENC32-722340000000-722360145000',
                'ext': 'mp4',
                'duration': 20145,
                'title': '1. posiedzenie Sejmu X kadencji - ENC32',
                'live_status': 'was_live',
            },
        }, {
            # sign lang interpreter
            'info_dict': {
                'id': 'Migacz-ENC01-1-722340000000-722360145000',
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
                'id': 'ENC08-1-503831270000-503840040000',
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
        term, video_id = self._match_valid_url(url).group('term', 'id')
        frame = self._download_webpage(
            f'https://sejm-embed.redcdn.pl/Sejm{term}.nsf/VideoFrame.xsp/{video_id}',
            video_id)
        # despite it says "transmisje_arch", it works for live streams too!
        data = self._download_json(
            f'https://www.sejm.gov.pl/Sejm{term}.nsf/transmisje_arch.xsp/json/{video_id}',
            video_id)
        params = data['params']

        title = data['title'].strip()

        def rfc3339_to_atende(date):
            date = datetime.datetime.fromisoformat(date)
            # marks naive as CET/CEST
            date.replace(tzinfo=ZoneInfo('Europe/Warsaw'))
            # UTC timestamp with an offset
            return int((date.astimezone(datetime.timezone.utc).timestamp() - 978307200) * 1000)

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
        else:
            stop_time = None

        duration = (stop_time - start_time) // 1000 if stop_time else None

        entries = []

        def add_entry(file, legacy_file=False):
            if not file:
                return
            file = f'https:{file}'
            if not legacy_file:
                file += f'?startTime={start_time}'
                if stop_time is not None:
                    file += f'&stopTime={stop_time}'
                stream_id = self._search_regex(r'/o2/sejm/([^/]+)/[^./]+\.livx', file, 'stream id')
            common_info = {
                'url': file,
                'duration': duration,
            }
            if legacy_file:
                entries.append({
                    **common_info,
                    'id': video_id,
                    'title': title,
                })
            else:
                entries.append({
                    **common_info,
                    '_type': 'url_transparent',
                    'ie_key': RedCDNLivxIE.ie_key(),
                    'id': stream_id,
                    'title': f'{title} - {stream_id}',
                })

        cameras = self._search_json(
            r'var\s+cameras\s*=', frame, 'camera list', video_id,
            contains_pattern=r'\[(?s:.+)\]', transform_source=js_to_json,
            fatal=not self.get_param('ignore_no_formats_error')) or []
        for camera in cameras:
            camera_file = camera['file']
            if camera_file.get('flv'):
                add_entry(camera_file['flv'])
            elif camera_file.get('mp4'):
                # this is only a thing in 7th term. no streams before, and starting 8th it's redcdn livx
                add_entry(camera_file['mp4'], legacy_file=True)
            else:
                self.report_warning('Unknown camera stream type found')

        if params.get('mig'):
            add_entry(self._search_regex(r"var sliUrl\s*=\s*'([^']+)'", frame, 'sign language interpreter url', fatal=False))

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
