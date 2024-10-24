from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    parse_age_limit,
    traverse_obj,
    unified_timestamp,
    url_or_none,
)


class WeyyakIE(InfoExtractor):
    _VALID_URL = r'https?://weyyak\.com/(?P<lang>\w+)/(?:player/)?(?P<type>episode|movie)/(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'https://weyyak.com/en/player/episode/1341952/Ribat-Al-Hob-Episode49',
            'md5': '0caf55c1a615531c8fe60f146ae46849',
            'info_dict': {
                'id': '1341952',
                'ext': 'mp4',
                'title': 'Ribat Al Hob',
                'duration': 2771,
                'alt_title': 'رباط الحب',
                'season': 'Season 1',
                'season_number': 1,
                'episode': 'Episode 49',
                'episode_number': 49,
                'timestamp': 1485907200,
                'upload_date': '20170201',
                'thumbnail': r're:^https://content\.weyyak\.com/.+/poster-image',
                'categories': ['Drama', 'Thrillers', 'Romance'],
                'tags': 'count:8',
            },
        },
        {
            'url': 'https://weyyak.com/en/movie/233255/8-Seconds',
            'md5': 'fe740ae0f63e4d1c8a7fc147a410c564',
            'info_dict': {
                'id': '233255',
                'ext': 'mp4',
                'title': '8 Seconds',
                'duration': 6490,
                'alt_title': '8 ثواني',
                'description': 'md5:45b83a155c30b49950624c7e99600b9d',
                'age_limit': 15,
                'release_year': 2015,
                'timestamp': 1683106031,
                'upload_date': '20230503',
                'thumbnail': r're:^https://content\.weyyak\.com/.+/poster-image',
                'categories': ['Drama', 'Social'],
                'cast': ['Ceylin Adiyaman', 'Esra Inal'],
            },
        },
    ]

    def _real_extract(self, url):
        video_id, lang, type_ = self._match_valid_url(url).group('id', 'lang', 'type')

        path = 'episode/' if type_ == 'episode' else 'contents/moviedetails?contentkey='
        data = self._download_json(
            f'https://msapifo-prod-me.weyyak.z5.com/v1/{lang}/{path}{video_id}', video_id)['data']
        m3u8_url = self._download_json(
            f'https://api-weyyak.akamaized.net/get_info/{data["video_id"]}',
            video_id, 'Extracting video details')['url_video']
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, video_id)

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(data, {
                'title': ('title', {str}),
                'alt_title': ('translated_title', {str}),
                'description': ('synopsis', {str}),
                'duration': ('length', {float_or_none}),
                'age_limit': ('age_rating', {parse_age_limit}),
                'season_number': ('season_number', {int_or_none}),
                'episode_number': ('episode_number', {int_or_none}),
                'thumbnail': ('imagery', 'thumbnail', {url_or_none}),
                'categories': ('genres', ..., {str}),
                'tags': ('tags', ..., {str}),
                'cast': (('main_actor', 'main_actress'), {str}),
                'timestamp': ('insertedAt', {unified_timestamp}),
                'release_year': ('production_year', {int_or_none}),
            }),
        }
