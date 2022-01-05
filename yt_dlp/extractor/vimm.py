# coding: utf-8
from .common import InfoExtractor


class VimmIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?vimm\.tv/c/(?P<id>[0-9a-z-]+)'
    _TESTS = [{
        'url': 'https://www.vimm.tv/c/calimeatwagon',
        'info_dict': {
            'id': 'calimeatwagon',
            'ext': 'mp4',
            'title': 're:^calimeatwagon [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'live_status': 'is_live',
        },
        'skip': 'Live',
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)

        formats, subs = self._extract_m3u8_formats_and_subtitles(
            f'https://www.vimm.tv/hls/{channel_id}.m3u8', channel_id, 'mp4', m3u8_id='hls', live=True)
        self._sort_formats(formats)

        return {
            'id': channel_id,
            'title': channel_id,
            'is_live': True,
            'formats': formats,
            'subtitles': subs,
        }
