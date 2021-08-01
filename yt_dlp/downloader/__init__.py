from __future__ import unicode_literals

from ..compat import compat_str
from ..utils import (
    determine_protocol,
    NO_DEFAULT
)


def get_suitable_downloader(info_dict, params={}, default=NO_DEFAULT, protocol=None, to_stdout=False):
    info_dict['protocol'] = determine_protocol(info_dict)
    info_copy = info_dict.copy()
    if protocol:
        info_copy['protocol'] = protocol
    info_copy['to_stdout'] = to_stdout
    return _get_suitable_downloader(info_copy, params, default)


# Some of these require get_suitable_downloader
from .common import FileDownloader
from .dash import DashSegmentsFD
from .f4m import F4mFD
from .hls import HlsFD
from .http import HttpFD
from .rtmp import RtmpFD
from .rtsp import RtspFD
from .ism import IsmFD
from .mhtml import MhtmlFD
from .niconico import NiconicoDmcFD
from .websocket import WebSocketFragmentFD
from .youtube_live_chat import YoutubeLiveChatFD
from .external import (
    get_external_downloader,
    FFmpegFD,
)

PROTOCOL_MAP = {
    'rtmp': RtmpFD,
    'rtmp_ffmpeg': FFmpegFD,
    'm3u8_native': HlsFD,
    'm3u8': FFmpegFD,
    'mms': RtspFD,
    'rtsp': RtspFD,
    'f4m': F4mFD,
    'http_dash_segments': DashSegmentsFD,
    'ism': IsmFD,
    'mhtml': MhtmlFD,
    'niconico_dmc': NiconicoDmcFD,
    'websocket_frag': WebSocketFragmentFD,
    'youtube_live_chat': YoutubeLiveChatFD,
    'youtube_live_chat_replay': YoutubeLiveChatFD,
}


def shorten_protocol_name(proto, simplify=False):
    short_protocol_names = {
        'm3u8_native': 'm3u8_n',
        'rtmp_ffmpeg': 'rtmp_f',
        'http_dash_segments': 'dash',
        'niconico_dmc': 'dmc',
        'websocket_frag': 'WSfrag',
    }
    if simplify:
        short_protocol_names.update({
            'https': 'http',
            'ftps': 'ftp',
            'm3u8_native': 'm3u8',
            'rtmp_ffmpeg': 'rtmp',
            'm3u8_frag_urls': 'm3u8',
            'dash_frag_urls': 'dash',
        })
    return short_protocol_names.get(proto, proto)


def _get_suitable_downloader(info_dict, params, default):
    """Get the downloader class that can handle the info dict."""
    if default is NO_DEFAULT:
        default = HttpFD

    # if (info_dict.get('start_time') or info_dict.get('end_time')) and not info_dict.get('requested_formats') and FFmpegFD.can_download(info_dict):
    #     return FFmpegFD

    protocol = info_dict['protocol']
    downloaders = params.get('external_downloader')
    external_downloader = (
        downloaders if isinstance(downloaders, compat_str) or downloaders is None
        else downloaders.get(shorten_protocol_name(protocol, True), downloaders.get('default')))

    if external_downloader is None:
        if info_dict['to_stdout'] and FFmpegFD.can_merge_formats(info_dict, params):
            return FFmpegFD
    elif external_downloader.lower() != 'native':
        ed = get_external_downloader(external_downloader)
        if ed.can_download(info_dict, external_downloader):
            return ed

    if protocol in ('m3u8', 'm3u8_native'):
        if info_dict.get('is_live'):
            return FFmpegFD
        elif (external_downloader or '').lower() == 'native':
            return HlsFD
        elif get_suitable_downloader(
                info_dict, params, None, protocol='m3u8_frag_urls', to_stdout=info_dict['to_stdout']):
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
