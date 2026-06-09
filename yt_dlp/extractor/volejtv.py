import functools

from .common import InfoExtractor
from ..utils import (
    InAdvancePagedList,
    int_or_none,
    join_nonempty,
    orderedSet,
    str_or_none,
    strftime_or_none,
    unified_timestamp,
    url_or_none,
)
from ..utils.traversal import (
    require,
    traverse_obj,
)


class VolejTVBaseIE(InfoExtractor):
    TBR_HEIGHT_MAPPING = {
        '6000': 1080,
        '2400': 720,
        '1500': 480,
        '800': 360,
    }

    def _call_api(self, endpoint, display_id, query=None):
        return self._download_json(
            f'https://api-volejtv-prod.apps.okd4.devopsie.cloud/api/{endpoint}',
            display_id, query=query)


class VolejTVIE(VolejTVBaseIE):
    IE_NAME = 'volejtv:match'
    _VALID_URL = r'https?://volej\.tv/match/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://volej.tv/match/270579',
        'info_dict': {
            'id': '270579',
            'ext': 'mp4',
            'title': 'SWE-CZE (2024-06-16)',
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
            'title': 'FRA-CZE (2024-09-06)',
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
        for video in traverse_obj(json_data, ('videos', 0, 'qualities', lambda _, v: url_or_none(v['cloud_front_path']))):
            formats.append(traverse_obj(video, {
                'url': 'cloud_front_path',
                'tbr': ('quality', {int_or_none}),
                'format_id': ('id', {str_or_none}),
                'height': ('quality', {self.TBR_HEIGHT_MAPPING.get}),
            }))

        data = {
            'id': video_id,
            **traverse_obj(json_data, {
                'series': ('competition_name', {str}),
                'season': ('season', {str}),
                'timestamp': ('match_time', {unified_timestamp}),
                'categories': ('category', ('title'), {str}, filter, all, filter),
                'thumbnail': ('poster', {url_or_none}),
            }),
            'formats': formats,
        }

        teams = orderedSet(traverse_obj(json_data, ('teams', ..., 'shortcut', {str})))
        if len(teams) > 2 and 'FIN' in teams:
            teams.remove('FIN')

        data['title'] = join_nonempty(
            join_nonempty(*teams, delim='-'),
            strftime_or_none(data.get('timestamp'), '(%Y-%m-%d)'),
            delim=' ')

        return data


class VolejTVPlaylistBaseIE(VolejTVBaseIE):
    """Subclasses must set _API_FILTER, _PAGE_SIZE"""

    def _get_page(self, playlist_id, page):
        return self._call_api(
            f'match/{self._API_FILTER}/{playlist_id}', playlist_id,
            query={'page': page + 1, 'take': self._PAGE_SIZE, 'order': 'DESC'})

    def _entries(self, playlist_id, first_page_data, page):
        entries = first_page_data if page == 0 else self._get_page(playlist_id, page)
        for match_id in traverse_obj(entries, ('data', ..., 'id')):
            yield self.url_result(f'https://volej.tv/match/{match_id}', VolejTVIE)


class VolejTVClubPlaylistIE(VolejTVPlaylistBaseIE):
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
    _API_FILTER = 'by-team-id-paginated'
    _PAGE_SIZE = 6

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        title = self._call_api(f'team/show/{playlist_id}', playlist_id)['title']
        first_page_data = self._get_page(playlist_id, 0)
        total_pages = traverse_obj(first_page_data, ('meta', 'pageCount', {int}, {require('page count')}))
        return self.playlist_result(InAdvancePagedList(
            functools.partial(self._entries, playlist_id, first_page_data),
            total_pages, self._PAGE_SIZE), playlist_id, title)


class VolejTVCategoryPlaylistIE(VolejTVPlaylistBaseIE):
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
    _API_FILTER = 'by-category-id-paginated'
    _PAGE_SIZE = 10

    def _get_category(self, playlist_id):
        categories = self._call_api('category', playlist_id)
        for category in traverse_obj(categories, (lambda _, v: v['slug'] and v['id'] and v['title'])):
            if category['slug'] == playlist_id:
                return category['id'], category['title']

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        category_id, title = self._get_category(playlist_id)
        first_page_data = self._get_page(category_id, 0)
        total_pages = traverse_obj(first_page_data, ('meta', 'pageCount', {int}, {require('page count')}))
        return self.playlist_result(InAdvancePagedList(
            functools.partial(self._entries, category_id, first_page_data),
            total_pages, self._PAGE_SIZE), playlist_id, title)
