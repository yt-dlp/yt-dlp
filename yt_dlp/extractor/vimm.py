# coding: utf-8
from .common import InfoExtractor


class VimmIE(InfoExtractor):
    IE_NAME = 'Vimm:stream'
    _VALID_URL = r'https?://(?:www\.)?vimm\.tv/(?:c/)?(?P<id>[0-9a-z-]+)$'
    _TESTS = [{
        'url': 'https://www.vimm.tv/c/calimeatwagon',
        'info_dict': {
            'id': 'calimeatwagon',
            'ext': 'mp4',
            'title': 're:^calimeatwagon [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'live_status': 'is_live',
        },
        'skip': 'Live',
    }, {
        'url': 'https://www.vimm.tv/octaafradio',
        'only_matching': True,
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


class VimmRecordingIE(InfoExtractor):
    IE_NAME = 'Vimm:recording'
    _VALID_URL = r'https?://(?:www\.)?vimm\.tv/c/(?P<channel_id>[0-9a-z-]+)\?v=(?P<video_id>[0-9A-Za-z]+)'
    _TESTS = [{
        'url': 'https://www.vimm.tv/c/kaldewei?v=2JZsrPTFxsSz',
        'md5': '15122ee95baa32a548e4a3e120b598f1',
        'info_dict': {
            'id': '2JZsrPTFxsSz',
            'ext': 'mp4',
            'title': 'VIMM - [DE/GER] Kaldewei Live - In Farbe und Bunt',
            'uploader_id': 'kaldewei',
        },
    }]

    def _real_extract(self, url):
        channel_id, video_id = self._match_valid_url(url).groups()

        webpage = self._download_webpage(url, video_id)
        title = self._og_search_title(webpage)

        formats, subs = self._extract_m3u8_formats_and_subtitles(
            f'https://d211qfrkztakg3.cloudfront.net/{channel_id}/{video_id}/index.m3u8', video_id, 'mp4', m3u8_id='hls', live=False)
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'is_live': False,
            'uploader_id': channel_id,
            'formats': formats,
            'subtitles': subs,
        }
