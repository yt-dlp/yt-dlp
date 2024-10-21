import functools
import math

from .common import InfoExtractor
from ..utils import (
    InAdvancePagedList,
    int_or_none,
    str_or_none,
    traverse_obj,
    unified_strdate,
    url_or_none,
)


class SubsplashVideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?subsplash\.com/u/[^/]+/media/d/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://subsplash.com/u/skywatchtv/media/d/5whnx5s-the-grand-delusion-taking-place-right-now',
        'md5': '2d67c50deac3c6c49c6e25c4a5b25afe',
        'info_dict': {
            'id': '33f8d305-68ab-414c-acf2-f2317a0abe21',
            'ext': 'mp4',
            'title': 'THE GRAND DELUSION TAKING PLACE RIGHT NOW!',
            'description': 'md5:220a630865c3697b0ec9dcb3a70cbc33',
            'upload_date': '20240901',
            'duration': 1710,
            'thumbnail': r're:^https?://.*\.(?:jpg|png)$',
        },
    }, {
        'url': 'https://subsplash.com/u/prophecywatchers/media/d/n4dr8b2-the-transhumanist-plan-for-humanity-billy-crone',
        'md5': 'f7b4109ba7f012dff953391d6b400730',
        'info_dict': {
            'id': 'e16348f1-040e-4596-b922-77b45fa8d253',
            'ext': 'mp4',
            'title': 'The Transhumanist Plan for Humanity | Billy Crone',
            'description': None,
            'upload_date': '20240903',
            'duration': 1709,
            'thumbnail': r're:^https?://.*\.(?:jpg|png)$',
        },
    }]

    def _fetch_json(self, url, display_id, token):
        return self._download_json(url, display_id, headers={'Authorization': f'Bearer {token}'})

    def _extract_metadata(self, data, display_id):
        return traverse_obj(data, {
            'id': ('id', {str_or_none}),
            'title': ('title', {str_or_none}),
            'description': ('summary_text', {str_or_none}),
            'thumbnail': ('_embedded', 'images', 0, '_links', 'related', 'href', {url_or_none}),
            'duration': ('_embedded', 'video', 'duration', {lambda x: int_or_none(x, 1000)}),
            'upload_date': ('published_at', {unified_strdate}),
            'formats': ('_embedded', 'video', '_embedded', 'playlists', 0, '_links', 'related', 'href',
                        {lambda url: self._extract_m3u8_formats(url, display_id)}),
        })

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage, urlh = self._download_webpage_handle(url, display_id)
        token = urlh.get_header('set-cookie').split(';')[0].split('=')[1].strip()
        metadata_url = f'https://core.subsplash.com/media/v1/media-items?filter[short_code]={display_id}&include=images,audio.audio-outputs,audio.video,video.video-outputs,video.playlists,document,broadcast'
        metadata = self._fetch_json(metadata_url, display_id, token)
        return self._extract_metadata(traverse_obj(metadata, ('_embedded', 'media-items', 0, {dict})), display_id)


class SubsplashPlaylistIE(SubsplashVideoIE):
    IE_NAME = 'subsplash:playlist'
    _VALID_URL = r'https?://(?:www\.)?subsplash\.com/[^/]+/(?:our-videos|media)/ms/\+(?P<id>\w+)'
    _PAGE_SIZE = 15
    _TESTS = [{
        'url': 'https://subsplash.com/skywatchtv/our-videos/ms/+dbyjzp8',
        'info_dict': {
            'id': 'dbyjzp8',
            'title': 'Five in Ten',
        },
        'playlist_mincount': 24,
    }, {
        'url': 'https://subsplash.com/prophecywatchers/media/ms/+n42mr48',
        'info_dict': {
            'id': 'n42mr48',
            'title': 'Road to Zion Series',
        },
        'playlist_mincount': 13,
    }, {
        'url': 'https://subsplash.com/prophecywatchers/media/ms/+918b9f6',
        'only_matching': True,
    }]

    def _get_entries(self, token, series_id, page):
        url = f'https://core.subsplash.com/media/v1/media-items?filter[broadcast.status|broadcast.status]=null|on-demand&filter[media_series]={series_id}&filter[status]=published&include=images,audio.audio-outputs,audio.video,video.video-outputs,video.playlists,document&page[number]={page + 1}&page[size]={self._PAGE_SIZE}&sort=-position'
        data = self._fetch_json(url, f'{series_id}_{page}', token)
        entries = traverse_obj(data, ('_embedded', 'media-items', {list}))
        for entry in entries:
            yield self._extract_metadata(entry, series_id)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage, urlh = self._download_webpage_handle(url, display_id)
        token = urlh.get_header('x-api-token')

        series_url = f'https://core.subsplash.com/media/v1/media-series?filter[short_code]={display_id}'
        json_data = self._fetch_json(series_url, display_id, token)
        series_data = traverse_obj(json_data, ('_embedded', 'media-series', 0, {
            'id': ('id', {str}),
            'title': ('title', {str}),
            'count': ('media_items_count', {int}),
        }))
        total_pages = math.ceil(series_data['count'] / self._PAGE_SIZE)

        entries = InAdvancePagedList(functools.partial(self._get_entries, token, series_data['id']), total_pages, self._PAGE_SIZE)
        return self.playlist_result(entries, display_id, series_data['title'])
