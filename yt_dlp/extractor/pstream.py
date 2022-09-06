from .common import InfoExtractor
from ..utils import base64, std_headers


class PStreamIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pstream\.net/(e|v)/(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [{
        'url': 'https://www.pstream.net/v/YdX2V1RLJjJVayY',
        'md5': '5487d5137cfeb078efb13454cd538f77',
        'info_dict': {
            'id': 'YdX2V1RLJjJVayY',
            'ext': 'mp4',
            'title': 'How I Keep My House In Order',
            'thumbnail': "https://i.pstream.net/l8sR7XK3DHszbtL4_vbWzA/YdX2V1RLJjJVayY/hrKo81Kbxb0iPXt21bL4Coshcp8S4DzO.jpg",
            # TODO more properties, either as:
            # * A value
            # * MD5 checksum; start the string with md5:
            # * A regular expression; start the string with re:
            # * Any Python type, e.g. int or float
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        url = f'https://www.pstream.net/e/{video_id}'

        webpage = self._download_webpage(url, video_id)

        m3u8Pattern = r"(https:\/\/www\.pstream\.net\/m\/([a-zA-Z0-9]*)\.m3u8\?expires=([0-9]*)&signature=(\b[A-Fa-f0-9]{64}\b))"
        playerScriptPattern = r"(https://www\.pstream\.net/u/player-script\?v=[a-zA-Z0-9]*&e=[a-zA-Z0-9]*(%3D){0,2})"
        veryLongBase64 = r"(^[a-zA-Z-0-9=]{500,}$)"


        playerScriptURL = self._search_regex(playerScriptPattern, webpage, "0")

        lines = self._download_webpage(playerScriptURL, video_id, note="Downloading Player script")
        line_decoded = []
        for line in lines.split('"'):
            if self._search_regex(veryLongBase64, line, "0", default=None, fatal=False):
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
        formats, subs = self._extract_m3u8_formats_and_subtitles(m3u8_URL, video_id, ext='mp4')
        self._sort_formats(formats)
        thumbnail = self._search_regex(r'(https?://i.pstream\.net/\w*/\w*/\w*\.jpg)', webpage, 'thumbnail')
        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'subtitles': subs,
            'thumbnail': thumbnail
            # 'description': self._og_search_description(webpage),
            # 'uploader': self._search_regex(r'<div[^>]+id="uploader"[^>]*>([^<]+)<', webpage, 'uploader', fatal=False),
            # TODO more properties (see yt_dlp/extractor/common.py)
        }


# print(PStreamIE._real_extract("https://www.pstream.net/e/YdX2V1RLJjJVayY"))
