import re

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    filter_dict,
    parse_qs,
    smuggle_url,
    unsmuggle_url,
    update_url_query,
)
from ..utils.traversal import traverse_obj


class MuxIE(InfoExtractor):
    _VALID_URL = r'https?://(?:stream\.new/v|player\.mux\.com)/(?P<id>[A-Za-z0-9-]+)'
    _EMBED_REGEX = [r'<iframe\b[^>]+\bsrc=["\'](?P<url>(?:https?:)?//(?:stream\.new/v|player\.mux\.com)/(?P<id>[A-Za-z0-9-]+)[^"\']+)']
    _TESTS = [{
        'url': 'https://stream.new/v/OCtRWZiZqKvLbnZ32WSEYiGNvHdAmB01j/embed',
        'info_dict': {
            'ext': 'mp4',
            'id': 'OCtRWZiZqKvLbnZ32WSEYiGNvHdAmB01j',
            'title': 'OCtRWZiZqKvLbnZ32WSEYiGNvHdAmB01j',
        },
    }, {
        'url': 'https://player.mux.com/OCtRWZiZqKvLbnZ32WSEYiGNvHdAmB01j',
        'info_dict': {
            'ext': 'mp4',
            'id': 'OCtRWZiZqKvLbnZ32WSEYiGNvHdAmB01j',
            'title': 'OCtRWZiZqKvLbnZ32WSEYiGNvHdAmB01j',
        },
    }]
    _WEBPAGE_TESTS = [{
        # iframe embed
        'url': 'https://www.redbrickai.com/blog/2025-07-14-FAST-brush',
        'info_dict': {
            'ext': 'mp4',
            'id': 'cXhzAiW1AmsHY01eRbEYFcTEAn0102aGN8sbt8JprP6Dfw',
            'title': 'cXhzAiW1AmsHY01eRbEYFcTEAn0102aGN8sbt8JprP6Dfw',
        },
    }, {
        # mux-player embed
        'url': 'https://muxvideo.2coders.com/download/',
        'info_dict': {
            'ext': 'mp4',
            'id': 'JBuasdg35Hw7tYmTe9k68QLPQKixL300YsWHDz5Flit8',
            'title': 'JBuasdg35Hw7tYmTe9k68QLPQKixL300YsWHDz5Flit8',
        },
    }, {
        # mux-player with title metadata
        'url': 'https://datastar-todomvc.cross.stream/',
        'info_dict': {
            'ext': 'mp4',
            'id': 'KX01ZSZ8CXv5SVfVwMZKJTcuBcUQmo1ReS9U5JjoHm4k',
            'title': 'TodoMVC with Datastar Tutorial',
        },
    }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        yield from super()._extract_embed_urls(url, webpage)
        for mux_player in re.findall(r'<mux-(?:player|video)\b[^>]*\bplayback-id=[^>]+>', webpage):
            attrs = extract_attributes(mux_player)
            playback_id = attrs.get('playback-id')
            if not playback_id:
                continue
            token = attrs.get('playback-token') or traverse_obj(playback_id, ({parse_qs}, 'token', -1))
            playback_id = playback_id.partition('?')[0]

            embed_url = update_url_query(
                f'https://player.mux.com/{playback_id}',
                filter_dict({'playback-token': token}))
            if title := attrs.get('metadata-video-title'):
                embed_url = smuggle_url(embed_url, {'title': title})
            yield embed_url

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        video_id = self._match_id(url)

        token = traverse_obj(parse_qs(url), ('playback-token', -1))

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            f'https://stream.mux.com/{video_id}.m3u8', video_id, 'mp4',
            query=filter_dict({'token': token}))

        return {
            'id': video_id,
            'title': smuggled_data.get('title') or video_id,
            'formats': formats,
            'subtitles': subtitles,
        }
