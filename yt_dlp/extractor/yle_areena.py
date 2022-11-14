from .common import InfoExtractor
from .kaltura import KalturaIE
from ..utils import int_or_none, traverse_obj, url_or_none


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
            'thumbnail': 'http://cfvod.kaltura.com/p/1955031/sp/195503100/thumbnail/entry_id/0_a3tjk92c/version/100061',
            'uploader_id': 'ovp@yle.fi',
            'duration': 1435,
            'view_count': int,
            'upload_date': '20181204',
            'timestamp': 1543916210,
            'subtitles': {'fin': [{'url': r're:^https?://', 'ext': 'srt'}]},
            'age_limit': 7,
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        info = self._search_json_ld(self._download_webpage(url, video_id), video_id, default={})
        video_data = self._download_json(
            f'https://player.api.yle.fi/v1/preview/{video_id}.json?app_id=player_static_prod&app_key=8930d72170e48303cf5f3867780d549b',
            video_id)

        # Example title: 'K1, J2: Pouchit | Modernit miehet'
        series, season_number, episode_number, episode = self._search_regex(
            r'K(?P<season_no>[\d]+),\s*J(?P<episode_no>[\d]+):?\s*\b(?P<episode>[^|]+)\s*|\s*(?P<series>.+)',
            info.get('title') or '', 'episode metadata', group=('season_no', 'episode_no', 'episode', 'series'),
            default=(None, None, None, None))
        description = traverse_obj(video_data, ('data', 'ongoing_ondemand', 'description', 'fin'), expected_type=str)

        subtitles = {}
        for sub in traverse_obj(video_data, ('data', 'ongoing_ondemand', 'subtitles', ...)):
            if url_or_none(sub.get('uri')):
                subtitles.setdefault(sub.get('language') or 'und', []).append({
                    'url': sub['uri'],
                    'ext': 'srt',
                    'name': sub.get('kind'),
                })

        return {
            '_type': 'url_transparent',
            'url': 'kaltura:1955031:%s' % traverse_obj(video_data, ('data', 'ongoing_ondemand', 'kaltura', 'id')),
            'ie_key': KalturaIE.ie_key(),
            'title': (traverse_obj(video_data, ('data', 'ongoing_ondemand', 'title', 'fin'), expected_type=str)
                      or episode or info.get('title')),
            'description': description,
            'series': (traverse_obj(video_data, ('data', 'ongoing_ondemand', 'series', 'title', 'fin'), expected_type=str)
                       or series),
            'season_number': (int_or_none(self._search_regex(r'Kausi (\d+)', description, 'season number', default=None))
                              or int(season_number)),
            'episode_number': (traverse_obj(video_data, ('data', 'ongoing_ondemand', 'episode_number'), expected_type=int_or_none)
                               or int(episode_number)),
            'thumbnails': traverse_obj(info, ('thumbnails', ..., {'url': 'url'})),
            'age_limit': traverse_obj(video_data, ('data', 'ongoing_ondemand', 'content_rating', 'age_restriction'), expected_type=int_or_none),
            'subtitles': subtitles,
        }
