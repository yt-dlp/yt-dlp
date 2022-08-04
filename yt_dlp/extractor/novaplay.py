from .common import InfoExtractor
from ..utils import int_or_none, parse_duration, parse_iso8601


class NovaPlayIE(InfoExtractor):
    _VALID_URL = r'https://play.nova\.bg/video/.*/(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'https://play.nova.bg/video/ochakvaite/season-0/ochakvaite-2022-07-22-sybudi-se-sat/606627',
            'md5': 'd79dff2d09d196c595a7290f48e33399',
            'info_dict': {
                'id': '606627',
                'ext': 'mp4',
                'title': 'Събуди се - събота по NOVA (23.07.2022)',
                'alt_title': 'ochakvaite/season-0/ochakvaite-2022-07-22-sybudi-se-sat',
                'duration': 29.0,
                'timestamp': 1658491547,
                'upload_date': '20220722',
                'thumbnail': 'https://nbg-img.fite.tv/img/606627_460x260.jpg',
                'description': '29 сек',
                'view_count': False
            },
        },
        {
            'url': 'https://play.nova.bg/video/ochakvaite/season-0/ochakvaite-2022-07-22-cherry-tazi/606609',
            'md5': 'f3e973e2ed1a5b9b3f498b1ab82d01b3',
            'info_dict': {
                'id': '606609',
                'ext': 'mp4',
                'title': 'Черешката на тортата - тази вечер по NOVA (22.07.2022)',
                'alt_title': 'ochakvaite/season-0/ochakvaite-2022-07-22-cherry-tazi',
                'duration': 29.0,
                'timestamp': 1658476303,
                'upload_date': '20220722',
                'thumbnail': 'https://nbg-img.fite.tv/img/606609_460x260.jpg',
                'description': '29 сек',
                'view_count': False
            },
        }
    ]

    _access_token = None

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        self._access_token = self._access_token or self._download_json(
            'https://play.nova.bg/api/client', None, note='Fetching access token')['accessToken']
        video_props = self._search_nextjs_data(webpage, video_id)['props']['pageProps']['video']
        m3u8_url = self._download_json(
            f'https://nbg-api.fite.tv/api/v2/videos/{video_id}/streams',
            video_id, headers={
                'x-flipps-user-agent': 'Flipps/75/9.7',
                'x-flipps-version': '2022-05-17',
                'Authorization': f'Bearer {self._access_token}'
            })[0]['links']['play']['href']
        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', m3u8_id='hls')
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': video_props['title'],
            'alt_title': video_props.get('slug'),
            'thumbnail': self._og_search_thumbnail(webpage),
            'description': self._og_search_description(webpage),
            'formats': formats,
            'duration': parse_duration(video_props['duration']),
            'timestamp': parse_iso8601(video_props['published_at']),
            'view_count': int_or_none(video_props['view_count']),
        }
