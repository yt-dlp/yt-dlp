from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    parse_iso8601,
    parse_qs,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import require, traverse_obj


class LocipoBaseIE(InfoExtractor):
    _BASE_URL = 'https://locipo.jp'

    def _call_api(self, path, item_id):
        return self._download_json(
            f'https://api.locipo.jp/api/v1/{path}', item_id)


class LocipoIE(LocipoBaseIE):
    _VALID_URL = r'https?://locipo\.jp/(?:creative|embed)/(?:\?(?:[^#]+&)?id=)?(?P<id>[\da-f]{8}(?:-[\da-f]{4}){3}-[\da-f]{12})'
    _TESTS = [{
        'url': 'https://locipo.jp/creative/fb5ffeaa-398d-45ce-bb49-0e221b5f94f1',
        'info_dict': {
            'id': 'fb5ffeaa-398d-45ce-bb49-0e221b5f94f1',
            'ext': 'mp4',
            'title': 'リアルカレカノ#4 ～伊達さゆりと勉強しよっ？～',
            'description': 'md5:70a40c202f3fb7946b61e55fa015094c',
            'duration': 3622,
            'genres': 'count:1',
            'modified_date': '20240904',
            'modified_timestamp': 1725415481,
            'release_timestamp': 1711789200,
            'release_date': '20240330',
            'series': 'リアルカレカノ',
            'series_id': 'b865b972-99fe-41d5-a72c-8ed5c42132bd',
            'thumbnail': r're:https?://.+\.(?:jpg|png)',
            'timestamp': 1711789200,
            'upload_date': '20240330',
            'uploader': '東海テレビ',
            'uploader_id': 'thk',
        },
    }, {
        'url': 'https://locipo.jp/embed/?id=71a334a0-2b25-406f-9d96-88f341f571c2',
        'info_dict': {
            'id': '71a334a0-2b25-406f-9d96-88f341f571c2',
            'ext': 'mp4',
            'title': '#1 オーディション／ゲスト伊藤美来、豊田萌絵',
            'description': 'md5:5bbcf532474700439cf56ceb6a15630e',
            'duration': 3399,
            'modified_date': '20250704',
            'modified_timestamp': 1751623614,
            'release_timestamp': 1751623200,
            'release_date': '20250704',
            'series': '声優ラジオのウラカブリ～Locipo出張所～',
            'series_id': 'eaf2f2b2-aa73-40f1-b4c9-e47f098775b8',
            'thumbnail': r're:https?://.+\.(?:jpg|png)',
            'timestamp': 1751623200,
            'upload_date': '20250704',
            'uploader': 'テレビ愛知',
            'uploader_id': 'tva',
        },
    }, {
        'url': 'https://locipo.jp/creative/860201fa-f22b-4ffd-8890-6320a857159f?list=fef7c4fb-741f-4d6a-a3a6-754f354302a2',
        'info_dict': {
            'id': 'fef7c4fb-741f-4d6a-a3a6-754f354302a2',
            'title': 'CBCアナウンサー公式【みてちょてれび】',
            'description': 'md5:50a1b23e63112d5c06c882835c8c1fb1',
            'genres': 'count:1',
            'modified_date': '20250611',
            'modified_timestamp': 1749614012,
            'thumbnail': r're:https?://.+\.(?:jpg|png)',
        },
        'playlist_mincount': 32,
    }]

    def _real_extract(self, url):
        video_type, video_id = self._match_valid_url(url).group('type', 'id')
        if not video_id:
            video_id = traverse_obj(parse_qs(url), ('id', -1, {str}, {require('video ID')}))

        playlist_id = traverse_obj(parse_qs(url), ('list', -1, {str}))
        if playlist_id and not self.get_param('noplaylist'):
            return self.url_result(
                f'{self._BASE_URL}/playlist/{playlist_id}', LocipoPlaylistIE)

        creatives = self._call_api(f'creatives/{video_id}', video_id)
        m3u8_url = traverse_obj(creatives, ('video', 'hls', {url_or_none}, {require('manifest URL')}))
        uploader_id = traverse_obj(creatives, ('station_cd', {str}))

        return {
            'id': video_id,
            'formats': self._extract_m3u8_formats(m3u8_url, video_id, 'mp4'),
            'uploader': traverse_obj(self._call_api('config', video_id), (
                'stations', lambda _, v: v['station_cd'] == uploader_id, 'name', {str}, any)),
            'uploader_id': uploader_id,
            **traverse_obj(creatives, {
                'title': ('title', {clean_html}),
                'description': ('description', {clean_html}, filter),
                'duration': ('video', 'duration', {int_or_none}),
                'modified_timestamp': ('updated_at', {parse_iso8601}),
                'release_timestamp': ('live_scheduled_at', {parse_iso8601}),
                'thumbnail': (('thumb', 'small_thumb', 'station_thumb'), {url_or_none}, any),
                'timestamp': ('publication_started_at', {parse_iso8601}),
            }),
            **traverse_obj(creatives, ('playlist', {
                'cast': ('actors', ..., 'name', {clean_html}, filter, all, filter),
                'genres': ('locipo_genres', ..., 'name', {clean_html}, filter, all, filter),
                'series': ('title', {clean_html}),
                'series_id': ('id', {str}),
            })),
        }


class LocipoPlaylistIE(LocipoBaseIE):
    _VALID_URL = r'https?://locipo\.jp/playlist/(?P<id>[\da-f]{8}(?:-[\da-f]{4}){3}-[\da-f]{12})'
    _TESTS = [{
        'url': 'https://locipo.jp/playlist/ae42c14e-6006-4932-b40d-16fc236ab71f',
        'info_dict': {
            'id': 'ae42c14e-6006-4932-b40d-16fc236ab71f',
            'title': 'キャッチ！ぶらり旅',
            'description': '知っているようで知らない鉄道沿線の魅力を、上山アナが歩いて探る！',
            'genres': 'count:2',
            'modified_date': '20250801',
            'modified_timestamp': 1754028028,
            'thumbnail': r're:https?://.+\.(?:jpg|png)',
        },
        'playlist_mincount': 67,
    }]

    def _entries(self, playlist_id):
        creatives = self._call_api(f'playlists/{playlist_id}/creatives', playlist_id)
        for creative in traverse_obj(creatives, ('items', lambda _, v: str_or_none(v['id']))):
            yield self.url_result(f'{self._BASE_URL}/creative/{creative["id"]}', LocipoIE)

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        playlists = self._call_api(f'playlists/{playlist_id}', playlist_id)

        return self.playlist_result(
            self._entries(playlist_id), playlist_id, **traverse_obj(playlists, {
                'title': ('title', {clean_html}),
                'description': ('description', {clean_html}, filter),
                'genres': ('locipo_genres', ..., 'name', {clean_html}, filter, all, filter),
                'modified_timestamp': ('updated_at', {parse_iso8601}),
                'thumbnail': (('thumb', 'small_thumb'), {url_or_none}, any),
            }),
        )
