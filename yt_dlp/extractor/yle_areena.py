from .common import InfoExtractor
from .kaltura import KalturaIE
from ..utils import (
    int_or_none,
    smuggle_url,
    traverse_obj,
    unified_strdate,
    url_or_none,
)


class YleAreenaIE(InfoExtractor):
    _VALID_URL = r'https?://areena\.yle\.fi/(?P<id>[\d-]+)'
    _TESTS = [
        {
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
                'release_date': '20190106',
                'timestamp': 1543916210,
                'subtitles': {'fin': [{'url': r're:^https?://', 'ext': 'srt'}]},
                'age_limit': 7,
                'webpage_url': 'https://areena.yle.fi/1-4371942'
            }
        },
        {
            'url': 'https://areena.yle.fi/1-2158940',
            'md5': 'cecb603661004e36af8c5188b5212b12',
            'info_dict': {
                'id': '1_l38iz9ur',
                'ext': 'mp4',
                'title': 'Albi haluaa vessan',
                'description': 'md5:15236d810c837bed861fae0e88663c33',
                'series': 'Albi Lumiukko',
                'season': None,
                'season_number': None,
                'episode': None,
                'episode_number': None,
                'thumbnail': 'http://cfvod.kaltura.com/p/1955031/sp/195503100/thumbnail/entry_id/1_l38iz9ur/version/100021',
                'uploader_id': 'ovp@yle.fi',
                'duration': 319,
                'view_count': int,
                'upload_date': '20211202',
                'release_date': '20211215',
                'timestamp': 1638448202,
                'subtitles': {},
                'age_limit': 0,
                'webpage_url': 'https://areena.yle.fi/1-2158940'
            }
        }
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        info = self._search_json_ld(self._download_webpage(url, video_id), video_id, default={})
        video_data = self._download_json(
            f'https://player.api.yle.fi/v1/preview/{video_id}.json?app_id=player_static_prod&app_key=8930d72170e48303cf5f3867780d549b',
            video_id, headers={
                'origin': 'https://areena.yle.fi',
                'referer': 'https://areena.yle.fi/',
                'content-type': 'application/json'
            })

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
            'url': smuggle_url(
                f'kaltura:1955031:{video_data["data"]["ongoing_ondemand"]["kaltura"]["id"]}',
                {'source_url': url}),
            'ie_key': KalturaIE.ie_key(),
            'title': (traverse_obj(video_data, ('data', 'ongoing_ondemand', 'title', 'fin'), expected_type=str)
                      or episode or info.get('title')),
            'description': description,
            'series': (traverse_obj(video_data, ('data', 'ongoing_ondemand', 'series', 'title', 'fin'), expected_type=str)
                       or series),
            'season_number': (int_or_none(self._search_regex(r'Kausi (\d+)', description, 'season number', default=None))
                              or int_or_none(season_number)),
            'episode_number': (traverse_obj(video_data, ('data', 'ongoing_ondemand', 'episode_number'), expected_type=int_or_none)
                               or int_or_none(episode_number)),
            'thumbnails': traverse_obj(info, ('thumbnails', ..., {'url': 'url'})),
            'age_limit': traverse_obj(video_data, ('data', 'ongoing_ondemand', 'content_rating', 'age_restriction'), expected_type=int_or_none),
            'subtitles': subtitles,
            'release_date': unified_strdate(traverse_obj(video_data, ('data', 'ongoing_ondemand', 'start_time'), expected_type=str)),
        }
