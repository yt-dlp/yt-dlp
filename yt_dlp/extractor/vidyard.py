import functools
import re

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    float_or_none,
    int_or_none,
    join_nonempty,
    mimetype2ext,
    parse_resolution,
    str_or_none,
    unescapeHTML,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class VidyardBaseIE(InfoExtractor):
    _HEADERS = {'Referer': 'https://play.vidyard.com/'}

    def _get_formats_and_subtitles(self, sources, video_id):
        formats, subtitles = [], {}

        def add_hls_fmts_and_subs(m3u8_url):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                m3u8_url, video_id, 'mp4', m3u8_id='hls', headers=self._HEADERS, fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        hls_list = isinstance(sources, dict) and sources.pop('hls', None)
        if master_m3u8_url := traverse_obj(
                hls_list, (lambda _, v: v['profile'] == 'auto', 'url', {url_or_none}, any)):
            add_hls_fmts_and_subs(master_m3u8_url)
        if not formats:  # These are duplicate and unnecesary requests if we got 'auto' hls fmts
            for variant_m3u8_url in traverse_obj(hls_list, (..., 'url', {url_or_none})):
                add_hls_fmts_and_subs(variant_m3u8_url)

        for source_type, source_list in traverse_obj(sources, ({dict.items}, ...)):
            for source in traverse_obj(source_list, lambda _, v: url_or_none(v['url'])):
                profile = source.get('profile')
                formats.append({
                    'url': source['url'],
                    'ext': mimetype2ext(source.get('mimeType'), default=None),
                    'format_id': join_nonempty('http', source_type, profile),
                    **parse_resolution(profile),
                })

        self._remove_duplicate_formats(formats)
        return formats, subtitles

    def _get_direct_subtitles(self, caption_json):
        subs = {}
        for caption in traverse_obj(caption_json, lambda _, v: url_or_none(v['vttUrl'])):
            subs.setdefault(caption.get('language') or 'und', []).append({
                'url': caption['vttUrl'],
                'name': caption.get('name'),
            })

        return subs

    def _fetch_video_json(self, video_id):
        return self._download_json(
            f'https://play.vidyard.com/player/{video_id}.json', video_id)['payload']

    def _process_video_json(self, json_data, video_id):
        formats, subtitles = self._get_formats_and_subtitles(json_data['sources'], video_id)
        self._merge_subtitles(self._get_direct_subtitles(json_data.get('captions')), target=subtitles)

        return {
            **traverse_obj(json_data, {
                'id': ('facadeUuid', {str}),
                'display_id': ('videoId', {int}, {str_or_none}),
                'title': ('name', {str}),
                'description': ('description', {str}, {unescapeHTML}, {lambda x: x or None}),
                'duration': ((
                    ('milliseconds', {functools.partial(float_or_none, scale=1000)}),
                    ('seconds', {int_or_none})), any),
                'thumbnails': ('thumbnailUrls', ('small', 'normal'), {'url': {url_or_none}}),
                'tags': ('tags', ..., 'name', {str}),
            }),
            'formats': formats,
            'subtitles': subtitles,
            'http_headers': self._HEADERS,
        }


class VidyardIE(VidyardBaseIE):
    _VALID_URL = [
        r'https?://[\w-]+(?:\.hubs)?\.vidyard\.com/watch/(?P<id>[\w-]+)',
        r'https?://(?:embed|share)\.vidyard\.com/share/(?P<id>[\w-]+)',
        r'https?://play\.vidyard\.com/(?:player/)?(?P<id>[\w-]+)',
    ]
    _EMBED_REGEX = [r'<iframe[^>]* src=["\'](?P<url>(?:https?:)?//play\.vidyard\.com/[\w-]+)']
    _TESTS = [{
        'url': 'https://vyexample03.hubs.vidyard.com/watch/oTDMPlUv--51Th455G5u7Q',
        'info_dict': {
            'id': 'oTDMPlUv--51Th455G5u7Q',
            'display_id': '50347',
            'ext': 'mp4',
            'title': 'Homepage Video',
            'description': 'Look I changed the description.',
            'thumbnail': 'https://cdn.vidyard.com/thumbnails/50347/OUPa5LTKV46849sLYngMqQ_small.jpg',
            'duration': 99,
            'tags': ['these', 'are', 'all', 'tags'],
        },
    }, {
        'url': 'https://share.vidyard.com/watch/PaQzDAT1h8JqB8ivEu2j6Y?',
        'info_dict': {
            'id': 'PaQzDAT1h8JqB8ivEu2j6Y',
            'display_id': '9281024',
            'ext': 'mp4',
            'title': 'Inline Embed',
            'thumbnail': 'https://cdn.vidyard.com/thumbnails/spacer.gif',
            'duration': 41.186,
        },
    }, {
        'url': 'https://embed.vidyard.com/share/oTDMPlUv--51Th455G5u7Q',
        'info_dict': {
            'id': 'oTDMPlUv--51Th455G5u7Q',
            'display_id': '50347',
            'ext': 'mp4',
            'title': 'Homepage Video',
            'description': 'Look I changed the description.',
            'thumbnail': 'https://cdn.vidyard.com/thumbnails/50347/OUPa5LTKV46849sLYngMqQ_small.jpg',
            'duration': 99,
            'tags': ['these', 'are', 'all', 'tags'],
        },
    }, {
        # First video from playlist below
        'url': 'https://embed.vidyard.com/share/SyStyHtYujcBHe5PkZc5DL',
        'info_dict': {
            'id': 'SyStyHtYujcBHe5PkZc5DL',
            'display_id': '41974005',
            'ext': 'mp4',
            'title': 'Prepare the Frame and Track for Palm Beach Polysatin Shutters With BiFold Track',
            'description': r're:In this video, you will learn how to prepare the frame.+',
            'thumbnail': 'https://cdn.vidyard.com/thumbnails/41974005/IJw7oCaJcF1h7WWu3OVZ8A_small.png',
            'duration': 258.666,
        },
    }, {
        # Playlist
        'url': 'https://thelink.hubs.vidyard.com/watch/pwu7pCYWSwAnPxs8nDoFrE',
        'info_dict': {
            'id': 'pwu7pCYWSwAnPxs8nDoFrE',
            'title': 'PLAYLIST - Palm Beach Shutters- Bi-Fold Track System Installation',
            'entries': [{
                'id': 'SyStyHtYujcBHe5PkZc5DL',
                'display_id': '41974005',
                'ext': 'mp4',
                'title': 'Prepare the Frame and Track for Palm Beach Polysatin Shutters With BiFold Track',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/41974005/IJw7oCaJcF1h7WWu3OVZ8A_small.png',
                'duration': 258.666,
            }, {
                'id': '1Fw4B84jZTXLXWqkE71RiM',
                'display_id': '5861113',
                'ext': 'mp4',
                'title': 'Palm Beach - Bi-Fold Track System "Frame Installation"',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/5861113/29CJ54s5g1_aP38zkKLHew_small.jpg',
                'duration': 167.858,
            }, {
                'id': 'DqP3wBvLXSpxrcqpT5kEeo',
                'display_id': '41976334',
                'ext': 'mp4',
                'title': 'Install the Track for Palm Beach Polysatin Shutters With BiFold Track',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/5861090/RwG2VaTylUa6KhSTED1r1Q_small.png',
                'duration': 94.229,
            }, {
                'id': 'opfybfxpzQArxqtQYB6oBU',
                'display_id': '41976364',
                'ext': 'mp4',
                'title': 'Install the Panel for Palm Beach Polysatin Shutters With BiFold Track',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/5860926/JIOaJR08dM4QgXi_iQ2zGA_small.png',
                'duration': 191.467,
            }, {
                'id': 'rWrXvkbTNNaNqD6189HJya',
                'display_id': '41976382',
                'ext': 'mp4',
                'title': 'Adjust the Panels for Palm Beach Polysatin Shutters With BiFold Track',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/5860687/CwHxBv4UudAhOh43FVB4tw_small.png',
                'duration': 138.155,
            }, {
                'id': 'eYPTB521MZ9TPEArSethQ5',
                'display_id': '41976409',
                'ext': 'mp4',
                'title': 'Assemble and Install the Valance for Palm Beach Polysatin Shutters With BiFold Track',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/5861425/0y68qlMU4O5VKU7bJ8i_AA_small.png',
                'duration': 148.224,
            }],
        },
        'playlist_count': 6,
    }, {
        # Non hubs.vidyard.com playlist
        'url': 'https://salesforce.vidyard.com/watch/d4vqPjs7Q5EzVEis5QT3jd',
        'info_dict': {
            'id': 'd4vqPjs7Q5EzVEis5QT3jd',
            'title': 'How To: Service Cloud: Import External Content in Lightning Knowledge',
            'entries': [{
                'id': 'mcjDpSZir2iSttbvFkx6Rv',
                'display_id': '29479036',
                'ext': 'mp4',
                'title': 'Welcome to this Expert Coaching Series',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/ouyQi9WuwyiOupChUWNmjQ/7170d3485ba602e012df05_small.jpg',
                'duration': 38.205,
            }, {
                'id': '84bPYwpg243G6xYEfJdYw9',
                'display_id': '21820704',
                'ext': 'mp4',
                'title': 'Chapter 1 - Title + Agenda',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/HFPN0ZgQq4Ow8BghGcQSow/bfaa30123c8f6601e7d7f2_small.jpg',
                'duration': 98.016,
            }, {
                'id': 'nP17fMuvA66buVHUrzqjTi',
                'display_id': '21820707',
                'ext': 'mp4',
                'title': 'Chapter 2 - Import Options',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/rGRIF5nFjPI9OOA2qJ_Dbg/86a8d02bfec9a566845dd4_small.jpg',
                'duration': 199.136,
            }, {
                'id': 'm54EcwXdpA5gDBH5rgCYoV',
                'display_id': '21820710',
                'ext': 'mp4',
                'title': 'Chapter 3 - Importing Article Translations',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/IVX4XR8zpSsiNIHx45kz-A/1ccbf8a29a33856d06b3ed_small.jpg',
                'duration': 184.352,
            }, {
                'id': 'j4nzS42oq4hE9oRV73w3eQ',
                'display_id': '21820716',
                'ext': 'mp4',
                'title': 'Chapter 4 - Best Practices',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/BtrRrQpRDLbA4AT95YQyog/1f1e6b8e7fdc3fa95ec8d3_small.jpg',
                'duration': 296.960,
            }, {
                'id': 'y28PYfW5pftvers9PXzisC',
                'display_id': '21820727',
                'ext': 'mp4',
                'title': 'Chapter 5 - Migration Steps',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/K2CdQOXDfLcrVTF60r0bdw/a09239ada28b6ffce12b1f_small.jpg',
                'duration': 620.640,
            }, {
                'id': 'YWU1eQxYvhj29SjYoPw5jH',
                'display_id': '21820733',
                'ext': 'mp4',
                'title': 'Chapter 6 - Demo',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/rsmhP-cO8dAa8ilvFGCX0g/7911ef415167cd14032068_small.jpg',
                'duration': 631.456,
            }, {
                'id': 'nmEvVqpwdJUgb74zKsLGxn',
                'display_id': '29479037',
                'ext': 'mp4',
                'title': 'Schedule Your Follow-Up',
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/Rtwc7X4PEkF4Ae5kHi-Jvw/174ebed3f34227b1ffa1d0_small.jpg',
                'duration': 33.608,
            }],
        },
        'playlist_count': 8,
    }, {
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
    }, {
        # Player JSON URL
        'url': 'https://play.vidyard.com/player/7GAApnNNbcZZ46k6JqJQSh.json?disable_analytics=0',
        'info_dict': {
            'id': '7GAApnNNbcZZ46k6JqJQSh',
            'display_id': '820026',
            'ext': 'mp4',
            'title': 'The Art of Storytelling: How to Deliver Your Brand Story with Content & Social',
            'thumbnail': 'https://cdn.vidyard.com/thumbnails/MhbE-5sEFQu4x3fI6FkNlA/41eb5717c557cd19456910_small.jpg',
            'duration': 2153.013,
            'tags': ['Summit2017'],
        },
    }, {
        'url': 'http://share.vidyard.com/share/diYeo6YR2yiGgL8odvS8Ri',
        'only_matching': True,
    }, {
        'url': 'https://play.vidyard.com/FFlz3ZpxhIfKQ1fd9DAryA',
        'only_matching': True,
    }, {
        'url': 'https://play.vidyard.com/qhMAu5A76GZVrFzOPgSf9A/type/standalone',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
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
    }, {
        # <script ... id="vidyard_embed_code_DXx2sW4WaLA6hTdGFz7ja8" src="//play.vidyard.com/DXx2sW4WaLA6hTdGFz7ja8.js?
        'url': 'http://videos.vivint.com/watch/DXx2sW4WaLA6hTdGFz7ja8',
        'info_dict': {
            'id': 'DXx2sW4WaLA6hTdGFz7ja8',
            'display_id': '2746529',
            'ext': 'mp4',
            'title': 'How To Powercycle the Smart Hub Panel',
            'duration': 30.613,
            'thumbnail': 'https://cdn.vidyard.com/thumbnails/_-6cw8xQUJ3qiCs_JENc_A/b21d7a5e47967f49399d30_small.jpg',
        },
    }, {
        # <script id="vidyard_embed_code_MIBHhiLVTxga7wqLsuoDjQ" src="//embed.vidyard.com/embed/MIBHhiLVTxga7wqLsuoDjQ/inline?v=2.1">
        'url': 'https://www.babypips.com/learn/forex/introduction-to-metatrader4',
        'info_dict': {
            'id': 'MIBHhiLVTxga7wqLsuoDjQ',
            'display_id': '20291',
            'ext': 'mp4',
            'title': 'Lesson 1 - Opening an MT4 Account',
            'description': 'Never heard of MetaTrader4? Here\'s the 411 on the popular trading platform!',
            'duration': 168,
            'thumbnail': 'https://cdn.vidyard.com/thumbnails/20291/IM-G2WXQR9VBLl2Cmzvftg_small.jpg',
        },
    }, {
        # <iframe ... src="//play.vidyard.com/d61w8EQoZv1LDuPxDkQP2Q/type/background?preview=1"
        'url': 'https://www.avaya.com/en/',
        'info_dict': {
            # These values come from the generic extractor and don't matter
            'id': str,
            'title': str,
            'age_limit': 0,
            'upload_date': str,
            'description': str,
            'thumbnail': str,
            'timestamp': float,
        },
        'playlist': [{
            'info_dict': {
                'id': 'd61w8EQoZv1LDuPxDkQP2Q',
                'display_id': '42456529',
                'ext': 'mp4',
                'title': 'GettyImages-1027',
                'duration': 6.0,
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/42061563/p6bY08d2N4e4IDz-7J4_wkgsPq3-qgcx_small.jpg',
            },
        }, {
            'info_dict': {
                'id': 'VAsYDi7eiqZRbHodUA2meC',
                'display_id': '42456569',
                'ext': 'mp4',
                'title': 'GettyImages-1325598833',
                'duration': 6.083,
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/42052358/y3qrbDpn_2quWr_5XBi7yzS3UvEI__ZM_small.jpg',
            },
        }],
        'playlist_count': 2,
    }, {
        # <div class="vidyard-player-embed" data-uuid="vpCWTVHw3qrciLtVY94YkS"
        'url': 'https://www.gogoair.com/',
        'info_dict': {
            # These values come from the generic extractor and don't matter
            'id': str,
            'title': str,
            'description': str,
            'age_limit': 0,
        },
        'playlist': [{
            'info_dict': {
                'id': 'vpCWTVHw3qrciLtVY94YkS',
                'display_id': '40780699',
                'ext': 'mp4',
                'title': 'Upgrade to AVANCE 100% worth it - Jason Talley, Owner and Pilot, Testimonial',
                'description': 'md5:f609824839439a51990cef55ffc472aa',
                'duration': 70.737,
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/40780699/KzjfYZz5MZl2gHF_e-4i2c6ib1cLDweQ_small.jpg',
            },
        }, {
            'info_dict': {
                'id': 'xAmV9AsLbnitCw35paLBD8',
                'display_id': '31130867',
                'ext': 'mp4',
                'title': 'Brad Keselowski goes faster with Gogo AVANCE inflight Wi-Fi',
                'duration': 132.565,
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/31130867/HknyDtLdm2Eih9JZ4A5XLjhfBX_6HRw5_small.jpg',
            },
        }, {
            'info_dict': {
                'id': 'RkkrFRNxfP79nwCQavecpF',
                'display_id': '39009815',
                'ext': 'mp4',
                'title': 'Live Demo of Gogo Galileo',
                'description': 'md5:e2df497236f4e12c3fef8b392b5f23e0',
                'duration': 112.128,
                'thumbnail': 'https://cdn.vidyard.com/thumbnails/38144873/CWLlxfUbJ4Gh0ThbUum89IsEM4yupzMb_small.jpg',
            },
        }],
        'playlist_count': 3,
    }]

    @classmethod
    def _extract_embed_urls(cls, url, webpage):
        # Handle protocol-less embed URLs
        for embed_url in super()._extract_embed_urls(url, webpage):
            if embed_url.startswith('//'):
                embed_url = f'https:{embed_url}'
            yield embed_url

        # Extract inline/lightbox embeds
        for embed_element in re.findall(
                r'(<(?:img|div)[^>]* class=(["\'])(?:[^>"\']* )?vidyard-player-embed(?: [^>"\']*)?\2[^>]+>)', webpage):
            if video_id := extract_attributes(embed_element[0]).get('data-uuid'):
                yield f'https://play.vidyard.com/{video_id}'

        for embed_id in re.findall(r'<script[^>]* id=["\']vidyard_embed_code_([\w-]+)["\']', webpage):
            yield f'https://play.vidyard.com/{embed_id}'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_json = self._fetch_video_json(video_id)

        if len(video_json['chapters']) == 1:
            return self._process_video_json(video_json['chapters'][0], video_id)

        return self.playlist_result(
            [self._process_video_json(chapter, video_id) for chapter in video_json['chapters']],
            str(video_json['playerUuid']), video_json.get('name'))
