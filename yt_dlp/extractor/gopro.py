from .common import InfoExtractor
from ..utils import (
    int_or_none,
    remove_end,
    str_or_none,
    try_get,
    unified_timestamp,
    url_or_none,
)


class GoProIE(InfoExtractor):
    _VALID_URL = r'https?://(www\.)?gopro\.com/v/(?P<id>[A-Za-z0-9]+)'

    _TESTS = [{
        'url': 'https://gopro.com/v/ZNVvED8QDzR5V',
        'info_dict': {
            'id': 'ZNVvED8QDzR5V',
            'title': 'My GoPro Adventure - 9/19/21',
            'thumbnail': r're:https?://.+',
            'ext': 'mp4',
            'timestamp': 1632072947,
            'upload_date': '20210919',
            'uploader_id': 'fireydive30018',
            'duration': 396062,
        }
    }, {
        'url': 'https://gopro.com/v/KRm6Vgp2peg4e',
        'info_dict': {
            'id': 'KRm6Vgp2peg4e',
            'title': 'じゃがいも カリカリ オーブン焼き',
            'thumbnail': r're:https?://.+',
            'ext': 'mp4',
            'timestamp': 1607231125,
            'upload_date': '20201206',
            'uploader_id': 'dc9bcb8b-47d2-47c6-afbc-4c48f9a3769e',
            'duration': 45187,
            'track': 'The Sky Machine',
        }
    }, {
        'url': 'https://gopro.com/v/kVrK9wlJvBMwn',
        'info_dict': {
            'id': 'kVrK9wlJvBMwn',
            'title': 'DARKNESS',
            'thumbnail': r're:https?://.+',
            'ext': 'mp4',
            'timestamp': 1594183735,
            'upload_date': '20200708',
            'uploader_id': '闇夜乃皇帝',
            'duration': 313075,
            'track': 'Battery (Live)',
            'artist': 'Metallica',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        metadata = self._parse_json(
            self._html_search_regex(r'window\.__reflectData\s*=\s*([^;]+)', webpage, 'metadata'), video_id)

        video_info = metadata['collectionMedia'][0]
        media_data = self._download_json(
            'https://api.gopro.com/media/%s/download' % video_info['id'], video_id)

        formats = []
        for fmt in try_get(media_data, lambda x: x['_embedded']['variations']) or []:
            format_url = url_or_none(fmt.get('url'))
            if not format_url:
                continue
            formats.append({
                'url': format_url,
                'format_id': str_or_none(fmt.get('quality')),
                'format_note': str_or_none(fmt.get('label')),
                'ext': str_or_none(fmt.get('type')),
                'width': int_or_none(fmt.get('width')),
                'height': int_or_none(fmt.get('height')),
            })

        title = str_or_none(
            try_get(metadata, lambda x: x['collection']['title'])
            or self._html_search_meta(['og:title', 'twitter:title'], webpage)
            or remove_end(self._html_search_regex(
                r'<title[^>]*>([^<]+)</title>', webpage, 'title', fatal=False), ' | GoPro'))
        if title:
            title = title.replace('\n', ' ')

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': url_or_none(
                self._html_search_meta(['og:image', 'twitter:image'], webpage)),
            'timestamp': unified_timestamp(
                try_get(metadata, lambda x: x['collection']['created_at'])),
            'uploader_id': str_or_none(
                try_get(metadata, lambda x: x['account']['nickname'])),
            'duration': int_or_none(
                video_info.get('source_duration')),
            'artist': str_or_none(
                video_info.get('music_track_artist')),
            'track': str_or_none(
                video_info.get('music_track_name')),
        }
