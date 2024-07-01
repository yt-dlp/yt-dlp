import re

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    float_or_none,
    int_or_none,
    traverse_obj,
)


class VidyardBaseIE(InfoExtractor):

    _HEADERS = {}

    def _get_formats_and_subtitles(self, video_source, video_id):
        formats, subtitles = [], {}
        for source_type, sources in traverse_obj(video_source, ({dict.items}, lambda _, v: v[1][0])):
            if source_type == 'hls':
                for video_hls in sources:
                    fmts, subs = self._extract_m3u8_formats_and_subtitles(video_hls.get('url'), video_id, headers=self._HEADERS, fatal=False)
                    formats.extend(fmts)
                    self._merge_subtitles(subs, target=subtitles)
            else:
                formats.extend({
                    'url': video_mp4.get('url'),
                    'ext': 'mp4',
                } for video_mp4 in sources)

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
            'id': str(json_data.get('facadeUuid') or json_data['videoUuid']),
            'display_id': str(json_data['videoId']),
            'title': json_data.get('name') or None,
            'description': json_data.get('description') or None,
            'duration': float_or_none(json_data.get('milliseconds'), 1000) or int_or_none(json_data.get('seconds')),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': [{'url': thumbnail_url}
                           for thumbnail_url in traverse_obj(json_data, ('thumbnailUrls', ...))],
            'http_headers': self._HEADERS,
        }


class VidyardIE(VidyardBaseIE):
    _VALID_URL = [
        r'https?://[\w-]+(?:\.hubs)?\.vidyard\.com/watch/(?P<id>[\w-]+)',
        r'https?://embed\.vidyard\.com/share/(?P<id>[\w-]+)',
        r'https?://play\.vidyard\.com/(?P<id>[\w-]+)\.html',
    ]
    _TESTS = [
        {
            'url': 'https://vyexample03.hubs.vidyard.com/watch/oTDMPlUv--51Th455G5u7Q',
            'info_dict': {
                'id': 'oTDMPlUv--51Th455G5u7Q',
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
                'id': 'PaQzDAT1h8JqB8ivEu2j6Y',
                'display_id': '9281024',
                'ext': 'mp4',
                'title': 'Inline Embed',
                'description': 'Vidyard video',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/spacer.gif',
                'duration': 41.186,
            },
        },
        {
            'url': 'https://embed.vidyard.com/share/oTDMPlUv--51Th455G5u7Q',
            'info_dict': {
                'id': 'oTDMPlUv--51Th455G5u7Q',
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
                'id': 'SyStyHtYujcBHe5PkZc5DL',
                'display_id': '41974005',
                'ext': 'mp4',
                'title': 'Prepare the Frame and Track for Palm Beach Polysatin Shutters With BiFold Track',
                'description': 'In this video, you will learn how to prepare the frame and track on Palm Beach shutters with a Bi-Fold Track system.',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/41974005/IJw7oCaJcF1h7WWu3OVZ8A_small.png',
                'duration': 258.666,
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
                        'id': 'SyStyHtYujcBHe5PkZc5DL',
                        'display_id': '41974005',
                        'ext': 'mp4',
                        'title': 'Prepare the Frame and Track for Palm Beach Polysatin Shutters With BiFold Track',
                        'thumbnail': 'https://cdn.vidyard.com/thumbnails/41974005/IJw7oCaJcF1h7WWu3OVZ8A_small.png',
                        'duration': 258.666,
                    },
                    {
                        'id': '1Fw4B84jZTXLXWqkE71RiM',
                        'display_id': '5861113',
                        'ext': 'mp4',
                        'title': 'Palm Beach - Bi-Fold Track System "Frame Installation"',
                        'thumbnail': 'https://cdn.vidyard.com/thumbnails/5861113/29CJ54s5g1_aP38zkKLHew_small.jpg',
                        'duration': 167.858,
                    },
                    {
                        'id': 'DqP3wBvLXSpxrcqpT5kEeo',
                        'display_id': '41976334',
                        'ext': 'mp4',
                        'title': 'Install the Track for Palm Beach Polysatin Shutters With BiFold Track',
                        'thumbnail': 'https://cdn.vidyard.com/thumbnails/5861090/RwG2VaTylUa6KhSTED1r1Q_small.png',
                        'duration': 94.229,
                    },
                    {
                        'id': 'opfybfxpzQArxqtQYB6oBU',
                        'display_id': '41976364',
                        'ext': 'mp4',
                        'title': 'Install the Panel for Palm Beach Polysatin Shutters With BiFold Track',
                        'thumbnail': 'https://cdn.vidyard.com/thumbnails/5860926/JIOaJR08dM4QgXi_iQ2zGA_small.png',
                        'duration': 191.467,
                    },
                    {
                        'id': 'rWrXvkbTNNaNqD6189HJya',
                        'display_id': '41976382',
                        'ext': 'mp4',
                        'title': 'Adjust the Panels for Palm Beach Polysatin Shutters With BiFold Track',
                        'thumbnail': 'https://cdn.vidyard.com/thumbnails/5860687/CwHxBv4UudAhOh43FVB4tw_small.png',
                        'duration': 138.155,
                    },
                    {
                        'id': 'eYPTB521MZ9TPEArSethQ5',
                        'display_id': '41976409',
                        'ext': 'mp4',
                        'title': 'Assemble and Install the Valance for Palm Beach Polysatin Shutters With BiFold Track',
                        'thumbnail': 'https://cdn.vidyard.com/thumbnails/5861425/0y68qlMU4O5VKU7bJ8i_AA_small.png',
                        'duration': 148.224,
                    },
                ],
            },
            'playlist_count': 6,
        },
        {
            # Non hubs.vidyard.com playlist
            'url': 'https://salesforce.vidyard.com/watch/d4vqPjs7Q5EzVEis5QT3jd',
            'info_dict': {
                '_type': 'playlist',
                'id': 'd4vqPjs7Q5EzVEis5QT3jd',
                'title': 'How To: Service Cloud: Import External Content in Lightning Knowledge',
                'entries': [
                    {
                        'id': 'mcjDpSZir2iSttbvFkx6Rv',
                        'display_id': '29479036',
                        'ext': 'mp4',
                        'title': 'Welcome to this Expert Coaching Series',
                        'thumbnail': 'https://cdn.vidyard.com/thumbnails/ouyQi9WuwyiOupChUWNmjQ/7170d3485ba602e012df05_small.jpg',
                        'duration': 38.205,
                    },
                    {
                        'id': '84bPYwpg243G6xYEfJdYw9',
                        'display_id': '21820704',
                        'ext': 'mp4',
                        'title': 'Chapter 1 - Title + Agenda',
                        'thumbnail': 'https://cdn.vidyard.com/thumbnails/HFPN0ZgQq4Ow8BghGcQSow/bfaa30123c8f6601e7d7f2_small.jpg',
                        'duration': 98.016,
                    },
                    {
                        'id': 'nP17fMuvA66buVHUrzqjTi',
                        'display_id': '21820707',
                        'ext': 'mp4',
                        'title': 'Chapter 2 - Import Options',
                        'thumbnail': 'https://cdn.vidyard.com/thumbnails/rGRIF5nFjPI9OOA2qJ_Dbg/86a8d02bfec9a566845dd4_small.jpg',
                        'duration': 199.136,
                    },
                    {
                        'id': 'm54EcwXdpA5gDBH5rgCYoV',
                        'display_id': '21820710',
                        'ext': 'mp4',
                        'title': 'Chapter 3 - Importing Article Translations',
                        'thumbnail': 'https://cdn.vidyard.com/thumbnails/IVX4XR8zpSsiNIHx45kz-A/1ccbf8a29a33856d06b3ed_small.jpg',
                        'duration': 184.352,
                    },
                    {
                        'id': 'j4nzS42oq4hE9oRV73w3eQ',
                        'display_id': '21820716',
                        'ext': 'mp4',
                        'title': 'Chapter 4 - Best Practices',
                        'thumbnail': 'https://cdn.vidyard.com/thumbnails/BtrRrQpRDLbA4AT95YQyog/1f1e6b8e7fdc3fa95ec8d3_small.jpg',
                        'duration': 296.960,
                    },
                    {
                        'id': 'y28PYfW5pftvers9PXzisC',
                        'display_id': '21820727',
                        'ext': 'mp4',
                        'title': 'Chapter 5 - Migration Steps',
                        'thumbnail': 'https://cdn.vidyard.com/thumbnails/K2CdQOXDfLcrVTF60r0bdw/a09239ada28b6ffce12b1f_small.jpg',
                        'duration': 620.640,
                    },
                    {
                        'id': 'YWU1eQxYvhj29SjYoPw5jH',
                        'display_id': '21820733',
                        'ext': 'mp4',
                        'title': 'Chapter 6 - Demo',
                        'thumbnail': 'https://cdn.vidyard.com/thumbnails/rsmhP-cO8dAa8ilvFGCX0g/7911ef415167cd14032068_small.jpg',
                        'duration': 631.456,
                    },
                    {
                        'id': 'nmEvVqpwdJUgb74zKsLGxn',
                        'display_id': '29479037',
                        'ext': 'mp4',
                        'title': 'Schedule Your Follow-Up',
                        'thumbnail': 'https://cdn.vidyard.com/thumbnails/Rtwc7X4PEkF4Ae5kHi-Jvw/174ebed3f34227b1ffa1d0_small.jpg',
                        'duration': 33.608,
                    },
                ],
            },
            'playlist_count': 8,
        },
        {
            # URL of iframe embed src
            'url': 'https://play.vidyard.com/iDqTwWGrd36vaLuaCY3nTs.html',
            'info_dict': {
                'id': 'iDqTwWGrd36vaLuaCY3nTs',
                'display_id': '9281009',
                'ext': 'mp4',
                'title': 'Lightbox Embed',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/spacer.gif',
                'duration': 39.035,
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
                'id': 'GDx1oXrFWj4XHbipfoXaMn',
                'display_id': '3225198',
                'ext': 'mp4',
                'title': 'The Extreme Importance of PC Board Stack Up',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/73_Q3_hBexWX7Og1sae6cg/9998fa4faec921439e2c04_small.jpg',
                'duration': 3422.742,
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
            embed = extract_attributes(embed_elm[0])
            uuid = embed.get('data-uuid')
            if uuid:
                yield f'https://play.vidyard.com/{uuid}.html'

    def _real_extract(self, url):
        video_id = self._match_id(url)
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
