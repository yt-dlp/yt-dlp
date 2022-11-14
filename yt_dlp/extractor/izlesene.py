from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urllib_parse_unquote,
)
from ..utils import (
    determine_ext,
    float_or_none,
    get_element_by_id,
    int_or_none,
    parse_iso8601,
    str_to_int,
)


class IzleseneIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(?:(?:www|m)\.)?izlesene\.com/
        (?:video|embedplayer)/(?:[^/]+/)?(?P<id>[0-9]+)
        '''
    _TESTS = [
        {
            'url': 'http://www.izlesene.com/video/sevincten-cildirtan-dogum-gunu-hediyesi/7599694',
            'md5': '4384f9f0ea65086734b881085ee05ac2',
            'info_dict': {
                'id': '7599694',
                'ext': 'mp4',
                'title': 'Sevinçten Çıldırtan Doğum Günü Hediyesi',
                'description': 'md5:253753e2655dde93f59f74b572454f6d',
                'thumbnail': r're:^https?://.*\.jpg',
                'uploader_id': 'pelikzzle',
                'timestamp': int,
                'upload_date': '20140702',
                'duration': 95.395,
                'age_limit': 0,
            }
        },
        {
            'url': 'http://www.izlesene.com/video/tarkan-dortmund-2006-konseri/17997',
            'md5': '97f09b6872bffa284cb7fa4f6910cb72',
            'info_dict': {
                'id': '17997',
                'ext': 'mp4',
                'title': 'Tarkan Dortmund 2006 Konseri',
                'thumbnail': r're:^https://.*\.jpg',
                'uploader_id': 'parlayankiz',
                'timestamp': int,
                'upload_date': '20061112',
                'duration': 253.666,
                'age_limit': 0,
            }
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage('http://www.izlesene.com/video/%s' % video_id, video_id)

        video = self._parse_json(
            self._search_regex(
                r'videoObj\s*=\s*({.+?})\s*;\s*\n', webpage, 'streams'),
            video_id)

        title = video.get('videoTitle') or self._og_search_title(webpage)

        formats = []
        for stream in video['media']['level']:
            source_url = stream.get('source')
            if not source_url or not isinstance(source_url, compat_str):
                continue
            ext = determine_ext(url, 'mp4')
            quality = stream.get('value')
            height = int_or_none(quality)
            formats.append({
                'format_id': '%sp' % quality if quality else 'sd',
                'url': compat_urllib_parse_unquote(source_url),
                'ext': ext,
                'height': height,
            })
        self._sort_formats(formats)

        description = self._og_search_description(webpage, default=None)
        thumbnail = video.get('posterURL') or self._proto_relative_url(
            self._og_search_thumbnail(webpage), scheme='http:')

        uploader = self._html_search_regex(
            r"adduserUsername\s*=\s*'([^']+)';",
            webpage, 'uploader', fatal=False)
        timestamp = parse_iso8601(self._html_search_meta(
            'uploadDate', webpage, 'upload date'))

        duration = float_or_none(video.get('duration') or self._html_search_regex(
            r'videoduration["\']?\s*=\s*(["\'])(?P<value>(?:(?!\1).)+)\1',
            webpage, 'duration', fatal=False, group='value'), scale=1000)

        view_count = str_to_int(get_element_by_id('videoViewCount', webpage))
        comment_count = self._html_search_regex(
            r'comment_count\s*=\s*\'([^\']+)\';',
            webpage, 'comment_count', fatal=False)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'uploader_id': uploader,
            'timestamp': timestamp,
            'duration': duration,
            'view_count': int_or_none(view_count),
            'comment_count': int_or_none(comment_count),
            'age_limit': self._family_friendly_search(webpage),
            'formats': formats,
        }
