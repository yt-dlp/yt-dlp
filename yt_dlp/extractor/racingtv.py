from .common import InfoExtractor
from ..utils import traverse_obj


class RacingTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?racingtv\.com/watch/on-demand/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.racingtv.com/watch/on-demand/137181',
        'info_dict': {
            'id': '137181',
            'title': 'Racing Replay',
            'description': 'md5:be3b53aad0d042e0a5b0b1fe5af1ebdf',
            'ext': 'mp4',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        headers = {
            'Accept': 'application/json',
            'Referer': 'https://www.racingtv.com/',
            'X-Requested-With': 'racingtv-web/5.6.0',
        }
        info = self._download_json(
            f'https://api.racingtv.com/videos/on-demand/catchup/episodes/{video_id}',
            video_id,
            headers=headers,
        )
        title = traverse_obj(info, ('video', 'catchup_video', 'title'))
        description = traverse_obj(info, ('video', 'catchup_video', 'description'))

        resp = self._download_json(
            f'https://api.racingtv.com/member/watch/on-demand/catchup/episodes/{video_id}',
            video_id,
            headers=headers,
            expected_status=402,
        )
        token = traverse_obj(resp, ('player', 'preroll_token'))

        play_info = self._download_json(
            f'https://api.racingtv.com/member/watch/on-demand/catchup/episodes/{video_id}',
            video_id,
            headers=headers,
            query={'preroll_token': token},
            expected_status=402,
        )
        m3u8_url = traverse_obj(play_info, ('player', 'sources', 0, 'url'))
        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', m3u8_id='hls')

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'formats': formats,
        }
