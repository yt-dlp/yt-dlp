from .common import InfoExtractor
from ..utils import (
    int_or_none,
    traverse_obj,
)

from urllib.parse import parse_qs


class RedCDNLivxIE(InfoExtractor):
    _VALID_URL = r'https?://[^.]+\.dcs\.redcdn\.pl/[^/]+/o2/(?P<tenant>[^/]+)/(?P<id>[^/]+)/(?P<filename>[^./]+)\.livx\?(?P<qs>.+)'
    IE_NAME = 'redcdnlivx'

    _TESTS = [{
        'url': 'https://r.dcs.redcdn.pl/livedash/o2/senat/ENC02/channel.livx?indexMode=true&startTime=638272860000&stopTime=638292544000',
        'info_dict': {
            'id': 'ENC02-638272860000-638292544000',
            'ext': 'mp4',
            'title': 'ENC02',
            'duration': 19684,
        },
    }, {
        'url': 'https://r.dcs.redcdn.pl/livedash/o2/sejm/ENC18/live.livx?indexMode=true&startTime=722333096000&stopTime=722335562000',
        'info_dict': {
            'id': 'ENC18-722333096000-722335562000',
            'ext': 'mp4',
            'title': 'ENC18',
            'duration': 2466,
        },
    }]

    def _real_extract(self, url):
        tenant, camera, filename, qs = self._match_valid_url(url).group('tenant', 'id', 'filename', 'qs')
        qs = parse_qs(qs)
        start_time = int(traverse_obj(qs, ("startTime", 0)))
        stop_time = int_or_none(traverse_obj(qs, ("stopTime", 0)))

        def livx_mode(mode, suffix=''):
            file = f'https://r.dcs.redcdn.pl/{mode}/o2/{tenant}/{camera}/{filename}.livx{suffix}?startTime={start_time}'
            if stop_time:
                file += f'&stopTime={stop_time}'
            return file + '&indexMode=true'

        # no id for a transmission
        video_id = f'{camera}-{start_time}-{stop_time}'

        formats = [{
            'url': livx_mode('nvr'),
            'ext': 'flv',
            'format_id': 'direct-0',
            'preference': -1,   # VERY slow to download (~200 KiB/s, compared to ~10-15 MiB/s by DASH/HLS)
        }]
        formats.extend(self._extract_mpd_formats(livx_mode('livedash'), video_id, mpd_id='dash'))
        formats.extend(self._extract_m3u8_formats(
            livx_mode('livehls', '/playlist.m3u8'), video_id, m3u8_id='hls', ext='mp4'))
        formats.extend(self._extract_ism_formats(
            livx_mode('livess', '/manifest'), video_id, ism_id='ss'))

        self._sort_formats(formats)

        duration = (stop_time - start_time) // 1000

        return {
            'id': video_id,
            'title': camera,
            'formats': formats,
            'duration': duration,
            # if there's no stop, it's live
            'is_live': stop_time is None,
        }
