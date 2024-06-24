import re

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    int_or_none,
    traverse_obj,
)


class VidyardBaseIE(InfoExtractor):

    _HEADERS = {}

    def _get_formats_and_subtitles(self, video_source, video_id):
        video_source = video_source or {}
        formats, subtitles = [], {}
        for key, value in video_source.items():
            if key == 'hls':
                for video_hls in value:
                    fmts, subs = self._extract_m3u8_formats_and_subtitles(video_hls.get('url'), video_id, headers=self._HEADERS)
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

    def _fetch_video_json(self, video_uuid, video_id=None):
        video_id = video_id or video_uuid
        return self._download_json(
            f'https://play.vidyard.com/player/{video_uuid}.json', video_id)['payload']

    def _process_video_json(self, json_data, video_id):
        formats, subtitles = self._get_formats_and_subtitles(json_data['sources'], video_id)
        self._merge_subtitles(self._get_direct_subtitles(json_data.get('captions')), target=subtitles)

        return {
            'id': str(json_data['videoUuid']),
            'display_id': str(json_data['videoId']),
            'title': json_data.get('name') or None,
            'description': json_data.get('description') or None,
            'duration': int_or_none(json_data.get('seconds')),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': [{'url': thumbnail_url}
                           for thumbnail_url in traverse_obj(json_data, ('thumbnailUrls', ...))],
            'http_headers': self._HEADERS,
        }


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
                'id': 'WcqshZjX7-vEe1l_hNc3Qg',
                'display_id': '50347',
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
                'id': 'GBL8gBrBaqC-JVG_6HTMyg',
                'display_id': '9281024',
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
                'id': 'WcqshZjX7-vEe1l_hNc3Qg',
                'display_id': '50347',
                'ext': 'mp4',
                'title': 'Homepage Video',
                'description': 'Look I changed the description.',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/50347/OUPa5LTKV46849sLYngMqQ_small.jpg',
                'duration': 99,
            },
        },
        {
            # First video from playlist below
            'url': 'https://embed.vidyard.com/share/SyStyHtYujcBHe5PkZc5DL',
            'info_dict': {
                'id': 'p5vsX0bzLxetOJbfGZ6Z6Q',
                'display_id': '41974005',
                'ext': 'mp4',
                'title': 'Prepare the Frame and Track for Palm Beach Polysatin Shutters With BiFold Track',
                'description': 'In this video, you will learn how to prepare the frame and track on Palm Beach shutters with a Bi-Fold Track system.',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/41974005/IJw7oCaJcF1h7WWu3OVZ8A_small.png',
                'duration': 259,
            },
        },
        {
            # Playlist
            'url': 'https://thelink.hubs.vidyard.com/watch/pwu7pCYWSwAnPxs8nDoFrE',
            'info_dict': {
                '_type': 'playlist',
                'id': 'pwu7pCYWSwAnPxs8nDoFrE',
                'title': 'PLAYLIST - Palm Beach Shutters- Bi-Fold Track System Installation',
                'entries': [
                    {
                        'id': 'p5vsX0bzLxetOJbfGZ6Z6Q',
                        'display_id': '41974005',
                        'ext': 'mp4',
                        'title': 'Prepare the Frame and Track for Palm Beach Polysatin Shutters With BiFold Track',
                        'thumbnail': 'https://cdn.vidyard.com/thumbnails/41974005/IJw7oCaJcF1h7WWu3OVZ8A_small.png',
                        'duration': 259,
                    },
                    {
                        'id': 'tn_0u7-ONJd2Pd8i3kxIeg',
                        'display_id': '5861113',
                        'ext': 'mp4',
                        'title': 'Palm Beach - Bi-Fold Track System "Frame Installation"',
                        'thumbnail': 'https://cdn.vidyard.com/thumbnails/5861113/29CJ54s5g1_aP38zkKLHew_small.jpg',
                        'duration': 167,
                    },
                    {
                        'id': 'fU7rvJu-nQKNnJzV_hOt6A',
                        'display_id': '41976334',
                        'ext': 'mp4',
                        'title': 'Install the Track for Palm Beach Polysatin Shutters With BiFold Track',
                        'thumbnail': 'https://cdn.vidyard.com/thumbnails/5861090/RwG2VaTylUa6KhSTED1r1Q_small.png',
                        'duration': 94,
                    },
                    {
                        'id': 'ueXUJagJso7KO_tnBkYo2Q',
                        'display_id': '41976364',
                        'ext': 'mp4',
                        'title': 'Install the Panel for Palm Beach Polysatin Shutters With BiFold Track',
                        'thumbnail': 'https://cdn.vidyard.com/thumbnails/5860926/JIOaJR08dM4QgXi_iQ2zGA_small.png',
                        'duration': 191,
                    },
                    {
                        'id': 'U9hEsKlpPTMasqEf5n0KQg',
                        'display_id': '41976382',
                        'ext': 'mp4',
                        'title': 'Adjust the Panels for Palm Beach Polysatin Shutters With BiFold Track',
                        'thumbnail': 'https://cdn.vidyard.com/thumbnails/5860687/CwHxBv4UudAhOh43FVB4tw_small.png',
                        'duration': 138,
                    },
                    {
                        'id': 'gBdBzCvGXK5j2f20lAF-vg',
                        'display_id': '41976409',
                        'ext': 'mp4',
                        'title': 'Assemble and Install the Valance for Palm Beach Polysatin Shutters With BiFold Track',
                        'thumbnail': 'https://cdn.vidyard.com/thumbnails/5861425/0y68qlMU4O5VKU7bJ8i_AA_small.png',
                        'duration': 148,
                    },
                ],
            },
            'playlist_count': 6,
        },
        {
            # URL of iframe embed src
            'url': 'https://play.vidyard.com/iDqTwWGrd36vaLuaCY3nTs.html',
            'info_dict': {
                'id': 'lrYeWCqR3UCAzwqUAgegHg',
                'display_id': '9281009',
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
                'id': 'rGGKQEAu8X-APkU68K8U_w',
                'display_id': '3225198',
                'ext': 'mp4',
                'title': 'The Extreme Importance of PC Board Stack Up',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/73_Q3_hBexWX7Og1sae6cg/9998fa4faec921439e2c04_small.jpg',
                'duration': 3422,
            },
        },
    ]
    _HEADERS = {
        'referer': 'https://play.vidyard.com/',
    }

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
        video_json = self._fetch_video_json(video_id)

        if len(video_json['chapters']) == 1:
            video_info = self._process_video_json(video_json['chapters'][0], video_id)

            if video_info['title'] is None or video_info['description'] is None:
                webpage = self._download_webpage(url, video_id, fatal=False)

                if video_info['title'] is None:
                    video_info['title'] = self._og_search_title(webpage, default=None) or self._html_extract_title(webpage)

                if video_info['description'] is None:
                    video_info['description'] = self._og_search_description(webpage, default=None)

            return video_info

        # Playlist
        return self.playlist_result(
            [self._process_video_json(chapter, video_id) for chapter in video_json['chapters']],
            playlist_id=str(video_json['playerUuid']),
            playlist_title=video_json.get('name'))
