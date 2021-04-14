from __future__ import unicode_literals

from ..compat import compat_str
from ..utils import (
    determine_protocol,
)


def _get_real_downloader(info_dict, protocol=None, *args, **kwargs):
    info_copy = info_dict.copy()
    if protocol:
        info_copy['protocol'] = protocol
    return get_suitable_downloader(info_copy, *args, **kwargs)


# Some of these require _get_real_downloader
from .common import FileDownloader
from .dash import DashSegmentsFD
from .f4m import F4mFD
from .hls import HlsFD
from .http import HttpFD
from .rtmp import RtmpFD
from .rtsp import RtspFD
from .ism import IsmFD
from .niconico import NiconicoDmcFD
from .youtube_live_chat import YoutubeLiveChatReplayFD
from .external import (
    get_external_downloader,
    FFmpegFD,
)

PROTOCOL_MAP = {
    'rtmp': RtmpFD,
    'm3u8_native': HlsFD,
    'm3u8': FFmpegFD,
    'mms': RtspFD,
    'rtsp': RtspFD,
    'f4m': F4mFD,
    'http_dash_segments': DashSegmentsFD,
    'ism': IsmFD,
    'niconico_dmc': NiconicoDmcFD,
    'youtube_live_chat_replay': YoutubeLiveChatReplayFD,
}


def shorten_protocol_name(proto, simplify=False):
    short_protocol_names = {
        'm3u8_native': 'm3u8_n',
        'http_dash_segments': 'dash',
        'niconico_dmc': 'dmc',
    }
    if simplify:
        short_protocol_names.update({
            'https': 'http',
            'ftps': 'ftp',
            'm3u8_native': 'm3u8',
            'm3u8_frag_urls': 'm3u8',
            'dash_frag_urls': 'dash',
        })
    return short_protocol_names.get(proto, proto)


def get_suitable_downloader(info_dict, params={}, default=HttpFD):
    """Get the downloader class that can handle the info dict."""
    protocol = determine_protocol(info_dict)
    info_dict['protocol'] = protocol

    # if (info_dict.get('start_time') or info_dict.get('end_time')) and not info_dict.get('requested_formats') and FFmpegFD.can_download(info_dict):
    #     return FFmpegFD

    downloaders = params.get('external_downloader')
    external_downloader = (
        downloaders if isinstance(downloaders, compat_str) or downloaders is None
        else downloaders.get(shorten_protocol_name(protocol, True), downloaders.get('default')))
    if external_downloader and external_downloader.lower() == 'native':
        external_downloader = 'native'

    if external_downloader not in (None, 'native'):
        ed = get_external_downloader(external_downloader)
        if ed.can_download(info_dict, external_downloader):
            return ed

    if protocol in ('m3u8', 'm3u8_native'):
        if info_dict.get('is_live'):
            return FFmpegFD
        elif external_downloader == 'native':
            return HlsFD
        elif _get_real_downloader(info_dict, 'm3u8_frag_urls', params, None):
            return HlsFD
        elif params.get('hls_prefer_native') is True:
            return HlsFD
        elif params.get('hls_prefer_native') is False:
            return FFmpegFD

    return PROTOCOL_MAP.get(protocol, default)


__all__ = [
    'FileDownloader',
    'get_suitable_downloader',
    'shorten_protocol_name',
]
