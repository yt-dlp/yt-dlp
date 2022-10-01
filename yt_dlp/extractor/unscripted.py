from .common import InfoExtractor
from ..utils import parse_duration, traverse_obj


class UnscriptedNewsVideoIE(InfoExtractor):
    _VALID_URL = r'https?://www\.unscripted\.news/videos/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.unscripted.news/videos/a-day-at-the-farmers-protest',
        'info_dict': {
            'id': '60c0a55cd1e99b1079918a57',
            'display_id': 'a-day-at-the-farmers-protest',
            'ext': 'mp4',
            'title': 'A Day at the Farmers\' Protest',
            'description': 'md5:4b3df22747a03e8f14f746dd72190384',
            'thumbnail': 'https://s3.unscripted.news/anj2/60c0a55cd1e99b1079918a57/5f199a65-c803-4a5c-8fce-2077359c3b72.jpg',
            'duration': 2251.0,
            'series': 'Ground Reports',
        }
    }, {
        'url': 'https://www.unscripted.news/videos/you-get-the-politicians-you-deserve-ft-shashi-tharoor',
        'info_dict': {
            'id': '5fb3afbf18ac817d341a74d8',
            'display_id': 'you-get-the-politicians-you-deserve-ft-shashi-tharoor',
            'ext': 'mp4',
            'cast': ['Avalok Langer', 'Ashwin Mehta'],
            'thumbnail': 'https://s3.unscripted.news/anj2/5fb3afbf18ac817d341a74d8/82bd7942-4f20-4cd8-98ae-83f9e814f998.jpg',
            'description': 'md5:1e91b069238a705ca3a40f87e6f1182c',
            'duration': 1046.0,
            'series': 'Dumb Questions Only',
            'title': 'You Get The Politicians You Deserve! ft. Shashi Tharoor',
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        nextjs_data = self._search_nextjs_data(webpage, display_id)['props']['pageProps']['dataLocal']

        # TODO: get subtitle from srt key
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(nextjs_data['alt_content'], display_id)

        return {
            'id': nextjs_data['_id'],
            'display_id': display_id,
            'title': nextjs_data.get('title') or self._og_search_title(webpage),
            'description': nextjs_data.get('sh_heading') or self._og_search_description(webpage),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': self._og_search_thumbnail(webpage),
            'duration': parse_duration(nextjs_data.get('duration')),
            'series': traverse_obj(nextjs_data, ('show', 'topic')),
            'cast': traverse_obj(nextjs_data, ('cast_crew', ..., 'displayname')),
        }
