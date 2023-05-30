from .common import InfoExtractor
from ..utils import (
    parse_iso8601,
    traverse_obj,
    url_or_none,
)


class ElevenSportsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?elevensports\.com/view/event/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://elevensports.com/view/event/clf46yr3kenn80jgrqsjmwefk',
        'md5': 'c0958d9ff90e4503a75544358758921d',
        'info_dict': {
            'id': 'clf46yr3kenn80jgrqsjmwefk',
            'title': 'Cleveland SC vs Lionsbridge FC',
            'ext': 'mp4',
            'description': 'md5:03b5238d6549f4ea1fddadf69b5e0b58',
            'upload_date': '20230323',
            'timestamp': 1679612400,
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
        },
        'params': {'skip_download': 'm3u8'}
    }, {
        'url': 'https://elevensports.com/view/event/clhpyd53b06160jez74qhgkmf',
        'md5': 'c0958d9ff90e4503a75544358758921d',
        'info_dict': {
            'id': 'clhpyd53b06160jez74qhgkmf',
            'title': 'AJNLF vs ARRAF',
            'ext': 'mp4',
            'description': 'md5:c8c5e75c78f37c6d15cd6c475e43a8c1',
            'upload_date': '20230521',
            'timestamp': 1684684800,
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
        },
        'params': {'skip_download': 'm3u8'}
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        event_id = self._search_nextjs_data(webpage, video_id)['props']['pageProps']['event']['mclsEventId']
        event_data = self._download_json(
            f'https://mcls-api.mycujoo.tv/bff/events/v1beta1/{event_id}', video_id,
            headers={'Authorization': 'Bearer FBVKACGN37JQC5SFA0OVK8KKSIOP153G'})
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            event_data['streams'][0]['full_url'], video_id, 'mp4', m3u8_id='hls')

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(event_data, {
                'title': ('title', {str}),
                'description': ('description', {str}),
                'timestamp': ('start_time', {parse_iso8601}),
                'thumbnail': ('thumbnail_url', {url_or_none}),
            }),
        }
