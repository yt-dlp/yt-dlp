import datetime as dt
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    join_nonempty,
    parse_iso8601,
    strip_or_none,
    traverse_obj,
    try_get,
)


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
                'id': 'ENC01-6181EF1AD9CEEBB5C1258A6D006452B5-1700647200000-1700667345000',
                'ext': 'mp4',
                'duration': 20145,
                'title': '1. posiedzenie Sejmu X kadencji - ENC01',
                'live_status': 'was_live',
                'location': 'Sala Posiedzeń',
            },
        }, {
            'info_dict': {
                'id': 'ENC30-6181EF1AD9CEEBB5C1258A6D006452B5-1700647200000-1700667345000',
                'ext': 'mp4',
                'duration': 20145,
                'title': '1. posiedzenie Sejmu X kadencji - ENC30',
                'live_status': 'was_live',
                'location': 'Sala Posiedzeń',
            },
        }, {
            'info_dict': {
                'id': 'ENC31-6181EF1AD9CEEBB5C1258A6D006452B5-1700647200000-1700667345000',
                'ext': 'mp4',
                'duration': 20145,
                'title': '1. posiedzenie Sejmu X kadencji - ENC31',
                'live_status': 'was_live',
                'location': 'Sala Posiedzeń',
            },
        }, {
            'info_dict': {
                'id': 'ENC32-6181EF1AD9CEEBB5C1258A6D006452B5-1700647200000-1700667345000',
                'ext': 'mp4',
                'duration': 20145,
                'title': '1. posiedzenie Sejmu X kadencji - ENC32',
                'live_status': 'was_live',
                'location': 'Sala Posiedzeń',
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
                'id': 'ENC08-9377A9D65518E9A5C125808E002E9FF2-1482142070-1482150840',
                'ext': 'mp4',
                'duration': 8770,
                'title': 'Debata "Lepsza Polska: obywatelska" - ENC08',
                'description': 'KP .Nowoczesna',
                'live_status': 'was_live',
                'location': 'sala kolumnowa im. Kazimierza Pużaka (bud. C-D)',
            },
        }],
    }, {
        # 7th term is very special, since it does not use redcdn livx.
        'skip': 'API requests return HTTP 204',
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
        data = self._download_json(
            f'https://api.sejm.gov.pl/sejm/term{term}/videos/{video_id}',
            video_id)

        title = traverse_obj(data, ('title', {strip_or_none}))
        start_time = traverse_obj(data, ('startDateTime', {parse_iso8601}))
        # This is planned end for live transmissions
        end_time = traverse_obj(data, ('endDateTime', {parse_iso8601}))
        is_live = dt.datetime.now().timestamp() <= end_time
        duration = end_time - start_time

        info_dict = {
            **traverse_obj(data, {
                'description': ('description', {strip_or_none}),
                'location': ('room', {strip_or_none}),
                'categories': (..., 'type', {strip_or_none}),
            }),
            'live_status': 'is_live' if is_live else 'was_live',
            'duration': duration,
        }

        entries = []
        for manifest_url in (traverse_obj(data, 'videoLink'), *(traverse_obj(data, 'otherVideoLinks') or ())):
            # If it's Redge, no it's not.
            camera_id = self._search_regex(r'^https?://redir\.atmcdn\.pl/nvr/o2/sejm/([\w-]+)', manifest_url, 'redge camera id', default=None)
            if camera_id is not None:
                manifest_url = f'https://sejm.c.blueonline.tv/stream/{camera_id}/{video_id}/manifest.mpd?start={start_time}&stop={end_time}'
            else:
                camera_id = SejmBlueonlineIE._match_valid_url(manifest_url).group('camera')
            entries.append({
                **info_dict,
                '_type': 'url_transparent',
                'title': join_nonempty(title, camera_id, delim=' - '),
                'url': manifest_url,
                'ie_key': SejmBlueonlineIE.ie_key(),
            })

        return {
            **info_dict,
            '_type': 'playlist',
            'id': video_id,
            'title': title,
            'entries': entries,
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
