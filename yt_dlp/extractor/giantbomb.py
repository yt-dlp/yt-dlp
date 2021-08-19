from __future__ import unicode_literals

import json

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    qualities,
    unescapeHTML,
)


class GiantBombIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?giantbomb\.com/(?:videos|shows)/(?P<display_id>[^/]+)/(?P<id>\d+-\d+)'
    _TESTS = [{
        'url': 'http://www.giantbomb.com/videos/quick-look-destiny-the-dark-below/2300-9782/',
        'md5': '132f5a803e7e0ab0e274d84bda1e77ae',
        'info_dict': {
            'id': '2300-9782',
            'display_id': 'quick-look-destiny-the-dark-below',
            'ext': 'mp4',
            'title': 'Quick Look: Destiny: The Dark Below',
            'description': 'md5:0aa3aaf2772a41b91d44c63f30dfad24',
            'duration': 2399,
            'thumbnail': r're:^https?://.*\.jpg$',
        }
    }, {
        'url': 'https://www.giantbomb.com/shows/ben-stranding/2970-20212',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        display_id = mobj.group('display_id')

        webpage = self._download_webpage(url, display_id)

        title = self._og_search_title(webpage)
        description = self._og_search_description(webpage)
        thumbnail = self._og_search_thumbnail(webpage)

        video = json.loads(unescapeHTML(self._search_regex(
            r'data-video="([^"]+)"', webpage, 'data-video')))

        duration = int_or_none(video.get('lengthSeconds'))

        quality = qualities([
            'f4m_low', 'progressive_low', 'f4m_high',
            'progressive_high', 'f4m_hd', 'progressive_hd'])

        formats = []
        for format_id, video_url in video['videoStreams'].items():
            if format_id == 'f4m_stream':
                continue
            ext = determine_ext(video_url)
            if ext == 'f4m':
                f4m_formats = self._extract_f4m_formats(video_url + '?hdcore=3.3.1', display_id)
                if f4m_formats:
                    f4m_formats[0]['quality'] = quality(format_id)
                    formats.extend(f4m_formats)
            elif ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    video_url, display_id, ext='mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
            else:
                formats.append({
                    'url': video_url,
                    'format_id': format_id,
                    'quality': quality(format_id),
                })

        if not formats:
            youtube_id = video.get('youtubeID')
            if youtube_id:
                return self.url_result(youtube_id, 'Youtube')

        self._sort_formats(formats)

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'formats': formats,
        }
