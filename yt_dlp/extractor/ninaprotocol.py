from .common import InfoExtractor


class NinaProtocolIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ninaprotocol\.com/releases/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': ' https://www.ninaprotocol.com/releases/3xl-nina-label-mix-014',
        'md5': 'TODO: md5 sum of the first 10241 bytes of the video file (use --test)',
        'info_dict': {
            'id': '1',
            'ext': 'mp3',
            'title': '3XL - Nina Label Mix 014',
            'thumbnail': r're:^https?://.*\.jpg$',
            # TODO more properties, either as:
            # * A value
            # * MD5 checksum; start the string with md5:
            # * A regular expression; start the string with re:
            # * Any Python type, e.g. int or float
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        # TODO more code goes here, for example ...
        title = self._html_search_regex(r'<h1>(.+?)</h1>', webpage, 'title')

        return {
            'id': video_id,
            'title': title,
            'description': self._og_search_description(webpage),
            'uploader': self._search_regex(r'<div[^>]+id="uploader"[^>]*>([^<]+)<', webpage, 'uploader', fatal=False),
            # TODO more properties (see yt_dlp/extractor/common.py)
        }