from .common import InfoExtractor
from .redge import RedCDNLivxIE
from ..utils import (
    clean_html,
    js_to_json,
    strip_or_none,
    traverse_obj,
)

import datetime


class SejmIE(InfoExtractor):
    _VALID_URL = (
        r'https?://(?:www\.)?sejm\.gov\.pl/Sejm(?P<term>\d+)\.nsf/transmisje(?:_arch)?\.xsp(?:\?[^#]*)?#(?P<id>[\dA-F]+)',
        r'https?://(?:www\.)?sejm\.gov\.pl/Sejm(?P<term>\d+)\.nsf/transmisje(?:_arch)?\.xsp\?(?:[^#]+&)?unid=(?P<id>[\dA-F]+)',
        r'https?://sejm-embed\.redcdn\.pl/Sejm(?P<term>\d+)\.nsf/VideoFrame\.xsp/(?P<id>[\dA-F]+)',
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
        'playlist_count': 5,
    }, {
        'url': 'https://www.sejm.gov.pl/Sejm10.nsf/transmisje.xsp?unid=7797B441DF1ACC35C1258A75002EB583',
        'info_dict': {
            'id': '7797B441DF1ACC35C1258A75002EB583',
            'title': 'Konferencja prasowa marszałka Sejmu Szymona Hołowni',
            'duration': 1972,
            'live_status': 'was_live',
            'location': 'hall przed Salą Kolumnową, bud. C',
        },
        'playlist_count': 1,
    }, {
        'url': 'https://sejm-embed.redcdn.pl/Sejm10.nsf/VideoFrame.xsp/FED58EABB97FBD53C1258A7400386492',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        term, video_id = self._match_valid_url(url).group('term', 'id')
        frame = self._download_webpage(
            f'https://sejm-embed.redcdn.pl/Sejm{term}.nsf/VideoFrame.xsp/{video_id}',
            video_id, headers={
                'Referer': f'https://www.sejm.gov.pl/Sejm{term}.nsf/transmisje_arch.xsp',
            })
        # despite it says "transmisje_arch", it works for live streams too!
        data = self._download_json(
            f'https://www.sejm.gov.pl/Sejm{term}.nsf/transmisje_arch.xsp/json/{video_id}',
            video_id, headers={
                'Referer': f'https://www.sejm.gov.pl/Sejm{term}.nsf/transmisje_arch.xsp',
            })
        params = data['params']

        def rfc3339_to_atende(date):
            date = datetime.datetime.fromisoformat(date)
            # atende uses timestamp but since 2001 instead of 1970
            date = date.replace(year=date.year - 31)
            # also it's in milliseconds
            return int(date.timestamp() * 1000)

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

        def add_entry(file):
            if not file:
                return
            file = f'https:{file}?startTime={start_time}'
            if stop_time is not None:
                file += f'&stopTime={stop_time}'
            stream_id = self._search_regex(r'/o2/sejm/([^/]+)/[^./]+\.livx', file, 'stream id')
            entries.append({
                '_type': 'url_transparent',
                'url': file,
                'ie_key': RedCDNLivxIE.ie_key(),
                'id': stream_id,
                'title': stream_id,
                'duration': duration,
            })

        cameras = self._parse_json(
            self._search_regex(r'(?s)var cameras = (\[.+?\]);', frame, 'camera list'),
            video_id, js_to_json)
        for camera in cameras:
            add_entry(traverse_obj(camera, ('file', 'flv')))

        if params.get('mig'):
            add_entry(self._search_regex(r"var sliUrl\s*=\s*'([^']+)'", frame, 'sign language interpreter url', fatal=False))

        return {
            '_type': 'multi_video',
            'entries': entries,
            'id': video_id,
            'title': data['title'].strip(),
            'description': clean_html(data.get('desc')) or None,
            'duration': duration,
            'live_status': live_status,
            'location': strip_or_none(data.get('location')),
        }
