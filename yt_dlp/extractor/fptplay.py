import hashlib
import time
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
)


class FptplayIE(InfoExtractor):
    _VALID_URL = r'https?://fptplay\.vn/xem-video/[^/]+\-(?P<id>[a-f0-9]+)'
    _GEO_COUNTRIES = ['VN']
    IE_NAME = 'fptplay'
    IE_DESC = 'fptplay.vn'
    _TESTS = [{
        'url': 'https://fptplay.vn/xem-video/jumanji-tro-choi-ky-ao-615c9b232089bd0509bfbf42',
        'info_dict': {
            'id': '615c9b232089bd0509bfbf42',
            'ext': 'mp4',
            'title': 'Jumanji: Welcome To The Jungle',
            'description': 'Phim theo chân một nhóm bốn học sinh phổ thông bị phạt dọn dẹp tầng hầm trường học. Tại đó, họ phát hiện ra trò chơi cổ mang tên Jumanji.',
            'thumbnail': 'https://images.fptplay.net/media/OTT/VOD/2023/03/13/jumanji-tro-choi-ky-ao-fpt-play-1678685776013_Background_1920x1080_over.jpg',
            'release_year': '2017',
        },
    }, {
        'url': 'https://fptplay.vn/xem-video/sang-nhu-trang-trong-may-6156d8292089bd2184e26238',
        'info_dict': {
            'id': '346034',
            'ext': 'mp4',
            'title': 'Bright As The Moon',
            'description': '',
            'release_year': '2021',
            'season_number': '1',
            'episode': 'Tập 1',
            'episode_number': '1',
            'duration': '2665',
        },
    }]

    def _real_extract(self, url):
        contentId = self._match_id(url)
        # Need valid cookie with Bearer token, else it won't work
        token = self._get_cookies(url).get('token')
        res = self._download_json(self.get_api_with_st_token(contentId), contentId, expected_status=406)
        if res['result']['episode_type'] == 0:
            # movie or single video
            manifest = self._download_json(self.get_api_with_st_token(contentId, 0), contentId, headers={'authorization': f'Bearer {token.value}'}, expected_status=406)
            if manifest.get('msg') != 'success':
                raise ExtractorError(f" - Got an error, response: {manifest.get('msg')}", expected=True)
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(manifest['data']['url'], contentId)
            return {
                'id': contentId,
                'title': res['result']['title_origin'] if res['result']['title_origin'] else res['result']['title_vie'],
                'description': res['result']['description'],
                'thumbnail': res['result']['thumb'],
                'release_year': int_or_none(res['result']['movie_release_date']),
                'duration': int_or_none(res['result']['duration']),
                'formats': formats,
                'subtitles': subtitles,
            }
        else:
            # playlist
            entries = []
            for episode in res['result']['episodes']:
                if episode['is_trailer'] == 1:
                    continue
                manifest = self._download_json(self.get_api_with_st_token(contentId, episode['_id']), episode['_id'], headers={'authorization': f'Bearer {token.value}'}, expected_status=406)
                if manifest.get('msg') != 'success':
                    raise ExtractorError(f" - Got an error, response: {manifest.get('msg')}", expected=True)
                formats, subtitles = self._extract_m3u8_formats_and_subtitles(manifest['data']['url'], episode['_id'])
                entry = {
                    'id': episode['ref_episode_id'],
                    'title': res['result']['title_origin'] if res['result']['title_origin'] else res['result']['title_vie'],
                    'description': episode['description'],
                    'thumbnail': episode['thumb'],
                    'release_year': int_or_none(res['result']['movie_release_date']),
                    'season_number': 1,  # Assuming season 1 for simplicity
                    'episode': episode['title'],
                    'episode_number': episode['_id'] + 1,
                    'duration': int_or_none(episode['duration']),
                    'formats': formats,
                    'subtitles': subtitles,
                }
                entries.append(entry)
            return {
                '_type': 'playlist',
                'id': contentId,
                'title': res['result']['title_origin'] if res['result']['title_origin'] else res['result']['title_vie'],
                'entries': entries,
            }

    def get_api_with_st_token(self, video_id, episode=None):
        if episode is not None:
            path = f'/api/v7.1_w/stream/vod/{video_id}/{0 if episode is None else episode}/adaptive_bitrate'
        else:
            path = f'/api/v7.1_w/vod/detail/{video_id}'
        timestamp = int(time.time()) + 10800
        t = hashlib.md5(f'6ea6d2a4e2d3a4bd5e275401aa086d{timestamp}{path}'.encode()).hexdigest().upper()
        r = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
        n = [int(f'0x{t[2 * o: 2 * o + 2]}', 16) for o in range(len(t) // 2)]

        def convert(e):
            t = ''
            n = 0
            i = [0, 0, 0]
            a = [0, 0, 0, 0]
            s = len(e)
            c = 0
            for _ in range(s, 0, -1):
                if n <= 3:
                    i[n] = e[c]
                n += 1
                c += 1
                if n == 3:
                    a[0] = (252 & i[0]) >> 2
                    a[1] = ((3 & i[0]) << 4) + ((240 & i[1]) >> 4)
                    a[2] = ((15 & i[1]) << 2) + ((192 & i[2]) >> 6)
                    a[3] = (63 & i[2])
                    for v in range(4):
                        t += r[a[v]]
                    n = 0
            if n:
                for o in range(n, 3):
                    i[o] = 0
                for o in range(n + 1):
                    a[0] = (252 & i[0]) >> 2
                    a[1] = ((3 & i[0]) << 4) + ((240 & i[1]) >> 4)
                    a[2] = ((15 & i[1]) << 2) + ((192 & i[2]) >> 6)
                    a[3] = (63 & i[2])
                    t += r[a[o]]
                    n += 1
                while n < 3:
                    t += ''
                    n += 1
            return t
        st_token = convert(n).replace('+', '-').replace('/', '_').replace('=', '')
        return f"https://api.fptplay.net{path}?{urllib.parse.urlencode({'st': st_token, 'e': timestamp})}"
