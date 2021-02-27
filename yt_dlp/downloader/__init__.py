from __future__ import unicode_literals

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


def get_suitable_downloader(info_dict, params={}, default=HttpFD):
    """Get the downloader class that can handle the info dict."""
    protocol = determine_protocol(info_dict)
    info_dict['protocol'] = protocol

    # if (info_dict.get('start_time') or info_dict.get('end_time')) and not info_dict.get('requested_formats') and FFmpegFD.can_download(info_dict):
    #     return FFmpegFD

    external_downloader = params.get('external_downloader')
    if external_downloader is not None:
        ed = get_external_downloader(external_downloader)
        if ed.can_download(info_dict, external_downloader):
            return ed

    if protocol.startswith('m3u8'):
        if info_dict.get('is_live'):
            return FFmpegFD
        elif _get_real_downloader(info_dict, 'frag_urls', params, None):
            return HlsFD
        elif params.get('hls_prefer_native') is True:
            return HlsFD
        elif params.get('hls_prefer_native') is False:
            return FFmpegFD

    return PROTOCOL_MAP.get(protocol, default)


__all__ = [
    'get_suitable_downloader',
    'FileDownloader',
]
