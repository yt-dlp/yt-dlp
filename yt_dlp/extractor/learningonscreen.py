import functools
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    extract_attributes,
    get_element_by_class,
    get_element_html_by_id,
    join_nonempty,
    parse_duration,
    unified_timestamp,
)
from ..utils.traversal import traverse_obj


class LearningOnScreenIE(InfoExtractor):
    _VALID_URL = r'https?://learningonscreen\.ac\.uk/ondemand/index\.php/prog/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://learningonscreen.ac.uk/ondemand/index.php/prog/005D81B2?bcast=22757013',
        'info_dict': {
            'id': '005D81B2',
            'ext': 'mp4',
            'title': 'Planet Earth',
            'duration': 3600.0,
            'timestamp': 1164567600.0,
            'upload_date': '20061126',
            'thumbnail': 'https://stream.learningonscreen.ac.uk/trilt-cover-images/005D81B2-Planet-Earth-2006-11-26T190000Z-BBC4.jpg',
        },
    }]

    def _real_initialize(self):
        if not self._get_cookies('https://learningonscreen.ac.uk/').get('PHPSESSID-BOB-LIVE'):
            self.raise_login_required(
                'Use --cookies for authentication. See '
                ' https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  '
                'for how to manually pass cookies', method=None)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        details = traverse_obj(webpage, (
            {functools.partial(get_element_html_by_id, 'programme-details')}, {
                'title': ({functools.partial(re.search, r'<h2>([^<]+)</h2>')}, 1, {clean_html}),
                'timestamp': (
                    {functools.partial(get_element_by_class, 'broadcast-date')},
                    {functools.partial(re.match, r'([^<]+)')}, 1, {unified_timestamp}),
                'duration': (
                    {functools.partial(get_element_by_class, 'prog-running-time')},
                    {clean_html}, {parse_duration}),
            }))

        title = details.pop('title', None) or traverse_obj(webpage, (
            {functools.partial(get_element_html_by_id, 'add-to-existing-playlist')},
            {extract_attributes}, 'data-record-title', {clean_html}))

        entries = self._parse_html5_media_entries(
            'https://stream.learningonscreen.ac.uk', webpage, video_id, m3u8_id='hls', mpd_id='dash',
            _headers={'Origin': 'https://learningonscreen.ac.uk', 'Referer': 'https://learningonscreen.ac.uk/'})
        if not entries:
            raise ExtractorError('No video found')

        if len(entries) > 1:
            duration = details.pop('duration', None)
            for idx, entry in enumerate(entries, start=1):
                entry.update(details)
                entry['id'] = join_nonempty(video_id, idx)
                entry['title'] = join_nonempty(title, idx)
            return self.playlist_result(entries, video_id, title, duration=duration)

        return {
            **entries[0],
            **details,
            'id': video_id,
            'title': title,
        }
