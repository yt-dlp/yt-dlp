import re

from .common import InfoExtractor
from ..utils import traverse_obj, urljoin


class IslamChannelIE(InfoExtractor):
    _VALID_URL = r'https?://watch\.islamchannel\.tv/watch/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://watch.islamchannel.tv/watch/38604310',
        'info_dict': {
            'id': '38604310',
            'title': 'Omar - Young Omar',
            'description': 'md5:5cc7ddecef064ea7afe52eb5e0e33b55',
            'thumbnail': r're:https?://.+',
            'ext': 'mp4',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        thumbnail = self._search_regex(
            r'data-poster="([^"]+)"', webpage, 'data poster', fatal=False) or \
            self._html_search_meta(('og:image', 'twitter:image'), webpage)

        headers = {
            'Token': self._search_regex(r'data-token="([^"]+)"', webpage, 'data token'),
            'Token-Expiry': self._search_regex(r'data-expiry="([^"]+)"', webpage, 'data expiry'),
            'Uvid': video_id,
        }
        show_stream = self._download_json(
            f'https://v2-streams-elb.simplestreamcdn.com/api/show/stream/{video_id}', video_id,
            query={
                'key': self._search_regex(r'data-key="([^"]+)"', webpage, 'data key'),
                'platform': 'chrome',
            }, headers=headers)
        # TODO: show_stream['stream'] and show_stream['drm'] may contain something interesting
        streams = self._download_json(
            traverse_obj(show_stream, ('response', 'tokenization', 'url')), video_id,
            headers=headers)
        formats, subs = self._extract_m3u8_formats_and_subtitles(traverse_obj(streams, ('Streams', 'Adaptive')), video_id, 'mp4')

        return {
            'id': video_id,
            'title': self._html_search_meta(('og:title', 'twitter:title'), webpage),
            'description': self._html_search_meta(('og:description', 'twitter:description', 'description'), webpage),
            'formats': formats,
            'subtitles': subs,
            'thumbnails': [{
                'id': 'unscaled',
                'url': thumbnail.split('?')[0],
                'ext': 'jpg',
                'preference': 2,
            }, {
                'id': 'orig',
                'url': thumbnail,
                'ext': 'jpg',
                'preference': 1,
            }] if thumbnail else None,
        }


class IslamChannelSeriesIE(InfoExtractor):
    _VALID_URL = r'https?://watch\.islamchannel\.tv/series/(?P<id>[a-f\d-]+)'
    _TESTS = [{
        'url': 'https://watch.islamchannel.tv/series/a6cccef3-3ef1-11eb-bc19-06b69c2357cd',
        'info_dict': {
            'id': 'a6cccef3-3ef1-11eb-bc19-06b69c2357cd',
        },
        'playlist_mincount': 31,
    }]

    def _real_extract(self, url):
        pl_id = self._match_id(url)
        webpage = self._download_webpage(url, pl_id)

        return self.playlist_from_matches(
            re.finditer(r'<a\s+href="(/watch/\d+)"[^>]+?data-video-type="show">', webpage),
            pl_id, getter=lambda x: urljoin(url, x.group(1)), ie=IslamChannelIE)
