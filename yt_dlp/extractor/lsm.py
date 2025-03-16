import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    js_to_json,
    parse_iso8601,
    parse_qs,
    str_or_none,
    url_or_none,
    urljoin,
)
from ..utils.traversal import traverse_obj


class LSMLREmbedIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(?:
            (?:latvijasradio|lr1|lr2|klasika|lr4|naba|radioteatris)\.lsm|
            pieci
        )\.lv/[^/?#]+/(?:
            pleijeris|embed
        )/?\?(?:[^#]+&)?(?:show|id)=(?P<id>\d+)'''
    _TESTS = [{
        'url': 'https://latvijasradio.lsm.lv/lv/embed/?theme=black&size=16x9&showCaptions=0&id=183522',
        'md5': '719b33875cd1429846eeeaeec6df2830',
        'info_dict': {
            'id': 'a342781',
            'ext': 'mp3',
            'duration': 1823,
            'title': '#138 Nepilnīgā kompensējamo zāļu sistēma pat mēnešiem dzenā pacientus pa aptiekām',
            'thumbnail': 'https://pic.latvijasradio.lv/public/assets/media/9/d/gallery_fd4675ac.jpg',
        },
    }, {
        'url': 'https://radioteatris.lsm.lv/lv/embed/?id=&show=1270&theme=white&size=16x9',
        'info_dict': {
            'id': '1270',
        },
        'playlist_count': 3,
        'playlist': [{
            'md5': '2e61b6eceff00d14d57fdbbe6ab24cac',
            'info_dict': {
                'id': 'a297397',
                'ext': 'mp3',
                'title': 'Eriks Emanuels Šmits "Pilāta evaņģēlijs". 1. daļa',
                'thumbnail': 'https://radioteatris.lsm.lv/public/assets/shows/62f131ae81e3c.jpg',
                'duration': 3300,
            },
        }],
    }, {
        'url': 'https://radioteatris.lsm.lv/lv/embed/?id=&show=1269&theme=white&size=16x9',
        'md5': '24810d4a961da2295d9860afdcaf4f5a',
        'info_dict': {
            'id': 'a230690',
            'ext': 'mp3',
            'title': 'Jens Ahlboms "Spārni". Radioizrāde ar Mārtiņa Freimaņa mūziku',
            'thumbnail': 'https://radioteatris.lsm.lv/public/assets/shows/62f13023a457c.jpg',
            'duration': 1788,
        },
    }, {
        'url': 'https://lr1.lsm.lv/lv/embed/?id=166557&show=0&theme=white&size=16x9',
        'info_dict': {
            'id': '166557',
        },
        'playlist_count': 2,
        'playlist': [{
            'md5': '6a8b0927572f443f09c6e50a3ad65f2d',
            'info_dict': {
                'id': 'a303104',
                'ext': 'mp3',
                'thumbnail': 'https://pic.latvijasradio.lv/public/assets/media/c/5/gallery_a83ad2c2.jpg',
                'title': 'Krustpunktā Lielā intervija: Valsts prezidents Egils Levits',
                'duration': 3222,
            },
        }, {
            'md5': '5d5e191e718b7644e5118b7b4e093a6d',
            'info_dict': {
                'id': 'v303104',
                'ext': 'mp4',
                'thumbnail': 'https://pic.latvijasradio.lv/public/assets/media/c/5/gallery_a83ad2c2.jpg',
                'title': 'Krustpunktā Lielā intervija: Valsts prezidents Egils Levits - Video Version',
                'duration': 3222,
            },
        }],
    }, {
        'url': 'https://lr1.lsm.lv/lv/embed/?id=183522&show=0&theme=white&size=16x9',
        'only_matching': True,
    }, {
        'url': 'https://lr2.lsm.lv/lv/embed/?id=182126&show=0&theme=white&size=16x9',
        'only_matching': True,
    }, {
        'url': 'https://klasika.lsm.lv/lv/embed/?id=110806&show=0&theme=white&size=16x9',
        'only_matching': True,
    }, {
        'url': 'https://lr4.lsm.lv/lv/embed/?id=184282&show=0&theme=white&size=16x9',
        'only_matching': True,
    }, {
        'url': 'https://pieci.lv/lv/embed/?id=168896&show=0&theme=white&size=16x9',
        'only_matching': True,
    }, {
        'url': 'https://naba.lsm.lv/lv/embed/?id=182901&show=0&theme=white&size=16x9',
        'only_matching': True,
    }, {
        'url': 'https://radioteatris.lsm.lv/lv/embed/?id=176439&show=0&theme=white&size=16x9',
        'only_matching': True,
    }, {
        'url': 'https://lr1.lsm.lv/lv/pleijeris/?embed=0&id=48205&time=00%3A00&idx=0',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        query = parse_qs(url)
        video_id = traverse_obj(query, (
            ('show', 'id'), 0, {int_or_none}, filter, {str_or_none}), get_all=False)
        webpage = self._download_webpage(url, video_id)

        player_data, media_data = self._search_regex(
            r'LR\.audio\.Player\s*\([^{]*(?P<player>\{.*?\}),(?P<media>\{.*\})\);',
            webpage, 'player json', group=('player', 'media'))

        player_json = self._parse_json(
            player_data, video_id, transform_source=js_to_json, fatal=False) or {}
        media_json = self._parse_json(media_data, video_id, transform_source=js_to_json)

        entries = []
        for item in traverse_obj(media_json, (('audio', 'video'), lambda _, v: v['id'])):
            formats = []
            for source_url in traverse_obj(item, ('sources', ..., 'file', {url_or_none})):
                if determine_ext(source_url) == 'm3u8':
                    formats.extend(self._extract_m3u8_formats(source_url, video_id, fatal=False))
                else:
                    formats.append({'url': source_url})

            id_ = item['id']
            title = item.get('title')
            if id_.startswith('v') and not title:
                title = traverse_obj(
                    media_json, ('audio', lambda _, v: v['id'][1:] == id_[1:], 'title',
                                 {lambda x: x and f'{x} - Video Version'}), get_all=False)

            entries.append({
                'formats': formats,
                'thumbnail': urljoin(url, player_json.get('poster')),
                'id': id_,
                'title': title,
                'duration': traverse_obj(item, ('duration', {int_or_none})),
            })

        if len(entries) == 1:
            return entries[0]

        return self.playlist_result(entries, video_id)


class LSMLTVEmbedIE(InfoExtractor):
    _VALID_URL = r'https?://ltv\.lsm\.lv/embed\?(?:[^#]+&)?c=(?P<id>[^#&]+)'
    _TESTS = [{
        'url': 'https://ltv.lsm.lv/embed?c=eyJpdiI6IjQzbHVUeHAyaDJiamFjcjdSUUFKdnc9PSIsInZhbHVlIjoiMHl3SnJNRmd2TmFIdnZwOGtGUUpzODFzUEZ4SVVsN2xoRjliSW9vckUyMWZIWG8vbWVzaFFkY0lhNmRjbjRpaCIsIm1hYyI6ImMzNjdhMzFhNTFhZmY1ZmE0NWI5YmFjZGI1YmJiNGEyNjgzNDM4MjUzMWEwM2FmMDMyZDMwYWM1MDFjZmM5MGIiLCJ0YWciOiIifQ==',
        'md5': '64f72a360ca530d5ed89c77646c9eee5',
        'info_dict': {
            'id': '46k_d23-6000-105',
            'ext': 'mp4',
            'timestamp': 1700589151,
            'duration': 1442,
            'upload_date': '20231121',
            'title': 'D23-6000-105_cetstud',
            'thumbnail': 'https://store.cloudycdn.services/tmsp00060/assets/media/660858/placeholder1700589200.jpg',
        },
    }, {
        'url': 'https://ltv.lsm.lv/embed?enablesdkjs=1&c=eyJpdiI6IncwVzZmUFk2MU12enVWK1I3SUcwQ1E9PSIsInZhbHVlIjoid3FhV29vamc3T2sxL1RaRmJ5Rm1GTXozU0o2dVczdUtLK0cwZEZJMDQ2a3ZIRG5DK2pneGlnbktBQy9uazVleHN6VXhxdWIweWNvcHRDSnlISlNYOHlVZ1lpcTUrcWZSTUZPQW14TVdkMW9aOUtRWVNDcFF4eWpHNGcrT0VZbUNFQStKQk91cGpndW9FVjJIa0lpbkh3PT0iLCJtYWMiOiIyZGI1NDJlMWRlM2QyMGNhOGEwYTM2MmNlN2JlOGRhY2QyYjdkMmEzN2RlOTEzYTVkNzI1ODlhZDlhZjU4MjQ2IiwidGFnIjoiIn0=',
        'md5': 'a1711e190fe680fdb68fd8413b378e87',
        'info_dict': {
            'id': 'wUnFArIPDSY',
            'ext': 'mp4',
            'uploader': 'LTV_16plus',
            'release_date': '20220514',
            'channel_url': 'https://www.youtube.com/channel/UCNMrnafwXD2XKeeQOyfkFCw',
            'view_count': int,
            'availability': 'public',
            'thumbnail': 'https://i.ytimg.com/vi/wUnFArIPDSY/maxresdefault.jpg',
            'release_timestamp': 1652544074,
            'title': 'EIROVĪZIJA SALĀTOS',
            'live_status': 'was_live',
            'uploader_id': '@LTV16plus',
            'comment_count': int,
            'channel_id': 'UCNMrnafwXD2XKeeQOyfkFCw',
            'channel_follower_count': int,
            'categories': ['Entertainment'],
            'duration': 5269,
            'upload_date': '20220514',
            'age_limit': 0,
            'channel': 'LTV_16plus',
            'playable_in_embed': True,
            'tags': [],
            'uploader_url': 'https://www.youtube.com/@LTV16plus',
            'like_count': int,
            'description': 'md5:7ff0c42ba971e3c13e4b8a2ff03b70b5',
        },
    }]

    def _real_extract(self, url):
        video_id = urllib.parse.unquote(self._match_id(url))
        webpage = self._download_webpage(url, video_id)
        data = self._search_json(
            r'window\.ltvEmbedPayload\s*=', webpage, 'embed json', video_id)
        embed_type = traverse_obj(data, ('source', 'name', {str}))

        if embed_type == 'telia':
            ie_key = 'CloudyCDN'
            embed_url = traverse_obj(data, ('source', 'embed_url', {url_or_none}))
        elif embed_type == 'youtube':
            ie_key = 'Youtube'
            embed_url = traverse_obj(data, ('source', 'id', {str}))
        else:
            raise ExtractorError(f'Unsupported embed type {embed_type!r}')

        return self.url_result(
            embed_url, ie_key, video_id, **traverse_obj(data, {
                'title': ('parentInfo', 'title'),
                'duration': ('parentInfo', 'duration', {int_or_none}),
                'thumbnail': ('source', 'poster', {url_or_none}),
            }))


class LSMReplayIE(InfoExtractor):
    _VALID_URL = r'https?://replay\.lsm\.lv/[^/?#]+/(?:ieraksts|statja)/[^/?#]+/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://replay.lsm.lv/lv/ieraksts/ltv/311130/4-studija-zolitudes-tragedija-un-incupes-stacija',
        'md5': '64f72a360ca530d5ed89c77646c9eee5',
        'info_dict': {
            'id': '46k_d23-6000-105',
            'ext': 'mp4',
            'timestamp': 1700586300,
            'description': 'md5:0f1b14798cc39e1ae578bd0eb268f759',
            'duration': 1442,
            'upload_date': '20231121',
            'title': '4. studija. Zolitūdes traģēdija un Inčupes stacija',
            'thumbnail': 'https://ltv.lsm.lv/storage/media/8/7/large/5/1f9604e1.jpg',
        },
    }, {
        'url': 'https://replay.lsm.lv/lv/ieraksts/lr/183522/138-nepilniga-kompensejamo-zalu-sistema-pat-menesiem-dzena-pacientus-pa-aptiekam',
        'md5': '719b33875cd1429846eeeaeec6df2830',
        'info_dict': {
            'id': 'a342781',
            'ext': 'mp3',
            'duration': 1823,
            'title': '#138 Nepilnīgā kompensējamo zāļu sistēma pat mēnešiem dzenā pacientus pa aptiekām',
            'thumbnail': 'https://pic.latvijasradio.lv/public/assets/media/9/d/large_fd4675ac.jpg',
            'upload_date': '20231102',
            'timestamp': 1698921060,
            'description': 'md5:7bac3b2dd41e44325032943251c357b1',
        },
    }, {
        'url': 'https://replay.lsm.lv/ru/statja/ltv/311130/4-studija-zolitudes-tragedija-un-incupes-stacija',
        'only_matching': True,
    }]

    def _fix_nuxt_data(self, webpage):
        return re.sub(r'Object\.create\(null(?:,(\{.+\}))?\)', lambda m: m.group(1) or 'null', webpage)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        data = self._search_nuxt_data(
            self._fix_nuxt_data(webpage), video_id, context_name='__REPLAY__')

        return {
            '_type': 'url_transparent',
            'id': video_id,
            **traverse_obj(data, {
                'url': ('playback', 'service', 'url', {url_or_none}),
                'title': ('mediaItem', 'title'),
                'description': ('mediaItem', ('lead', 'body')),
                'duration': ('mediaItem', 'duration', {int_or_none}),
                'timestamp': ('mediaItem', 'aired_at', {parse_iso8601}),
                'thumbnail': ('mediaItem', 'largeThumbnail', {url_or_none}),
            }, get_all=False),
        }
