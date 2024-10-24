import functools
import re
import uuid

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    float_or_none,
    int_or_none,
    join_nonempty,
    parse_age_limit,
    parse_qs,
    str_or_none,
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
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)',
            'duration': 5486.955,
            'release_date': '20220924',
            'series': 'Ask Us Anything',
            'series_id': '11790',
            'episode_number': 351,
            'episode': 'Jung Sung-ho, Park Seul-gi, Kim Bo-min, Yang Seung-won',
        },
    }, {
        'url': 'https://www.ondemandkorea.com/player/vod/breakup-probation-a-week?contentId=1595796',
        'md5': '57266c720006962be7ff415b24775caa',
        'info_dict': {
            'id': '1595796',
            'ext': 'mp4',
            'title': 'Breakup Probation, A Week: E08',
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)',
            'duration': 1586.0,
            'release_date': '20231001',
            'series': 'Breakup Probation, A Week',
            'series_id': '22912',
            'episode_number': 8,
            'episode': 'E08',
        },
    }, {
        'url': 'https://www.ondemandkorea.com/player/vod/the-outlaws?contentId=369531',
        'md5': 'fa5523b87aa1f6d74fc622a97f2b47cd',
        'info_dict': {
            'id': '369531',
            'ext': 'mp4',
            'release_date': '20220519',
            'duration': 7267.0,
            'title': 'The Outlaws: Main Movie',
            'thumbnail': r're:^https?://.*\.(jpg|jpeg|png)',
            'age_limit': 18,
        },
    }, {
        'url': 'https://www.ondemandkorea.com/en/player/vod/capture-the-moment-how-is-that-possible?contentId=1605006',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        data = self._download_json(
            f'https://odkmedia.io/odx/api/v3/playback/{video_id}/', video_id, fatal=False,
            headers={'service-name': 'odk'}, query={'did': str(uuid.uuid4())}, expected_status=(403, 404))
        if not traverse_obj(data, ('result', {dict})):
            msg = traverse_obj(data, ('messages', '__default'), 'title', expected_type=str)
            raise ExtractorError(msg or 'Got empty response from playback API', expected=True)

        data = data['result']

        def try_geo_bypass(url):
            return traverse_obj(url, ({parse_qs}, 'stream_url', 0, {url_or_none})) or url

        formats = []
        for m3u8_url in traverse_obj(data, (('sources', 'manifest'), ..., 'url', {url_or_none}, {try_geo_bypass})):
            mod_url = re.sub(r'_720(p?)\.m3u8', r'_1080\1.m3u8', m3u8_url)
            if mod_url != m3u8_url:
                mod_format = self._extract_m3u8_formats(
                    mod_url, video_id, note='Checking for higher quality format',
                    errnote='No higher quality format found', fatal=False)
                if mod_format:
                    formats.extend(mod_format)
                    continue
            formats.extend(self._extract_m3u8_formats(m3u8_url, video_id, fatal=False))

        subtitles = {}
        for track in traverse_obj(data, ('text_tracks', lambda _, v: url_or_none(v['url']))):
            subtitles.setdefault(track.get('language', 'und'), []).append({
                'url': track['url'],
                'ext': track.get('codec'),
                'name': track.get('label'),
            })

        def if_series(key=None):
            return lambda obj: obj[key] if key and obj['kind'] == 'series' else None

        return {
            'id': video_id,
            'title': join_nonempty(
                ('episode', 'program', 'title'),
                ('episode', 'title'), from_dict=data, delim=': '),
            **traverse_obj(data, {
                'thumbnail': ('episode', 'images', 'thumbnail', {url_or_none}),
                'release_date': ('episode', 'release_date', {lambda x: x.replace('-', '')}, {unified_strdate}),
                'duration': ('duration', {functools.partial(float_or_none, scale=1000)}),
                'age_limit': ('age_rating', 'name', {lambda x: x.replace('R', '')}, {parse_age_limit}),
                'series': ('episode', {if_series(key='program')}, 'title'),
                'series_id': ('episode', {if_series(key='program')}, 'id', {str_or_none}),
                'episode': ('episode', {if_series(key='title')}),
                'episode_number': ('episode', {if_series(key='number')}, {int_or_none}),
            }, get_all=False),
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
        'playlist_mincount': 755,
    }, {
        'url': 'https://www.ondemandkorea.com/en/player/vod/the-land',
        'info_dict': {
            'id': 'the-land',
        },
        'playlist_count': 52,
    }]

    _PAGE_SIZE = 100

    def _fetch_page(self, display_id, page):
        page += 1
        page_data = self._download_json(
            f'https://odkmedia.io/odx/api/v3/program/{display_id}/episodes/', display_id,
            headers={'service-name': 'odk'}, query={
                'page': page,
                'page_size': self._PAGE_SIZE,
            }, note=f'Downloading page {page}', expected_status=404)
        for episode in traverse_obj(page_data, ('result', 'results', ...)):
            yield self.url_result(
                f'https://www.ondemandkorea.com/player/vod/{display_id}?contentId={episode["id"]}',
                ie=OnDemandKoreaIE, video_title=episode.get('title'))

    def _real_extract(self, url):
        display_id = self._match_id(url)

        entries = OnDemandPagedList(functools.partial(
            self._fetch_page, display_id), self._PAGE_SIZE)

        return self.playlist_result(entries, display_id)
