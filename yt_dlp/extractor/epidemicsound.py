from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    orderedSet,
    parse_iso8601,
    parse_qs,
    parse_resolution,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class EpidemicSoundIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?epidemicsound\.com/track/(?P<id>[0-9a-zA-Z]+)'
    _TESTS = [{
        'url': 'https://www.epidemicsound.com/track/yFfQVRpSPz/',
        'md5': 'd98ff2ddb49e8acab9716541cbc9dfac',
        'info_dict': {
            'id': '45014',
            'display_id': 'yFfQVRpSPz',
            'ext': 'mp3',
            'title': 'Door Knock Door 1',
            'alt_title': 'Door Knock Door 1',
            'tags': ['foley', 'door', 'knock', 'glass', 'window', 'glass door knock'],
            'categories': ['Misc. Door'],
            'duration': 1,
            'thumbnail': 'https://cdn.epidemicsound.com/curation-assets/commercial-release-cover-images/default-sfx/3000x3000.jpg',
            'timestamp': 1415320353,
            'upload_date': '20141107',
        },
    }, {
        'url': 'https://www.epidemicsound.com/track/mj8GTTwsZd/',
        'md5': 'c82b745890f9baf18dc2f8d568ee3830',
        'info_dict': {
            'id': '148700',
            'display_id': 'mj8GTTwsZd',
            'ext': 'mp3',
            'title': 'Noplace',
            'tags': ['liquid drum n bass', 'energetic'],
            'categories': ['drum and bass'],
            'duration': 237,
            'timestamp': 1694426482,
            'thumbnail': 'https://cdn.epidemicsound.com/curation-assets/commercial-release-cover-images/11138/3000x3000.jpg',
            'upload_date': '20230911',
            'release_timestamp': 1700535606,
            'release_date': '20231121',
        },
    }]

    @staticmethod
    def _epidemic_parse_thumbnail(url: str):
        if not url_or_none(url):
            return None

        return {
            'url': url,
            **(traverse_obj(url, ({parse_qs}, {
                'width': ('width', 0, {int_or_none}),
                'height': ('height', 0, {int_or_none}),
            })) or parse_resolution(url)),
        }

    @staticmethod
    def _epidemic_fmt_or_none(f):
        if not f.get('format'):
            f['format'] = f.get('format_id')
        elif not f.get('format_id'):
            f['format_id'] = f['format']
        if not f['url'] or not f['format']:
            return None
        if f.get('format_note'):
            f['format_note'] = f'track ID {f["format_note"]}'
        if f['format'] != 'full':
            f['preference'] = -2
        return f

    def _real_extract(self, url):
        video_id = self._match_id(url)
        json_data = self._download_json(f'https://www.epidemicsound.com/json/track/{video_id}', video_id)

        thumbnails = traverse_obj(json_data, [('imageUrl', 'cover')])
        thumb_base_url = traverse_obj(json_data, ('coverArt', 'baseUrl', {url_or_none}))
        if thumb_base_url:
            thumbnails.extend(traverse_obj(json_data, (
                'coverArt', 'sizes', ..., {thumb_base_url.__add__})))

        return traverse_obj(json_data, {
            'id': ('id', {str_or_none}),
            'display_id': ('publicSlug', {str}),
            'title': ('title', {str}),
            'alt_title': ('oldTitle', {str}),
            'duration': ('length', {float_or_none}),
            'timestamp': ('added', {parse_iso8601}),
            'release_timestamp': ('releaseDate', {parse_iso8601}),
            'categories': ('genres', ..., 'tag', {str}),
            'tags': ('metadataTags', ..., {str}),
            'age_limit': ('isExplicit', {lambda b: 18 if b else None}),
            'thumbnails': ({lambda _: thumbnails}, {orderedSet}, ..., {self._epidemic_parse_thumbnail}),
            'formats': ('stems', {dict.items}, ..., {
                'format': (0, {str_or_none}),
                'format_note': (1, 's3TrackId', {str_or_none}),
                'format_id': (1, 'stemType', {str}),
                'url': (1, 'lqMp3Url', {url_or_none}),
            }, {self._epidemic_fmt_or_none}),
        })
