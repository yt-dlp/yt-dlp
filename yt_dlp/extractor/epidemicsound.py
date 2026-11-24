from .common import InfoExtractor
from ..utils import (
    ExtractorError,
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
    _VALID_URL = r'https?://(?:www\.)?epidemicsound\.com/(?:(?P<tracks>(?:music|sound-effects)/tracks)|track)/(?P<id>[0-9a-zA-Z-]+)'
    _TESTS = [{
        'url': 'https://www.epidemicsound.com/music/tracks/4f6686e3-037e-3f03-a9cd-0855f070b05a/',
        'md5': 'c7881dcd46945e84596f0c61fe72a1b0',
        'info_dict': {
            'id': '98281',
            'display_id': 'mXJkVme0Sl',
            'ext': 'mp3',
            'title': 'Wave Crest',
            'tags': ['corporate', 'sunset', 'water', 'warm', 'chill', 'beaches', 'sun', 'ocean', 'tropical'],
            'categories': ['Electronic', 'Beats'],
            'uploader': 'Gavin Luke',
            'creators': ['Airae'],
            'duration': 167.0,
            'timestamp': 1543928593,
            'upload_date': '20181204',
            'thumbnail': 'https://cdn.epidemicsound.com/curation-assets/commercial-release-cover-images/920/3000x3000.jpg',
        },
    }, {
        'url': 'https://www.epidemicsound.com/music/tracks/b66ce071-c3a0-445c-a5a8-971ef2016596/',
        'md5': 'df722e30d1e4e22ab45f191a90cd98b2',
        'info_dict': {
            'id': '148700',
            'display_id': 'mj8GTTwsZd',
            'ext': 'mp3',
            'title': 'Noplace',
            'tags': ['liquid drum n bass', 'energetic'],
            'categories': ['Drum And Bass'],
            'uploader': 'Jake and Jake',
            'creators': ['Jake and Jake'],
            'duration': 237,
            'timestamp': 1694426482,
            'thumbnail': 'https://cdn.epidemicsound.com/curation-assets/commercial-release-cover-images/11138/3000x3000.jpg',
            'upload_date': '20230911',
            'release_timestamp': 1700535606,
            'release_date': '20231121',
        },
    }, {
        'url': 'https://www.epidemicsound.com/sound-effects/tracks/2f02f54b-9faa-4daf-abac-1cfe9e9cef69/',
        'md5': '7e69cd296165f0b40497a5e02022ae5e',
        'info_dict': {
            'id': '208931',
            'ext': 'mp3',
            'upload_date': '20240516',
            'timestamp': 1715874501,
            'categories': ['Appliance'],
            'display_id': '6b2NXLURPr',
            'duration': 1.0,
            'title': 'Doors, Appliance, Oven, Grill, Door Open, Close 01',
            'thumbnail': 'https://cdn.epidemicsound.com/curation-assets/commercial-release-cover-images/default-sfx/3000x3000.jpg',
        },
    }, {
        'url': 'https://www.epidemicsound.com/track/mj8GTTwsZd/',
        'only_matching': True,
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
        video_id, is_tracks = self._match_valid_url(url).group('id', 'tracks')
        if not is_tracks:
            urlh = self._request_webpage(url, video_id, note='resolving track redirect')
            match = self._match_valid_url(urlh.url)
            if not match:
                raise ExtractorError('this track has been removed or is no longer available', expected=True)
            video_id = match.group('id')

        json_data = self._download_json(
            f'https://www.epidemicsound.com/json/track/kosmos-id/{video_id}', video_id)

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
            'uploader': ('creatives', 'producers', ..., 'name', all, {', '.join}, filter),
            'creators': ('creatives', ('mainArtists', 'featuredArtists'), ..., 'name', {str}, filter),
            'categories': ('genres', ..., 'displayTag', {str}),
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
