import re

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    int_or_none,
    traverse_obj,
)


class VidyardBaseIE(InfoExtractor):

    def _get_formats_and_subtitles(self, video_source, video_id):
        video_source = video_source or {}
        formats, subtitles = [], {}
        for key, value in video_source.items():
            if key == 'hls':
                for video_hls in value:
                    fmts, subs = self._extract_m3u8_formats_and_subtitles(video_hls.get('url'), video_id, headers={
                        'referer': 'https://play.vidyard.com/',
                    })
                    formats.extend(fmts)
                    self._merge_subtitles(subs, target=subtitles)
            else:
                formats.extend({
                    'url': video_mp4.get('url'),
                    'ext': 'mp4',
                } for video_mp4 in value)

        return formats, subtitles

    def _get_direct_subtitles(self, caption_json):
        subs = {}
        for caption in caption_json:
            subs.setdefault(caption.get('language') or 'und', []).append({
                'url': caption.get('vttUrl'),
                'name': caption.get('name'),
            })

        return subs

    def _webpage_url(self, url, video_id):
        return url


class VidyardIE(VidyardBaseIE):
    _VALID_URL = [
        r'https?://(?:[\w-]+\.hubs|share)\.vidyard\.com/watch/(?P<id>[\w-]+)',
        r'https?://embed\.vidyard\.com/share/(?P<id>[\w-]+)',
        r'https?://play\.vidyard\.com/(?P<id>[\w-]+)\.html',
    ]
    _TESTS = [
        {
            'url': 'https://vyexample03.hubs.vidyard.com/watch/oTDMPlUv--51Th455G5u7Q',
            'info_dict': {
                'id': '50347',
                'ext': 'mp4',
                'title': 'Homepage Video',
                'description': 'Look I changed the description.',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/50347/OUPa5LTKV46849sLYngMqQ_small.jpg',
                'duration': 99,
            },
        },
        {
            'url': 'https://share.vidyard.com/watch/PaQzDAT1h8JqB8ivEu2j6Y?',
            'info_dict': {
                'id': '9281024',
                'ext': 'mp4',
                'title': 'Inline Embed',
                'description': 'Vidyard video',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/spacer.gif',
                'duration': 41,
            },
        },
        {
            'url': 'https://embed.vidyard.com/share/oTDMPlUv--51Th455G5u7Q',
            'info_dict': {
                'id': '50347',
                'ext': 'mp4',
                'title': 'Homepage Video',
                'description': 'Look I changed the description.',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/50347/OUPa5LTKV46849sLYngMqQ_small.jpg',
                'duration': 99,
            },
        },
        {
            # URL of iframe embed src
            'url': 'https://play.vidyard.com/iDqTwWGrd36vaLuaCY3nTs.html',
            'info_dict': {
                'id': '9281009',
                'ext': 'mp4',
                'title': 'Lightbox Embed',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/spacer.gif',
                'duration': 39,
            },
        },
        {
            # URL of iframe embed src (protocol relative URL)
            'url': '//play.vidyard.com/iDqTwWGrd36vaLuaCY3nTs.html?',
            'info_dict': {
                'id': '9281009',
                'ext': 'mp4',
                'title': 'Lightbox Embed',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/spacer.gif',
                'duration': 39,
            },
        },
    ]
    _EMBED_REGEX = [
        # iframe embed
        r'<iframe[^>]+?src=(["\'])(?P<url>(?:https?:)?//play\.vidyard\.com/[\w-]+.\w+)\1',
    ]
    _WEBPAGE_TESTS = [
        {
            # URL containing inline/lightbox embedded video
            'url': 'https://resources.altium.com/p/2-the-extreme-importance-of-pc-board-stack-up',
            'info_dict': {
                'id': '3225198',
                'ext': 'mp4',
                'title': 'The Extreme Importance of PC Board Stack Up',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/73_Q3_hBexWX7Og1sae6cg/9998fa4faec921439e2c04_small.jpg',
                'duration': 3422,
            },
        },
    ]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        # Handle protocol-less embed URLs
        for embed_url in super()._extract_embed_urls(url, webpage):
            if embed_url.startswith('//'):
                embed_url = f'https:{embed_url}'
            yield embed_url

        # Extract inline/lightbox embeds
        for embed_elm in re.findall(r'(<img[^>]+class=(["\'])(?:[^>"\']* )?vidyard-player-embed(?: [^>"\']*)?\2[^>]+[^>]*>)', webpage):
            embed = extract_attributes(embed_elm[0]) or {}
            uuid = embed.get('data-uuid')
            if uuid:
                yield f'https://play.vidyard.com/{uuid}.html'

    def _real_extract(self, url):
        video_id = self._match_valid_url(url).group('id')
        webpage = self._download_webpage(self._webpage_url(url, video_id), video_id)

        json_data = self._download_json(
            f'https://play.vidyard.com/player/{video_id}.json', video_id)['payload']['chapters'][0]

        formats, subtitles = self._get_formats_and_subtitles(json_data['sources'], video_id)
        self._merge_subtitles(self._get_direct_subtitles(json_data.get('captions')), target=subtitles)

        return {
            'id': str(json_data['videoId']),
            'title': json_data.get('name') or self._og_search_title(webpage, default=None) or self._html_extract_title(webpage),
            'description': json_data.get('description') or self._og_search_description(webpage, default=None),
            'duration': int_or_none(json_data.get('seconds')),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': [{'url': thumbnail_url}
                           for thumbnail_url in traverse_obj(json_data, ('thumbnailUrls', ...))],
            'http_headers': {
                'referer': 'https://play.vidyard.com/',
            },
        }
