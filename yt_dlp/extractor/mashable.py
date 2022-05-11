import json
import re

from ..utils import ExtractorError, try_get
from .common import InfoExtractor


class MashableIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?mashable\.com/video/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://mashable.com/video/why-life-on-venus-is-better-than-mars',
        'md5': 'f401a6db2b649d9733c7753474dd2a31',
        'info_dict': {
            'id': '50319e30-a4ce-084d',
            'ext': 'mp4',
            'duration': 257.0,
            'title': 'Mashable video #50319e30-a4ce-084d',  # generic assigned by code
            'thumbnail': r're:^https?://.*\.jpg$',
            'description': 'Leave Mars to the ultra-rich. It’s Venus we should move to one day.',
        }
    },
        {
            'url': 'https://mashable.com/video/who-took-the-first-selfie-ever',
            'md5': '4e83f6efc988ffa242fe7254094b9774',
            'info_dict': {
                'id': '5cee6e38-f9c8-5ceb',
                'ext': 'mp4',
                'duration': 63.0,
                'title': 'Who took the first selfie ever?',
                'thumbnail': r're:^https?://.*\.png$',
                'description': 'Say cheese!',
            }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        pattern = re.compile(r'data: (.*),')
        matches = pattern.search(webpage)
        try:
            video_metadata = json.loads(matches.group(1))
            pattern = re.compile(r'https:\/\/vdist.aws.mashable.com\/cms/[0-9]{4}\/[0-9]{1,2}\/(.*-.*-.*)\/mp4\/.*')
            video_id = pattern.search(video_metadata['url']).group(1)
            url = video_metadata['url']
            thumbnail_url = video_metadata.get('thumbnail_url')
            duration = float(video_metadata.get('duration'))
            m3u8_url = try_get(video_metadata, lambda x: x['transcoded_urls'][0])
            if m3u8_url:
                formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', 'm3u8_native')
                self._sort_formats(formats)
        except (ValueError, IndexError) as e:
            raise ExtractorError(f'Could not parse video metadata from mashable: {e}')

        title = video_metadata['title'] if video_metadata['title'] else ''

        return {
            'id': video_id,
            'title': title,
            'duration': duration,
            'description': self._og_search_description(webpage),
            'thumbnail': thumbnail_url,
            'formats': formats if formats else None,
        }
