from .common import InfoExtractor


class FYPTTIE(InfoExtractor):
    _VALID_URL = r'https?://(?:stream\.|)fyptt\.to/(?P<id>[0-9a-zA-Z]+)(?:\.|/)'
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
        #video_id = self._match_id(url)
        #webpage = self._download_webpage(url, video_id)

        # TODO more code goes here, for example ...
        title = self._html_search_regex(r'<h1>(.+?)</h1>', webpage, 'title')

        return {
            'id': video_id,
            'title': title,
            'description': self._og_search_description(webpage),
            'uploader': self._search_regex(r'<div[^>]+id="uploader"[^>]*>([^<]+)<', webpage, 'uploader', fatal=False),
            # TODO more properties (see yt_dlp/extractor/common.py)
        }