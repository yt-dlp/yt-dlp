from .common import InfoExtractor
from ..utils import parse_age_limit, parse_duration, traverse_obj


class MagellanTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?magellantv\.com/(?:watch|video)/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.magellantv.com/watch/my-dads-on-death-row?type=v',
        'info_dict': {
            'id': 'my-dads-on-death-row',
            'ext': 'mp4',
            'title': 'My Dad\'s On Death Row',
            'description': 'md5:33ba23b9f0651fc4537ed19b1d5b0d7a',
            'duration': 3780.0,
            'age_limit': 14,
            'tags': ['Justice', 'Reality', 'United States', 'True Crime'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.magellantv.com/video/james-bulger-the-new-revelations',
        'info_dict': {
            'id': 'james-bulger-the-new-revelations',
            'ext': 'mp4',
            'title': 'James Bulger: The New Revelations',
            'description': 'md5:7b97922038bad1d0fe8d0470d8a189f2',
            'duration': 2640.0,
            'age_limit': 0,
            'tags': ['Investigation', 'True Crime', 'Justice', 'Europe'],
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        data = self._search_nextjs_data(webpage, video_id)['props']['pageProps']['reactContext']['video']['detail']
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(data['jwpVideoUrl'], video_id)

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(data, {
                'title': ('title', {str}),
                'description': ('metadata', 'description', {str}),
                'duration': ('duration', {parse_duration}),
                'age_limit': ('ratingCategory', {parse_age_limit}),
                'tags': ('tags', ..., {str}),
            }),
        }
