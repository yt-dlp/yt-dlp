import re

from .common import InfoExtractor


class MuxIE(InfoExtractor):
    _VALID_URL = r'https?://(?:stream\.new/v|player\.mux\.com)/(?P<id>[A-Za-z0-9-]+)'
    _EMBED_REGEX = [r'<iframe\b[^>]+\bsrc=["\'](?P<url>(?:https?:)?//(?:stream\.new/v|player\.mux\.com)/(?P<id>[A-Za-z0-9-]+))']
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
    }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        yield from super()._extract_embed_urls(url, webpage)
        for playback_id in re.findall(r'<mux-player[^>]*\bplayback-id=["\'](?P<id>[A-Za-z0-9-]+)', webpage):
            yield f'https://player.mux.com/{playback_id}'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        formats = self._extract_m3u8_formats(
            f'https://stream.mux.com/{video_id}.m3u8', video_id, 'mp4')

        return {
            'id': video_id,
            'title': video_id,
            'formats': formats,
        }
