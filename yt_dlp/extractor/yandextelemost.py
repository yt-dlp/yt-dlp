
from .common import InfoExtractor
from ..utils import (
    js_to_json,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class YandexRuntimeStrmIE(InfoExtractor):
    _VALID_URL = r'https?://runtime\.strm\.yandex\.ru/player/[a-z]+/(?P<id>[a-z0-9]+)'
    _TESTS = [{
        'url': 'https://runtime.strm.yandex.ru/player/episode/vplege43k2rsf45ao43x',
        'info_dict': {
            'id': 'vplege43k2rsf45ao43x',
            'ext': 'mp4',
            'title': r're:^85a94a0aec3e473588a0b507021208b1-0 \d{4}-\d\d-\d\d \d\d:\d\d',
            'live_status': 'is_live',
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        content = self._search_json(
            r'window\.CloudVideo\.hydratePage\s*\(', webpage, 'playlist',
            video_id, transform_source=js_to_json)['firstItemData']['content']

        live_from_start = self.get_param('live_from_start', False)

        formats = []
        for stream in traverse_obj(content, ('streams', lambda _, v: url_or_none(v['url']))):
            s_url = stream['url']

            stream_type = stream.get('type')

            if stream_type == 'dash':
                dash_formats = self._extract_mpd_formats(
                    s_url, video_id, mpd_id='dash', fatal=False)
                formats.extend(dash_formats)

            if stream_type == 'hls':
                hls_formats = self._extract_m3u8_formats(
                    s_url, video_id, 'mp4', m3u8_id='hls', fatal=False, live=True)
                for f in hls_formats:
                    f['preference'] = -1
                    dl_opts = f.setdefault('downloader_options', {})
                    ffmpeg_args = dl_opts.get('ffmpeg_args', [])
                    if live_from_start:
                        ffmpeg_args.extend(['-live_start_index', '0'])

                    dl_opts['ffmpeg_args'] = ffmpeg_args

                    if live_from_start:
                        f['is_from_start'] = True

                formats.extend(hls_formats)

        return {
            'id': video_id,
            'formats': formats,
            **traverse_obj(content, {
                'title': ('title', {str}),
                'is_live': ('ugc_live', {bool}),
            }),
        }


class YandexTelemostIE(InfoExtractor):
    _VALID_URL = r'https?://telemost\.yandex\.ru/live/(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [{
        'url': 'https://telemost.yandex.ru/live/85a94a0aec3e473588a0b507021208b1',
        'info_dict': {
            'id': 'vplege43k2rsf45ao43x',
            'ext': 'mp4',
            # match any timestamp appended for live streams
            'title': r're:^Подготовка к аттестации по МО. День 8. Афанасьев О.Н. Афанасьев О.Н. Коптевская Г.Л. \d{4}-\d\d-\d\d \d\d:\d\d',
            'live_status': 'is_live',
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        preloaded_state = self._search_json(
            r'<script[^>]+id="preloaded-state"[^>]*>',
            webpage, 'preloaded_state', video_id)
        return {
            '_type': 'url_transparent',
            'ie_key': 'YandexRuntimeStrm',
            'id': video_id,
            **traverse_obj(preloaded_state, ('broadcastView', {
                'title': ('caption', {str}),
                'url': ('player_url', {url_or_none}),
            })),
        }
