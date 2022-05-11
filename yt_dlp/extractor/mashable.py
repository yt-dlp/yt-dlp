import json
import re

from yt_dlp.utils import ExtractorError

from .common import InfoExtractor

class MashableExtractorIE(InfoExtractor):
    # _VALID_URL = r'https?://(?:www\.)?mashable\.com/video/(?P<id>[0-9]+)'
    _VALID_URL = r'https?://(?:www\.)?mashable\.com/video/(.*)'
    _TESTS = [{
            'url': 'https://mashable.com/video/who-took-the-first-selfie-ever',
            'md5': '57885cced912e5813a3e6447278c8b8e',
            'info_dict': {
                'id': '5cee6e38-f9c8-5ceb',
                'ext': 'mp4',
                'duration': 63.0,
                'title': 'Who took the first selfie ever?',
                'thumbnail': r're:^https?://.*\.png$',
                'description': 'Say cheese!',
            }
        },{
            'url': 'https://mashable.com/video/why-life-on-venus-is-better-than-mars',
            'md5': '109054d8aa133d33fd46985d42f1195e',
            'info_dict': {
                'id': '50319e30-a4ce-084d',
                'ext': 'mp4',
                'duration': 257.0,
                'title': 'MashableExtractor video #50319e30-a4ce-084d', # generic assigned by code
                'thumbnail': r're:^https?://.*\.jpg$',
                'description': 'Leave Mars to the ultra-rich. It’s Venus we should move to one day.',
            }
        }]

    def _real_extract(self, url):
        webpage = self._download_webpage(url, None)
        
        pattern = re.compile(r'data: (.*),')
        matches = pattern.search(webpage)
        try:
            video_metadata = json.loads(matches.group(1))
            pattern = re.compile(r'https:\/\/vdist.aws.mashable.com\/cms/[0-9]{4}\/[0-9]{1,2}\/(.*-.*-.*)\/mp4\/.*')
            video_id = pattern.search(video_metadata['url']).group(1)
            url = video_metadata['url']
            thumbnail_url = video_metadata['thumbnail_url']
            duration = float(video_metadata['duration'])
        except (ValueError, IndexError) as e:
            raise ExtractorError(f"Could not parse video metadata from mashable: {e}")

        title = video_metadata['title'] if video_metadata['title'] else ''

        return {
            'id': video_id,
            'title': title,
            'ext': 'mp4',
            'duration': duration,
            'description': self._og_search_description(webpage),
            'url': url,
            'thumbnail': thumbnail_url,
        }