from ..utils import NO_DEFAULT, determine_protocol


def get_suitable_downloader(info_dict, params={}, default=NO_DEFAULT, protocol=None, to_stdout=False):
    info_dict['protocol'] = determine_protocol(info_dict)
    info_copy = info_dict.copy()
    info_copy['to_stdout'] = to_stdout

    protocols = (protocol or info_copy['protocol']).split('+')
    downloaders = [_get_suitable_downloader(info_copy, proto, params, default) for proto in protocols]

    if set(downloaders) == {FFmpegFD} and FFmpegFD.can_merge_formats(info_copy, params):
        return FFmpegFD
    elif (set(downloaders) == {DashSegmentsFD}
          and not (to_stdout and len(protocols) > 1)
          and set(protocols) == {'http_dash_segments_generator'}):
        return DashSegmentsFD
    elif len(downloaders) == 1:
        return downloaders[0]
    return None


# Some of these require get_suitable_downloader
from .common import FileDownloader
from .dash import DashSegmentsFD
from .external import FFmpegFD, get_external_downloader
from .f4m import F4mFD
from .fc2 import FC2LiveFD
from .hls import HlsFD
from .http import HttpFD
from .ism import IsmFD
from .mhtml import MhtmlFD
from .niconico import NiconicoDmcFD, NiconicoLiveFD
from .rtmp import RtmpFD
from .rtsp import RtspFD
from .websocket import WebSocketFragmentFD
from .youtube_live_chat import YoutubeLiveChatFD
from .bunnycdn import BunnyCdnFD

PROTOCOL_MAP = {
    'rtmp': RtmpFD,
    'rtmpe': RtmpFD,
    'rtmp_ffmpeg': FFmpegFD,
    'm3u8_native': HlsFD,
    'm3u8': FFmpegFD,
    'mms': RtspFD,
    'rtsp': RtspFD,
    'f4m': F4mFD,
    'http_dash_segments': DashSegmentsFD,
    'http_dash_segments_generator': DashSegmentsFD,
    'ism': IsmFD,
    'mhtml': MhtmlFD,
    'niconico_dmc': NiconicoDmcFD,
    'niconico_live': NiconicoLiveFD,
    'fc2_live': FC2LiveFD,
    'websocket_frag': WebSocketFragmentFD,
    'youtube_live_chat': YoutubeLiveChatFD,
    'youtube_live_chat_replay': YoutubeLiveChatFD,
    'bunnycdn': BunnyCdnFD,
}


def shorten_protocol_name(proto, simplify=False):
    short_protocol_names = {
        'm3u8_native': 'm3u8',
        'm3u8': 'm3u8F',
        'rtmp_ffmpeg': 'rtmpF',
        'http_dash_segments': 'dash',
        'http_dash_segments_generator': 'dashG',
        'niconico_dmc': 'dmc',
        'websocket_frag': 'WSfrag',
    }
    if simplify:
        short_protocol_names.update({
            'https': 'http',
            'ftps': 'ftp',
            'm3u8': 'm3u8',  # Reverse above m3u8 mapping
            'm3u8_native': 'm3u8',
            'http_dash_segments_generator': 'dash',
            'rtmp_ffmpeg': 'rtmp',
            'm3u8_frag_urls': 'm3u8',
            'dash_frag_urls': 'dash',
        })
    return short_protocol_names.get(proto, proto)


def _get_suitable_downloader(info_dict, protocol, params, default):
    """Get the downloader class that can handle the info dict."""
    if default is NO_DEFAULT:
        default = HttpFD

    if (info_dict.get('section_start') or info_dict.get('section_end')) and FFmpegFD.can_download(info_dict):
        return FFmpegFD

    info_dict['protocol'] = protocol
    downloaders = params.get('external_downloader')
    external_downloader = (
        downloaders if isinstance(downloaders, str) or downloaders is None
        else downloaders.get(shorten_protocol_name(protocol, True), downloaders.get('default')))

    if external_downloader is None:
        if info_dict['to_stdout'] and FFmpegFD.can_merge_formats(info_dict, params):
            return FFmpegFD
    elif external_downloader.lower() != 'native':
        ed = get_external_downloader(external_downloader)
        if ed.can_download(info_dict, external_downloader):
            return ed

    if protocol == 'http_dash_segments':
        if info_dict.get('is_live') and (external_downloader or '').lower() != 'native':
            return FFmpegFD

    if protocol in ('m3u8', 'm3u8_native'):
        if info_dict.get('is_live'):
            return FFmpegFD
        elif (external_downloader or '').lower() == 'native':
            return HlsFD
        elif protocol == 'm3u8_native' and get_suitable_downloader(
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
