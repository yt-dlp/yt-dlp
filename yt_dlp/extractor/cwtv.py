from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_age_limit,
    parse_iso8601,
    smuggle_url,
    str_or_none,
    update_url_query,
)
from ..utils.traversal import traverse_obj


class CWTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?cw(?:tv(?:pr)?|seed)\.com/(?:shows/)?(?:[^/]+/)+[^?]*\?.*\b(?:play|watch)=(?P<id>[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12})'
    _TESTS = [{
        'url': 'https://www.cwtv.com/shows/continuum/a-stitch-in-time/?play=9149a1e1-4cb2-46d7-81b2-47d35bbd332b',
        'info_dict': {
            'id': '9149a1e1-4cb2-46d7-81b2-47d35bbd332b',
            'ext': 'mp4',
            'title': 'A Stitch in Time',
            'description': r're:(?s)City Protective Services officer Kiera Cameron is transported from 2077.+',
            'thumbnail': r're:https?://.+\.jpe?g',
            'duration': 2632,
            'timestamp': 1736928000,
            'uploader': 'CWTV',
            'chapters': 'count:5',
            'series': 'Continuum',
            'season_number': 1,
            'episode_number': 1,
            'age_limit': 14,
            'upload_date': '20250115',
            'season': 'Season 1',
            'episode': 'Episode 1',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'http://cwtv.com/shows/arrow/legends-of-yesterday/?play=6b15e985-9345-4f60-baf8-56e96be57c63',
        'info_dict': {
            'id': '6b15e985-9345-4f60-baf8-56e96be57c63',
            'ext': 'mp4',
            'title': 'Legends of Yesterday',
            'description': r're:(?s)Oliver and Barry Allen take Kendra Saunders and Carter Hall to a remote.+',
            'duration': 2665,
            'series': 'Arrow',
            'season_number': 4,
            'season': '4',
            'episode_number': 8,
            'upload_date': '20151203',
            'timestamp': 1449122100,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'skip': 'redirect to http://cwtv.com/shows/arrow/',
    }, {
        'url': 'http://www.cwseed.com/shows/whose-line-is-it-anyway/jeff-davis-4/?play=24282b12-ead2-42f2-95ad-26770c2c6088',
        'info_dict': {
            'id': '24282b12-ead2-42f2-95ad-26770c2c6088',
            'ext': 'mp4',
            'title': 'Jeff Davis 4',
            'description': 'Jeff Davis is back to make you laugh.',
            'duration': 1263,
            'series': 'Whose Line Is It Anyway?',
            'season_number': 11,
            'episode_number': 20,
            'upload_date': '20151006',
            'timestamp': 1444107300,
            'age_limit': 14,
            'uploader': 'CWTV',
            'thumbnail': r're:https?://.+\.jpe?g',
            'chapters': 'count:4',
            'episode': 'Episode 20',
            'season': 'Season 11',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'http://cwtv.com/thecw/chroniclesofcisco/?play=8adebe35-f447-465f-ab52-e863506ff6d6',
        'only_matching': True,
    }, {
        'url': 'http://cwtvpr.com/the-cw/video?watch=9eee3f60-ef4e-440b-b3b2-49428ac9c54e',
        'only_matching': True,
    }, {
        'url': 'http://cwtv.com/shows/arrow/legends-of-yesterday/?watch=6b15e985-9345-4f60-baf8-56e96be57c63',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._download_json(
            f'https://images.cwtv.com/feed/app-2/video-meta/apiversion_22/device_android/guid_{video_id}', video_id)
        if traverse_obj(data, 'result') != 'ok':
            raise ExtractorError(traverse_obj(data, (('error_msg', 'msg'), {str}, any)), expected=True)
        video_data = data['video']
        title = video_data['title']
        mpx_url = update_url_query(
            video_data.get('mpx_url') or f'https://link.theplatform.com/s/cwtv/media/guid/2703454149/{video_id}',
            {'formats': 'M3U+none'})

        season = str_or_none(video_data.get('season'))
        episode = str_or_none(video_data.get('episode'))
        if episode and season:
            episode = episode[len(season):]

        return {
            '_type': 'url_transparent',
            'id': video_id,
            'title': title,
            'url': smuggle_url(mpx_url, {'force_smil_url': True}),
            'description': video_data.get('description_long'),
            'duration': int_or_none(video_data.get('duration_secs')),
            'series': video_data.get('series_name'),
            'season_number': int_or_none(season),
            'episode_number': int_or_none(episode),
            'timestamp': parse_iso8601(video_data.get('start_time')),
            'age_limit': parse_age_limit(video_data.get('rating')),
            'ie_key': 'ThePlatform',
            'thumbnail': video_data.get('large_thumbnail'),
        }
