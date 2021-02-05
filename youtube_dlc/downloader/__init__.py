from __future__ import unicode_literals

from .common import FileDownloader
from .f4m import F4mFD
from .hls import HlsFD
from .http import HttpFD
from .rtmp import RtmpFD
from .dash import DashSegmentsFD
from .rtsp import RtspFD
from .ism import IsmFD
from .youtube_live_chat import YoutubeLiveChatReplayFD
from .niconico import (
    NiconicoDmcHttpFD,
    NiconicoDmcHlsFD
)
from .external import (
    get_external_downloader,
    FFmpegFD,
)

from ..utils import (
    determine_protocol,
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
    'youtube_live_chat_replay': YoutubeLiveChatReplayFD,
    'niconico_dmc_http': NiconicoDmcHttpFD,
    'niconico_dmc_hls': NiconicoDmcHlsFD,
}


def get_suitable_downloader(info_dict, params={}):
    """Get the downloader class that can handle the info dict."""
    protocol = determine_protocol(info_dict)
    info_dict['protocol'] = protocol

    # if (info_dict.get('start_time') or info_dict.get('end_time')) and not info_dict.get('requested_formats') and FFmpegFD.can_download(info_dict):
    #     return FFmpegFD

    external_downloader = params.get('external_downloader')
    if external_downloader is not None:
        ed = get_external_downloader(external_downloader)
        if ed.can_download(info_dict):
            return ed

    if protocol.startswith('m3u8') and info_dict.get('is_live'):
        return FFmpegFD

    if protocol == 'm3u8' and params.get('hls_prefer_native') is True:
        return HlsFD

    if protocol == 'm3u8_native' and params.get('hls_prefer_native') is False:
        return FFmpegFD

    return PROTOCOL_MAP.get(protocol, HttpFD)


__all__ = [
    'get_suitable_downloader',
    'FileDownloader',
]
