import functools
import math

from .common import InfoExtractor
from ..utils import (
    InAdvancePagedList,
    int_or_none,
    parse_iso8601,
    try_call,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class SubsplashBaseIE(InfoExtractor):
    def _get_headers(self, url, display_id):
        token = try_call(lambda: self._get_cookies(url)['ss-token-guest'].value)
        if not token:
            webpage, urlh = self._download_webpage_handle(url, display_id)
            token = (
                try_call(lambda: self._get_cookies(url)['ss-token-guest'].value)
                or urlh.get_header('x-api-token')
                or self._search_json(
                    r'<script[^>]+\bid="shoebox-tokens"[^>]*>', webpage, 'shoebox tokens',
                    display_id, default={}).get('apiToken')
                or self._search_regex(r'\\"tokens\\":{\\"guest\\":\\"([A-Za-z0-9._-]+)\\"', webpage, 'token', default=None))

        if not token:
            self.report_warning('Unable to extract auth token')
            return None
        return {'Authorization': f'Bearer {token}'}

    def _extract_video(self, data, video_id):
        formats = []
        video_data = traverse_obj(data, ('_embedded', 'video', '_embedded', {dict}))
        m3u8_url = traverse_obj(video_data, ('playlists', 0, '_links', 'related', 'href', {url_or_none}))
        if m3u8_url:
            formats.extend(self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', m3u8_id='hls', fatal=False))
        mp4_entry = traverse_obj(video_data, ('video-outputs', lambda _, v: url_or_none(v['_links']['related']['href']), any))
        if mp4_entry:
            formats.append({
                'url': mp4_entry['_links']['related']['href'],
                'format_id': 'direct',
                'quality': 1,
                **traverse_obj(mp4_entry, {
                    'height': ('height', {int_or_none}),
                    'width': ('width', {int_or_none}),
                    'filesize': ('file_size', {int_or_none}),
                }),
            })
        return {
            'id': video_id,
            'formats': formats,
            **traverse_obj(data, {
                'title': ('title', {str}),
                'description': ('summary_text', {str}),
                'thumbnail': ('_embedded', 'images', 0, '_links', 'related', 'href', {url_or_none}),
                'duration': ('_embedded', 'video', 'duration', {int_or_none(scale=1000)}),
                'timestamp': ('date', {parse_iso8601}),
                'release_timestamp': ('published_at', {parse_iso8601}),
                'modified_timestamp': ('updated_at', {parse_iso8601}),
            }),
        }


class SubsplashIE(SubsplashBaseIE):
    _VALID_URL = [
        r'https?://(?:www\.)?subsplash\.com/(?:u/)?[^/?#]+/[^/?#]+/(?:d/|mi/\+)(?P<id>\w+)',
        r'https?://(?:\w+\.)?subspla\.sh/(?P<id>\w+)',
    ]
    _TESTS = [{
        'url': 'https://subsplash.com/u/skywatchtv/media/d/5whnx5s-the-grand-delusion-taking-place-right-now',
        'md5': 'd468729814e533cec86f1da505dec82d',
        'info_dict': {
            'id': '5whnx5s',
            'ext': 'mp4',
            'title': 'THE GRAND DELUSION TAKING PLACE RIGHT NOW!',
            'description': 'md5:220a630865c3697b0ec9dcb3a70cbc33',
            'upload_date': '20240901',
            'duration': 1710,
            'thumbnail': r're:https?://.*\.(?:jpg|png)$',
            'modified_date': '20240901',
            'release_date': '20240901',
            'release_timestamp': 1725195600,
            'timestamp': 1725148800,
            'modified_timestamp': 1725195657,
        },
    }, {
        'url': 'https://subsplash.com/u/prophecywatchers/media/d/n4dr8b2-the-transhumanist-plan-for-humanity-billy-crone',
        'md5': '01982d58021af81c969958459bd81f13',
        'info_dict': {
            'id': 'n4dr8b2',
            'ext': 'mp4',
            'title': 'The Transhumanist Plan for Humanity | Billy Crone',
            'upload_date': '20240903',
            'duration': 1709,
            'thumbnail': r're:https?://.*\.(?:jpg|png)$',
            'timestamp': 1725321600,
            'modified_date': '20241010',
            'release_date': '20240903',
            'release_timestamp': 1725379200,
            'modified_timestamp': 1728577804,
        },
    }, {
        'url': 'https://subsplash.com/laiglesiadelcentro/vid/mi/+ecb6a6b?autoplay=true',
        'md5': '013c9b1e391dd4b34d8612439445deef',
        'info_dict': {
            'id': 'ecb6a6b',
            'ext': 'mp4',
            'thumbnail': r're:https?://.*\.(?:jpg|png)$',
            'release_timestamp': 1477095852,
            'title': 'En el Principio Era el Verbo | EVANGELIO DE JUAN | Ps. Gadiel Ríos',
            'timestamp': 1425772800,
            'upload_date': '20150308',
            'description': 'md5:f368221de93176654989ba66bb564798',
            'modified_timestamp': 1730258864,
            'modified_date': '20241030',
            'release_date': '20161022',
        },
    }, {
        'url': 'https://prophecywatchers.subspla.sh/8gps8cx',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._download_json(
            'https://core.subsplash.com/media/v1/media-items',
            video_id, headers=self._get_headers(url, video_id),
            query={
                'filter[short_code]': video_id,
                'include': 'images,audio.audio-outputs,audio.video,video.video-outputs,video.playlists,document,broadcast',
            })
        return self._extract_video(traverse_obj(data, ('_embedded', 'media-items', 0)), video_id)


class SubsplashPlaylistIE(SubsplashBaseIE):
    IE_NAME = 'subsplash:playlist'
    _VALID_URL = r'https?://(?:www\.)?subsplash\.com/[^/?#]+/(?:our-videos|media)/ms/\+(?P<id>\w+)'
    _PAGE_SIZE = 15
    _TESTS = [{
        'url': 'https://subsplash.com/skywatchtv/our-videos/ms/+dbyjzp8',
        'info_dict': {
            'id': 'dbyjzp8',
            'title': 'Five in Ten',
        },
        'playlist_mincount': 11,
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

    def _entries(self, series_id, headers, page):
        data = self._download_json(
            'https://core.subsplash.com/media/v1/media-items', series_id, headers=headers,
            query={
                'filter[broadcast.status|broadcast.status]': 'null|on-demand',
                'filter[media_series]': series_id,
                'filter[status]': 'published',
                'include': 'images,audio.audio-outputs,audio.video,video.video-outputs,video.playlists,document',
                'page[number]': page + 1,
                'page[size]': self._PAGE_SIZE,
                'sort': '-position',
            }, note=f'Downloading page {page + 1}')

        for entry in traverse_obj(data, ('_embedded', 'media-items', lambda _, v: v['short_code'])):
            entry_id = entry['short_code']
            info = self._extract_video(entry, entry_id)
            yield {
                **info,
                'webpage_url': f'https://subspla.sh/{entry_id}',
                'extractor_key': SubsplashIE.ie_key(),
                'extractor': SubsplashIE.IE_NAME,
            }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        headers = self._get_headers(url, display_id)

        data = self._download_json(
            'https://core.subsplash.com/media/v1/media-series', display_id, headers=headers,
            query={'filter[short_code]': display_id})
        series_data = traverse_obj(data, ('_embedded', 'media-series', 0, {
            'id': ('id', {str}),
            'title': ('title', {str}),
            'count': ('media_items_count', {int}),
        }))
        total_pages = math.ceil(series_data['count'] / self._PAGE_SIZE)

        return self.playlist_result(
            InAdvancePagedList(functools.partial(self._entries, series_data['id'], headers), total_pages, self._PAGE_SIZE),
            display_id, series_data['title'])
