from .common import InfoExtractor
from .kaltura import KalturaIE
from ..utils import (
    int_or_none,
    str_or_none,
    url_or_none,
    traverse_obj
)


class YleAreenaIE(InfoExtractor):
    _VALID_URL = r'https?://areena\.yle\.fi/(?P<id>[\d-]+)'
    _TESTS = [{
        'url': 'https://areena.yle.fi/1-4371942',
        'md5': '932edda0ecf5dfd6423804182d32f8ac',
        'info_dict': {
            'id': '0_a3tjk92c',
            'ext': 'mp4',
            'title': 'Pouchit',
            'description': 'md5:d487309c3abbe5650265bbd1742d2f82',
            'series': 'Modernit miehet',
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 2',
            'episode_number': 2,
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader_id': 'ovp@yle.fi',
            'duration': 1435,
            'view_count': int,
            'upload_date': '20181204',
            'timestamp': 1543916210,
            'subtitles': {'fin': [{'url': r're:^https?://.*$', 'ext': 'unknown_video'}]},
            'age_limit': 7,
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video_data = self._download_json(
            f'https://player.api.yle.fi/v1/preview/{video_id}.json?app_id=player_static_prod&app_key=8930d72170e48303cf5f3867780d549b',
            video_id)
        kaltura_id = traverse_obj(video_data, ('data', 'ongoing_ondemand', 'kaltura', 'id'))

        webpage = self._download_webpage(url, video_id)
        info = self._search_json_ld(webpage, video_id, default={})
        raw_title = info.get('title') or ''
        # raw_title example:'K1, J2: Pouchit | Modernit miehet',
        _RAW_TITLE_RE = r'K(?P<season_number>[\d]+), J(?P<episode_number>[\d]+): (?P<episode_title>[^|]*) | (?P<series_title>.*)$'

        title = (
            traverse_obj(video_data, ('data', 'ongoing_ondemand', 'title', 'fin'), expected_type=str_or_none)
            or str_or_none(self._search_regex(_RAW_TITLE_RE, raw_title, 'episode_title', fatal=False, group='episode_title'))
            or raw_title or '')

        description = traverse_obj(video_data, ('data', 'ongoing_ondemand', 'description', 'fin'), expected_type=str_or_none)

        series = (
            traverse_obj(video_data, ('data', 'ongoing_ondemand', 'series', 'title', 'fin'), expected_type=str_or_none)
            or str_or_none(self._search_regex(_RAW_TITLE_RE, raw_title, 'series_title', fatal=False, group='series_title')))

        season_number = (
            int_or_none(self._search_regex(r'Kausi (?P<season_number>[\d]+)', description, 'season_number', fatal=False, group='season_number'))
            or int_or_none(self._search_regex(_RAW_TITLE_RE, raw_title, 'season_number', fatal=False, group='season_number')))

        episode_number = (
            traverse_obj(video_data, ('data', 'ongoing_ondemand', 'episode_number'), expected_type=int_or_none)
            or int_or_none(self._search_regex(_RAW_TITLE_RE, raw_title, 'episode_number', fatal=False, group='episode_number')))

        subtitles = {}
        subtitles_data = traverse_obj(video_data, ('data', 'ongoing_ondemand', 'subtitles', ...), list)
        for subtitles_track in subtitles_data:
            subtitles_language = subtitles_track.get('language')
            subtitles_url = url_or_none(subtitles_track.get('uri'))
            if subtitles_url is None:
                continue
            if subtitles_language in subtitles:
                subtitles[subtitles_language].append({'url': subtitles_url})
                continue
            subtitles[subtitles_language] = [{'url': subtitles_url}]

        return {
            '_type': 'url_transparent',
            'url': f'kaltura:1955031:{kaltura_id}',
            'ie_key': KalturaIE.ie_key(),
            'title': title,
            'description': description,
            'series': series,
            'season_number': season_number,
            'episode_number': episode_number,
            'thumbnail': False,
            'thumbnails': traverse_obj(info, ('thumbnails', ..., {'url': 'url'})),
            'subtitles': subtitles,
            'age_limit': traverse_obj(video_data, ('data', 'ongoing_ondemand', 'content_rating', 'age_restriction'), expected_type=int_or_none),
        }
