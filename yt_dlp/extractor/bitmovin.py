import re

from .common import InfoExtractor
from ..utils.traversal import traverse_obj


class BitmovinIE(InfoExtractor):
    _VALID_URL = r'https?://streams\.bitmovin\.com/(?P<id>\w+)'
    _EMBED_REGEX = [r'<iframe\b[^>]+\bsrc=["\'](?P<url>(?:https?:)?//streams\.bitmovin\.com/(?P<id>\w+)[^"\']+)']
    _TESTS = [{
        'url': 'https://streams.bitmovin.com/cqkl1t5giv3lrce7pjbg/embed',
        'info_dict': {
            'id': 'cqkl1t5giv3lrce7pjbg',
            'ext': 'mp4',
            'title': 'Developing Osteopathic Residents as Faculty',
            'thumbnail': 'https://streams.bitmovin.com/cqkl1t5giv3lrce7pjbg/poster',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://streams.bitmovin.com/cgl9rh94uvs51rqc8jhg/share',
        'info_dict': {
            'id': 'cgl9rh94uvs51rqc8jhg',
            'ext': 'mp4',
            'title': 'Big Buck Bunny (Streams Docs)',
            'thumbnail': 'https://streams.bitmovin.com/cgl9rh94uvs51rqc8jhg/poster',
        },
        'params': {'skip_download': 'm3u8'},
    }]
    _WEBPAGE_TESTS = [{
        # bitmovin-stream web component
        'url': 'https://www.institutionalinvestor.com/article/2bsw1in1l9k68mp9kritc/video-war-stories-over-board-games/best-case-i-get-fired-war-stories',
        'info_dict': {
            'id': 'cuiumeil6g115lc4li3g',
            'ext': 'mp4',
            'title': '[media] War Stories over Board Games: ‚ÄúBest Case: I Get Fired‚Äù ',
            'thumbnail': 'https://streams.bitmovin.com/cuiumeil6g115lc4li3g/poster',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # iframe embed
        'url': 'https://www.clearblueionizer.com/en/pool-ionizers/mineral-pool-vs-saltwater-pool/',
        'info_dict': {
            'id': 'cvpvfsm1pf7itg7cfvtg',
            'ext': 'mp4',
            'title': 'Pool Ionizer vs. Salt Chlorinator',
            'thumbnail': 'https://streams.bitmovin.com/cvpvfsm1pf7itg7cfvtg/poster',
        },
        'params': {'skip_download': 'm3u8'},
    }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        yield from super()._extract_embed_urls(url, webpage)
        for stream_id in re.findall(r'<bitmovin-stream\b[^>]*\bstream-id=["\'](?P<id>\w+)', webpage):
            yield f'https://streams.bitmovin.com/{stream_id}'

    def _real_extract(self, url):
        video_id = self._match_id(url)

        player_config = self._download_json(
            f'https://streams.bitmovin.com/{video_id}/config', video_id)['sources']

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            player_config['hls'], video_id, 'mp4')

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(player_config, {
                'title': ('title', {str}),
                'thumbnail': ('poster', {str}),
            }),
        }
