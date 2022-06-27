from ..utils import ExtractorError
from .common import InfoExtractor


class WillowIE(InfoExtractor):
    _VALID_URL = r'https?://(www\.)?willow\.tv/videos/(?P<id>[0-9a-z-_]+)'
    _GEO_COUNTRIES = ['US']

    _TESTS = [{
        'url': 'http://willow.tv/videos/d5winning-moment-eng-vs-ind-streaming-online-4th-test-india-tour-of-england-2021',
        'info_dict': {
            'id': '169662',
            'display_id': 'd5winning-moment-eng-vs-ind-streaming-online-4th-test-india-tour-of-england-2021',
            'ext': 'mp4',
            'title': 'Winning Moment: 4th Test, England vs India',
            'thumbnail': 'https://aimages.willow.tv/ytThumbnails/6748_D5winning_moment.jpg',
            'duration': 233,
            'timestamp': 1630947954,
            'upload_date': '20210906',
            'location': 'Kennington Oval, London',
            'series': 'India tour of England 2021',
        },
        'params': {
            'skip_download': True,  # AES-encrypted m3u8
        },
    }, {
        'url': 'http://willow.tv/videos/highlights-short-ind-vs-nz-streaming-online-2nd-t20i-new-zealand-tour-of-india-2021',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        video_data = self._parse_json(self._html_search_regex(
            r'var\s+data_js\s*=\s*JSON\.parse\(\'(.+)\'\)', webpage,
            'data_js'), video_id)

        video = next((v for v in video_data.get('trending_videos') or []
                      if v.get('secureurl')), None)
        if not video:
            raise ExtractorError('No videos found')

        formats = self._extract_m3u8_formats(video['secureurl'], video_id, 'mp4')
        self._sort_formats(formats)

        return {
            'id': str(video.get('content_id')),
            'display_id': video.get('video_slug'),
            'title': video.get('video_name') or self._html_search_meta('twitter:title', webpage),
            'formats': formats,
            'thumbnail': video.get('yt_thumb_url') or self._html_search_meta(
                'twitter:image', webpage, default=None),
            'duration': video.get('duration_seconds'),
            'timestamp': video.get('created_date'),
            'location': video.get('venue'),
            'series': video.get('series_name'),
        }
