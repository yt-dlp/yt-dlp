from .common import InfoExtractor
from ..utils import base64, re, std_headers


class PStreamIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pstream\.net/(e|v)/(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [{
        'url': 'https://www.pstream.net/e/YdX2V1RLJjJVayY',
        'md5': 'ff370a5aea3f7bbb1e5a7535a80b1e8aebf5c8d7a1f7c80995e550696d2f7659',
        'info_dict': {
            'id': 'mQN5YQKD6jLXvRa',
            'ext': 'mp4',
            'title': 'How I Keep My House In Order',
            'thumbnail': r're^https?://i.pstream\.net/\w*/\w*/\w*\.jpg$',
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

        # url = 'https://www.pstream.net/e/YdX2V1RLJjJVayY'

        m3u8Pattern = r"(https:\/\/www\.pstream\.net\/m\/([a-zA-Z0-9]*)\.m3u8\?expires=([0-9]*)&signature=(\b[A-Fa-f0-9]{64}\b))"
        playerScriptPattern = re.compile("(https://www\.pstream\.net/u/player-script\?v=[a-zA-Z0-9]*&e=[a-zA-Z0-9]*(%3D){0,2})")
        r = self._download_webpage(url, video_id)

        playerScriptURL = self._search_regex(playerScriptPattern, r, "0")

        lines = self._download_webpage(playerScriptURL, video_id)
        line_decoded = []
        for line in lines.split('"'):
            if re.compile("^[a-zA-Z-0-9=]{500,}$").match(line):
                line_decoded.append(line)

        badJson = base64.b64decode(line_decoded[0])
        dicti = self._parse_json(badJson[2:], video_id)
        for i in dicti.items():
            try:
                if None != self._search_regex(m3u8Pattern, i[1], "0", fatal=False, default=None):
                    m3u8_URL = i[1]
            except TypeError:
                pass

        # TODO more code goes here, for example ...
        title = self._search_regex(r'<meta name="og:title" content="([\w ]*)" *\/>', webpage, 'title', fatal=False, default=None)
        return {
            'id': video_id,
            'title': title,
            'url': m3u8_URL,
            'http_headers': std_headers
            # 'description': self._og_search_description(webpage),
            # 'uploader': self._search_regex(r'<div[^>]+id="uploader"[^>]*>([^<]+)<', webpage, 'uploader', fatal=False),
            # TODO more properties (see yt_dlp/extractor/common.py)
        }


# print(PStreamIE._real_extract("https://www.pstream.net/e/YdX2V1RLJjJVayY"))
