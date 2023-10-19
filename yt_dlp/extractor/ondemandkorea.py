import functools
import re

from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    join_nonempty,
    OnDemandPagedList,
    parse_age_limit,
    parse_qs,
    random_uuidv4,
    unified_strdate,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class OnDemandKoreaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ondemandkorea\.com/(?:en/)?player/vod/[a-z0-9-]+\?(?:[^#]+&)?contentId=(?P<id>\d+)'
    _GEO_COUNTRIES = ['US', 'CA']

    _TESTS = [{
        'url': 'https://www.ondemandkorea.com/player/vod/ask-us-anything?contentId=686471',
        'md5': 'e2ff77255d989e3135bde0c5889fbce8',
        'info_dict': {
            'id': '686471',
            'ext': 'mp4',
            'title': 'Ask Us Anything: Jung Sung-ho, Park Seul-gi, Kim Bo-min, Yang Seung-won',
            'thumbnail': 'https://sp.ondemandkorea.com/wp-content/themes/ondemandkorea/uploads/thumbnail/1891035_20220924_1.jpg',
            'duration': 5486.955,
            'release_date': '20220924',
            'series': 'Ask Us Anything',
            'series_id': 11790,
            'episode_number': 351,
            'episode': 'Jung Sung-ho, Park Seul-gi, Kim Bo-min, Yang Seung-won',
        },
    }, {
        'url': 'https://www.ondemandkorea.com/en/player/vod/joint-security-area?contentId=464622',
        'md5': '44e274d2b04977e03fc7f3941fbcb355',
        'info_dict': {
            'id': '464622',
            'ext': 'mp4',
            'title': 'Joint Security Area: Main Movie',
            'thumbnail': 'https://sp.ondemandkorea.com/wp-content/themes/ondemandkorea/uploads/thumbnail/jsa.1080p.4896k_3410.901645.jpg',
            'age_limit': 15,
            'duration': 6525.0,
            'release_date': '20200114',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        data = self._download_json(f'https://odkmedia.io/odx/api/v3/playback/{video_id}/', video_id,
                                   fatal=False, headers={'service-name': 'odk'},
                                   query={'did': random_uuidv4()}, expected_status=(200, 403))
        if not data.get('result'):
            raise ExtractorError(traverse_obj(data, ('messages', '__default'), 'title'), expected=True)

        potential_urls = traverse_obj(data, ('result', 'sources', ..., 'url'), ('result', 'manifests', ..., 'url'))
        # Try to bypass geo-restricted ad proxy
        potential_urls = [
            alt_url if (alt_url := traverse_obj(url, ({parse_qs}, 'stream_url', 0, {url_or_none}))) else url
            for url in potential_urls
        ]
        # Try to upgrade quality
        potential_urls = [
            mod_url if self._request_webpage(
                HEADRequest(mod_url := re.sub(r'_720(p?)\.m3u8', r'_1080\1.m3u8', url)), video_id,
                note='Checking if higher quality format is available', fatal=False) else url
            for url in potential_urls
        ]

        formats = []
        for url in potential_urls:
            formats.extend(self._extract_m3u8_formats(url, video_id, fatal=False))

        subtitles = {}
        for track in traverse_obj(data, ('result', 'text_tracks', lambda _, v: url_or_none(v['url']))):
            subtitles.setdefault(track.get('language', 'und'), []).append({
                'url': track['url'],
                'ext': track.get('codec'),
                'name': track.get('label'),
            })

        return {
            'id': video_id,
            'title': join_nonempty(
                ('result', 'episode', 'program', 'title'),
                ('result', 'episode', 'title'), from_dict=data, delim=': '),
            **traverse_obj(data, ('result', {
                'thumbnail': ('episode', 'images', 'thumbnail', {url_or_none}),
                'release_date': ('episode', 'release_date', {lambda x: x.replace('-', '')}, {unified_strdate}),
                'duration': ('duration', {functools.partial(float_or_none, scale=1000)}),
                'age_limit': ('age_rating', 'name', {lambda x: x.replace('R', '')}, {parse_age_limit}),
                'series': ('episode', {lambda x: x['program'] if x['kind'] == 'series' else None}, 'title'),
                'series_id': ('episode', {lambda x: x['program'] if x['kind'] == 'series' else None}, 'id'),
                'episode': ('episode', {lambda x: x['title'] if x['kind'] == 'series' else None},),
                'episode_number': ('episode', {lambda x: x['number'] if x['kind'] == 'series' else None}, {int_or_none}),
            }), get_all=False),
            'formats': formats,
            'subtitles': subtitles,
        }


class OnDemandKoreaProgramIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ondemandkorea\.com/(?:en/)?player/vod/(?P<id>[a-z0-9-]+)(?:$|#)'
    _GEO_COUNTRIES = ['US', 'CA']

    _TESTS = [{
        'url': 'https://www.ondemandkorea.com/player/vod/uskn-news',
        'info_dict': {
            'id': 'uskn-news',
        },
        'playlist_count': 755,
    }, {
        'url': 'https://www.ondemandkorea.com/en/player/vod/joint-security-area',
        'info_dict': {
            'id': 'joint-security-area',
        },
        'playlist_count': 2,
    }]

    _PAGE_SIZE = 100

    def _fetch_page(self, display_id, page):
        page += 1
        page_data = self._download_json(
            f'https://odkmedia.io/odx/api/v3/program/{display_id}/episodes/', display_id,
            headers={'service-name': 'odk'}, query={
                'page': page,
                'page_size': self._PAGE_SIZE,
            }, note=f'Downloading page {page}')
        for episode in traverse_obj(page_data, ('result', 'results')):
            yield self.url_result(
                f'https://www.ondemandkorea.com/player/vod/{display_id}?contentId={episode["id"]}',
                ie=OnDemandKoreaIE, video_title=episode.get('title')
            )

    def _real_extract(self, url):
        display_id = self._match_id(url)

        entries = OnDemandPagedList(functools.partial(
            self._fetch_page, display_id), self._PAGE_SIZE)

        return self.playlist_result(entries, display_id)
