import re

from ..utils import try_get
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
            'title': 'The ultimate case for living on Venus',
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
        data_pattern = re.compile(r'data: (.*),')
        video_metadata = self._parse_json(self._search_regex(data_pattern, webpage, display_id), display_id)

        video_id_pattern = re.compile(r'https://vdist.aws.mashable.com/cms/[0-9]{4}/[0-9]{1,2}/([0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b)/mp4/.*')
        video_id = self._search_regex(video_id_pattern, video_metadata.get('url'), display_id)
        thumbnail_url = video_metadata.get('thumbnail_url')
        duration = float(video_metadata.get('duration'))
        m3u8_url = try_get(video_metadata, lambda x: x['transcoded_urls'][0])
        if m3u8_url:
            formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', 'm3u8_native')
            self._sort_formats(formats)

        title = video_metadata.get('title')
        if not title:
            # Grab title from the webpage instead
            title = self._og_search_title(webpage)

        return {
            'id': video_id,
            'title': title,
            'duration': duration,
            'description': self._og_search_description(webpage),
            'thumbnail': thumbnail_url,
            'formats': formats if formats else None,
        }
