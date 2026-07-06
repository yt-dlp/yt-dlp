import math
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    InAdvancePagedList,
    determine_ext,
    format_field,
    int_or_none,
    join_nonempty,
    traverse_obj,
    unified_timestamp,
    url_or_none,
)


class BanByeBaseIE(InfoExtractor):
    _API_BASE = 'https://api.banbye.com'
    _CDN_BASE = 'https://cdn.banbye.com'
    _VIDEO_BASE = 'https://banbye.com/watch'

    @staticmethod
    def _extract_playlist_id(url, param='playlist'):
        return urllib.parse.parse_qs(
            urllib.parse.urlparse(url).query).get(param, [None])[0]

    def _extract_playlist(self, playlist_id):
        data = self._download_json(f'{self._API_BASE}/playlists/{playlist_id}', playlist_id)
        return self.playlist_result([
            self.url_result(f'{self._VIDEO_BASE}/{video_id}', BanByeIE)
            for video_id in data['videoIds']], playlist_id, data.get('name'))


class BanByeIE(BanByeBaseIE):
    _VALID_URL = r'https?://(?:www\.)?banbye\.com/(?:en/)?watch/(?P<id>[\w-]+)'
    _TESTS = [{
        # ['src']['mp4']['levels'] direct mp4 urls only
        'url': 'https://banbye.com/watch/v_ytfmvkVYLE8T',
        'md5': '2f4ea15c5ca259a73d909b2cfd558eb5',
        'info_dict': {
            'id': 'v_ytfmvkVYLE8T',
            'ext': 'mp4',
            'title': 'md5:5ec098f88a0d796f987648de6322ba0f',
            'description': 'md5:4d94836e73396bc18ef1fa0f43e5a63a',
            'uploader': 'wRealu24',
            'channel_id': 'ch_wrealu24',
            'channel_url': 'https://banbye.com/channel/ch_wrealu24',
            'timestamp': 1647604800,
            'upload_date': '20220318',
            'duration': 1931,
            'thumbnail': r're:https?://.*\.webp',
            'tags': 'count:5',
            'like_count': int,
            'dislike_count': int,
            'view_count': int,
            'comment_count': int,
        },
    }, {
        'url': 'https://banbye.com/watch/v_2JjQtqjKUE_F?playlistId=p_Ld82N6gBw_OJ',
        'info_dict': {
            'title': 'Krzysztof Karoń',
            'id': 'p_Ld82N6gBw_OJ',
        },
        'playlist_mincount': 9,
    }, {
        # ['src']['mp4']['levels'] direct mp4 urls only
        'url': 'https://banbye.com/watch/v_kb6_o1Kyq-CD',
        'info_dict': {
            'id': 'v_kb6_o1Kyq-CD',
            'ext': 'mp4',
            'title': 'Co tak naprawdę dzieje się we Francji?! Czy Warszawa a potem cała Polska będzie drugim Paryżem?!🤔🇵🇱',
            'description': 'md5:82be4c0e13eae8ea1ca8b9f2e07226a8',
            'uploader': 'Marcin Rola - MOIM ZDANIEM!🇵🇱',
            'channel_id': 'ch_QgWnHvDG2fo5',
            'channel_url': 'https://banbye.com/channel/ch_QgWnHvDG2fo5',
            'duration': 597,
            'timestamp': 1688642656,
            'upload_date': '20230706',
            'thumbnail': 'https://cdn.banbye.com/video/v_kb6_o1Kyq-CD/96.webp',
            'tags': ['Paryż', 'Francja', 'Polska', 'Imigranci', 'Morawiecki', 'Tusk'],
            'like_count': int,
            'dislike_count': int,
            'view_count': int,
            'comment_count': int,
        },
    }, {
        # ['src']['hls']['levels'] variant m3u8 urls only; master m3u8 is 404
        'url': 'https://banbye.com/watch/v_a_gPFuC9LoW5',
        'info_dict': {
            'id': 'v_a_gPFuC9LoW5',
            'ext': 'mp4',
            'title': 'md5:183524056bebdfa245fd6d214f63c0fe',
            'description': 'md5:943ac87287ca98d28d8b8797719827c6',
            'uploader': 'wRealu24',
            'channel_id': 'ch_wrealu24',
            'channel_url': 'https://banbye.com/channel/ch_wrealu24',
            'upload_date': '20231113',
            'timestamp': 1699874062,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'comment_count': int,
            'thumbnail': 'https://cdn.banbye.com/video/v_a_gPFuC9LoW5/96.webp',
            'tags': ['jaszczur', 'sejm', 'lewica', 'polska', 'ukrainizacja', 'pierwszeposiedzeniesejmu'],
        },
        'expected_warnings': ['Failed to download m3u8'],
    }, {
        # ['src']['hls']['masterPlaylist'] m3u8 only
        'url': 'https://banbye.com/watch/v_B0rsKWsr-aaa',
        'info_dict': {
            'id': 'v_B0rsKWsr-aaa',
            'ext': 'mp4',
            'title': 'md5:00b254164b82101b3f9e5326037447ed',
            'description': 'md5:3fd8b48aa81954ba024bc60f5de6e167',
            'uploader': 'PSTV Piotr Szlachtowicz ',
            'channel_id': 'ch_KV9EVObkB9wB',
            'channel_url': 'https://banbye.com/channel/ch_KV9EVObkB9wB',
            'upload_date': '20240629',
            'timestamp': 1719646816,
            'duration': 2377,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'comment_count': int,
            'thumbnail': 'https://cdn.banbye.com/video/v_B0rsKWsr-aaa/96.webp',
            'tags': ['Biden', 'Trump', 'Wybory', 'USA'],
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        playlist_id = self._extract_playlist_id(url, 'playlistId')

        if self._yes_playlist(playlist_id, video_id):
            return self._extract_playlist(playlist_id)

        data = self._download_json(f'{self._API_BASE}/videos/{video_id}', video_id)
        thumbnails = [{
            'id': f'{quality}p',
            'url': f'{self._CDN_BASE}/video/{video_id}/{quality}.webp',
        } for quality in [48, 96, 144, 240, 512, 1080]]

        formats = []
        url_data = self._download_json(f'{self._API_BASE}/videos/{video_id}/url', video_id, data=b'')
        if master_url := traverse_obj(url_data, ('src', 'hls', 'masterPlaylist', {url_or_none})):
            formats = self._extract_m3u8_formats(master_url, video_id, 'mp4', m3u8_id='hls', fatal=False)

        for format_id, format_url in traverse_obj(url_data, (
                'src', ('mp4', 'hls'), 'levels', {dict.items}, lambda _, v: url_or_none(v[1]))):
            ext = determine_ext(format_url)
            is_hls = ext == 'm3u8'
            formats.append({
                'url': format_url,
                'ext': 'mp4' if is_hls else ext,
                'format_id': join_nonempty(is_hls and 'hls', format_id),
                'protocol': 'm3u8_native' if is_hls else 'https',
                'height': int_or_none(format_id),
            })
        self._remove_duplicate_formats(formats)

        return {
            'id': video_id,
            'title': data.get('title'),
            'description': data.get('desc'),
            'uploader': traverse_obj(data, ('channel', 'name')),
            'channel_id': data.get('channelId'),
            'channel_url': format_field(data, 'channelId', 'https://banbye.com/channel/%s'),
            'timestamp': unified_timestamp(data.get('publishedAt')),
            'duration': data.get('duration'),
            'tags': data.get('tags'),
            'formats': formats,
            'thumbnails': thumbnails,
            'like_count': data.get('likes'),
            'dislike_count': data.get('dislikes'),
            'view_count': data.get('views'),
            'comment_count': data.get('commentCount'),
        }


class BanByeChannelIE(BanByeBaseIE):
    _VALID_URL = r'https?://(?:www\.)?banbye\.com/(?:en/)?channel/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://banbye.com/channel/ch_wrealu24',
        'info_dict': {
            'title': 'wRealu24',
            'id': 'ch_wrealu24',
            'description': 'md5:da54e48416b74dfdde20a04867c0c2f6',
        },
        'playlist_mincount': 791,
    }, {
        'url': 'https://banbye.com/channel/ch_wrealu24?playlist=p_Ld82N6gBw_OJ',
        'info_dict': {
            'title': 'Krzysztof Karoń',
            'id': 'p_Ld82N6gBw_OJ',
        },
        'playlist_count': 9,
    }]
    _PAGE_SIZE = 100

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        playlist_id = self._extract_playlist_id(url)

        if playlist_id:
            return self._extract_playlist(playlist_id)

        def page_func(page_num):
            data = self._download_json(f'{self._API_BASE}/videos', channel_id, query={
                'channelId': channel_id,
                'sort': 'new',
                'limit': self._PAGE_SIZE,
                'offset': page_num * self._PAGE_SIZE,
            }, note=f'Downloading page {page_num + 1}')
            return [
                self.url_result(f"{self._VIDEO_BASE}/{video['_id']}", BanByeIE)
                for video in data['items']
            ]

        channel_data = self._download_json(f'{self._API_BASE}/channels/{channel_id}', channel_id)
        entries = InAdvancePagedList(
            page_func,
            math.ceil(channel_data['videoCount'] / self._PAGE_SIZE),
            self._PAGE_SIZE)

        return self.playlist_result(
            entries, channel_id, channel_data.get('name'), channel_data.get('description'))
