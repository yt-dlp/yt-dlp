from .common import InfoExtractor
from ..utils import escapeHTML

import re

class FYPTTIE(InfoExtractor):
    _VALID_URL = r'https?://(?:stream\.|)fyptt\.to/(?P<id>[0-9a-zA-Z]+)(?:|/)'
    _TESTS = [{
        'url': 'https://fyptt.to/203/gorgeous-naughty-blonde-with-beautiful-curves-shows-her-naked-boobies-on-nsfw-tiktok/',
        'md5': 'TODO: md5 sum of the first 10241 bytes of the video file (use --test)',
        'info_dict': {
            # For videos, only the 'id' and 'ext' fields are required to RUN the test:
            'id': '203',
            'ext': 'mp4',
            # Then if the test run fails, it will output the missing/incorrect fields.
            # Properties can be added as:
            # * A value, e.g.
            #     'title': 'Video title goes here',
            # * MD5 checksum; start the string with 'md5:', e.g.
            #     'description': 'md5:098f6bcd4621d373cade4e832627b4f6',
            # * A regular expression; start the string with 're:', e.g.
            #     'thumbnail': r're:^https?://.*\.jpg$',
            # * A count of elements in a list; start the string with 'count:', e.g.
            #     'tags': 'count:10',
            # * Any Python type, e.g.
            #     'view_count': int,
        },
    }, {
        'url': 'https://fyptt.to/10382/beautiful-livestream-tits-and-nipples-slip-from-girls-who-loves-talking-with-their-viewers/',
        'only_matching': True,
    }, {
        'url': 'https://fyptt.to/120/small-tits-fit-blonde-dancing-naked-at-the-front-door-on-tiktok',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        formats = []


#        format_url = self._html_search_regex(r'<span">(.+?)</span>', webpage, 'title')
        format_url = self._html_search_regex(r'"embedURL":"([^"]+)"', webpage, 'video URL')

    # Remove invalid characters using regex
        format_url = re.sub(r'\\', '', format_url)
        print("format_url")
        print(format_url)
        webpage_video = self._download_webpage(format_url, video_id)


  #      format_url = self._html_search_regex(r'<source\s+src="(.+?)"\s+type', webpage, 'format_url')
        match = re.search(r'<source\s+src="(.+?)"\s+type', webpage_video)

        format_url = match.group(1)
        print(match)
        formats.append({
            'url': format_url,
            'format_id': 'default',
        })

        title = self._html_search_regex(r'<span class="fl-heading-text">(.+?)</span>', webpage, 'title')


        return {
            'id': video_id,
            'title': title,
            'description': self._og_search_description(webpage),
            'age_limit': 18,
            'formats': formats,
        }