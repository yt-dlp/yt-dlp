import functools

from .common import InfoExtractor
from ..utils import (
    InAdvancePagedList,
    str_or_none,
    strftime_or_none,
    traverse_obj,
    unified_timestamp,
    url_or_none,
)


class VolejTVBaseIE(InfoExtractor):
    _API_URL = 'https://api-volejtv-prod.apps.okd4.devopsie.cloud/api'

    def _call_api(self, endpoint, api_id, query={}):
        return self._download_json(f'{self._API_URL}/{endpoint}', api_id,
                                   'Downloading JSON', 'Unable to download JSON', query=query)


class VolejTVIE(VolejTVBaseIE):
    IE_NAME = 'volejtv:match'
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
        json_data = self._call_api(f'match/{video_id}', video_id)
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


class VolejTVClubPlaylistIE(VolejTVBaseIE):
    IE_NAME = 'volejtv:club'
    _VALID_URL = r'https?://volej\.tv/klub/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://volej.tv/klub/1173',
        'info_dict': {
            'id': '1173',
            'title': 'VK Jihostroj České Budějovice',
        },
        'playlist_mincount': 30,
    }]
    _PAGE_SIZE = 6

    def _get_page(self, playlist_id, page):
        return self._call_api(f'match/by-team-id-paginated/{playlist_id}', playlist_id,
                              query={'page': page + 1, 'take': self._PAGE_SIZE, 'order': 'DESC'})

    def _entries(self, playlist_id, first_page_data, page):
        entries = first_page_data if page == 0 else self._get_page(playlist_id, page)
        for entry in entries.get('data', []):
            yield self.url_result(f"https://volej.tv/match/{entry['id']}", VolejTVIE)

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        title = self._call_api(f'team/show/{playlist_id}', playlist_id)['title']
        first_page_data = self._get_page(playlist_id, 0)
        total_pages = traverse_obj(first_page_data, ('meta', 'pageCount', {int}))
        return self.playlist_result(InAdvancePagedList(
            functools.partial(self._entries, playlist_id, first_page_data),
            total_pages, self._PAGE_SIZE), playlist_id, title)


class VolejTVCategoryPlaylistIE(VolejTVClubPlaylistIE):
    IE_NAME = 'volejtv:category'
    _VALID_URL = r'https?://volej\.tv/kategorie/(?P<id>[^/$?]+)'
    _TESTS = [{
        'url': 'https://volej.tv/kategorie/chance-cesky-pohar',
        'info_dict': {
            'id': 'chance-cesky-pohar',
            'title': 'Chance Český pohár',
        },
        'playlist_mincount': 30,
    }]
    _PAGE_SIZE = 10

    def _get_page(self, playlist_id, page):
        return self._call_api(f'match/by-category-id-paginated/{playlist_id}', playlist_id,
                              query={'page': page + 1, 'take': self._PAGE_SIZE, 'order': 'DESC'})

    def _get_category(self, playlist_id):
        categories = self._call_api('category', playlist_id)
        for category in categories:
            if category['slug'] == str(playlist_id):
                return category['id'], category['title']

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        category_id, title = self._get_category(playlist_id)
        first_page_data = self._get_page(category_id, 0)
        total_pages = traverse_obj(first_page_data, ('meta', 'pageCount', {int}))
        return self.playlist_result(InAdvancePagedList(
            functools.partial(self._entries, category_id, first_page_data),
            total_pages, self._PAGE_SIZE), playlist_id, title)
