from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_duration,
    unified_timestamp,
)


class MeipaiIE(InfoExtractor):
    IE_DESC = '美拍'
    _VALID_URL = r'https?://(?:www\.)?meipai\.com/media/(?P<id>[0-9]+)'
    _TESTS = [{
        # regular uploaded video
        'url': 'http://www.meipai.com/media/531697625',
        'md5': 'e3e9600f9e55a302daecc90825854b4f',
        'info_dict': {
            'id': '531697625',
            'ext': 'mp4',
            'title': '#葉子##阿桑##余姿昀##超級女聲#',
            'description': '#葉子##阿桑##余姿昀##超級女聲#',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 152,
            'timestamp': 1465492420,
            'upload_date': '20160609',
            'view_count': 35511,
            'creator': '她她-TATA',
            'tags': ['葉子', '阿桑', '余姿昀', '超級女聲'],
        },
    }, {
        # record of live streaming
        'url': 'http://www.meipai.com/media/585526361',
        'md5': 'ff7d6afdbc6143342408223d4f5fb99a',
        'info_dict': {
            'id': '585526361',
            'ext': 'mp4',
            'title': '姿昀和善願 練歌練琴啦😁😁😁',
            'description': '姿昀和善願 練歌練琴啦😁😁😁',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 5975,
            'timestamp': 1474311799,
            'upload_date': '20160919',
            'view_count': 1215,
            'creator': '她她-TATA',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._generic_title('', webpage)

        formats = []

        # recorded playback of live streaming
        m3u8_url = self._html_search_regex(
            r'file:\s*encodeURIComponent\((["\'])(?P<url>(?:(?!\1).)+)\1\)',
            webpage, 'm3u8 url', group='url', default=None)
        if m3u8_url:
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, video_id, 'mp4', entry_protocol='m3u8_native',
                m3u8_id='hls', fatal=False))

        if not formats:
            # regular uploaded video
            video_url = self._search_regex(
                r'data-video=(["\'])(?P<url>(?:(?!\1).)+)\1', webpage, 'video url',
                group='url', default=None)
            if video_url:
                formats.append({
                    'url': video_url,
                    'format_id': 'http',
                })

        timestamp = unified_timestamp(self._og_search_property(
            'video:release_date', webpage, 'release date', fatal=False))

        tags = self._og_search_property(
            'video:tag', webpage, 'tags', default='').split(',')

        view_count = int_or_none(self._html_search_meta(
            'interactionCount', webpage, 'view count'))
        duration = parse_duration(self._html_search_meta(
            'duration', webpage, 'duration'))
        creator = self._og_search_property(
            'video:director', webpage, 'creator', fatal=False)

        return {
            'id': video_id,
            'title': title,
            'description': self._og_search_description(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
            'duration': duration,
            'timestamp': timestamp,
            'view_count': view_count,
            'creator': creator,
            'tags': tags,
            'formats': formats,
        }
