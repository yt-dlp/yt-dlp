
from .common import InfoExtractor
from ..utils import (
    js_to_json,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class YandexRuntimeStrmIE(InfoExtractor):
    _VALID_URL = r'https?://runtime\.strm\.yandex\.ru/player/[a-z]+/(?P<id>[a-z0-9]+)'
    _TESTS = [{
        'url': 'https://runtime.strm.yandex.ru/player/episode/vple3e7omvkythqefn4a',
        'info_dict': {
            'id': 'vple3e7omvkythqefn4a',
            'ext': 'mp4',
            # match any timestamp appended for live streams
            'title': r're:^ed3ab5fc53624ae19e4b65886bf4bb70.*',
            'live_status': 'is_live',
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        playlist = self._search_json(
            r'window\.CloudVideo\.hydratePage\s*\(',
            webpage, 'playlist', video_id, transform_source=js_to_json)
        content = traverse_obj(playlist, ('firstItemData', 'content'))

        formats = []
        streams = content.get('streams', [])
        for stream in streams:
            s_url = url_or_none(stream.get('url'))
            if not s_url:
                continue

            live_from_start = self.get_param('live_from_start', False)
            stream_type = stream.get('type')
            # dash is too complicated
            #
            # if stream_type == 'dash':
            #     dash_formats = self._extract_mpd_formats(
            #         s_url, video_id, mpd_id='dash', fatal=False)
            #     formats.extend(dash_formats)
            if stream_type == 'hls':
                hls_formats = self._extract_m3u8_formats(
                    s_url, video_id, 'mp4', m3u8_id='hls', fatal=False, live=True)
                if live_from_start:
                    for f in hls_formats:
                        f.setdefault('downloader_options', {}).update({'ffmpeg_args': ['-live_start_index', '0']})
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
        'url': 'https://telemost.yandex.ru/live/ed3ab5fc53624ae19e4b65886bf4bb70',
        'info_dict': {
            'id': 'vple3e7omvkythqefn4a',
            'ext': 'mp4',
            # match any timestamp appended for live streams
            'title': r're:^Подготовка к аттестации.*',
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
