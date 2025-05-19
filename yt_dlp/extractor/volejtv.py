from .common import InfoExtractor
from ..utils import (
    str_or_none,
    strftime_or_none,
    traverse_obj,
    unified_timestamp,
    url_or_none,
)


class VolejTVIE(InfoExtractor):
    _VALID_URL = r'https?://volej\.tv/match/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://volej.tv/match/270579',
        'info_dict': {
            'id': '270579',
            'ext': 'mp4',
            'title': 'CZE-SWE (2024-06-16)',
            'categories': ['ženy'],
            'series': 'ZLATÁ EVROPSKÁ VOLEJBALOVÁ LIGA',
            'season': '2023-2024',
            'timestamp': 1718553600,
            'upload_date': '20240616',
        },
    }, {
        'url': 'https://volej.tv/match/487520',
        'info_dict': {
            'id': '487520',
            'ext': 'mp4',
            'thumbnail': r're:https://.+\.(png|jpeg)',
            'title': 'CZE-FRA (2024-09-06)',
            'categories': ['mládež'],
            'series': 'Mistrovství Evropy do 20 let',
            'season': '2024-2025',
            'timestamp': 1725627600,
            'upload_date': '20240906',

        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        json_data = self._download_json(f'https://api-volejtv-prod.apps.okd4.devopsie.cloud/api/match/{video_id}', video_id)
        formats = []
        tbr_resolution_mapping = {'6000': '1080p', '2400': '720p', '1500': '480p', '800': '360p'}
        for video in traverse_obj(json_data, ('videos', 0, 'qualities')):
            formats.append({
                'url': video['cloud_front_path'],
                'tbr': int(video['quality']),
                'format_id': str(video['id']),
                'format_note': tbr_resolution_mapping[video['quality']],
            })
        data = {
            'id': video_id,
            **traverse_obj(json_data, {
                'series': ('competition_name', {str_or_none}),
                'season': ('season', {str_or_none}),
                'timestamp': ('match_time', {unified_timestamp}),
                'categories': ('category', ('title'), {str}, filter, all, filter),
                'thumbnail': ('poster', {url_or_none}),
            }),
            'formats': formats,
        }
        teams = list(set(traverse_obj(json_data, ('teams', ..., 'shortcut'))))
        if len(teams) > 2 and 'FIN' in teams:
            teams.remove('FIN')
        title = '-'.join(sorted(teams))
        if data.get('timestamp'):
            title += f" ({strftime_or_none(data['timestamp'], '%Y-%m-%d')})"
        data['title'] = title
        return data
