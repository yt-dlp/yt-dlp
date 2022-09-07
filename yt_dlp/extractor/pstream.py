from .common import InfoExtractor
from ..utils import base64


class PStreamIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pstream\.net/(e|v)/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://www.pstream.net/v/YdX2V1RLJjJVayY',
        'md5': '5487d5137cfeb078efb13454cd538f77',
        'info_dict': {
            'id': 'YdX2V1RLJjJVayY',
            'ext': 'mp4',
            'title': 'How I Keep My House In Order',
            'thumbnail': 'https://i.pstream.net/l8sR7XK3DHszbtL4_vbWzA/YdX2V1RLJjJVayY/hrKo81Kbxb0iPXt21bL4Coshcp8S4DzO.jpg',
        }
    },
        {
        'url': 'https://www.pstream.net/v/mQN5YQKD6jLXvRa',
        'md5': '08245a58b410a0c62896dd758d16e127',
        'info_dict': {
            'id': 'mQN5YQKD6jLXvRa',
            'ext': 'mp4',
            'title': 'DanMachi_S01E10_MULTi_1080p_10bits_BluRay_x265_AAC_-Punisher694.mkv',
            'thumbnail': None,
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(f'https://www.pstream.net/e/{video_id}', video_id)

        playerScriptURL = self._search_regex(
            r'(https://www\.pstream\.net/u/player-script\?v=[a-zA-Z0-9]*&e=[a-zA-Z0-9]*(?:%3D){0,2})',
            webpage, '0')

        lines = self._download_webpage(playerScriptURL, video_id, note='Downloading Player script')
        line_decoded = []
        for line in lines.split('"'):
            if self._search_regex(r'(^[a-zA-Z-0-9=]{500,}$)', line, '0', default=None, fatal=False):
                line_decoded = line
                break

        badJson = base64.b64decode(line_decoded)
        goodJson = self._parse_json(badJson[2:], video_id)  # Remove the two first characters because there are here to break

        M3U8_RE = r'(https:\/\/www\.pstream\.net\/m\/(?:[a-zA-Z0-9]*)\.m3u8\?expires=(?:[0-9]*)&signature=(?:\b[A-Fa-f0-9]{64}\b))'

        for i in goodJson.items():
            try:
                if self._search_regex(M3U8_RE, i[1], '0', fatal=False, default=None) is not None:
                    m3u8_URL = i[1]
            except TypeError:
                pass

        formats, subs = self._extract_m3u8_formats_and_subtitles(m3u8_URL, video_id, ext='mp4')
        thumbnail = self._search_regex(r'(^[a-zA-Z-0-9=]{500,}$)', webpage, 'thumbnail', fatal=False, default=None)

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'formats': formats,
            'subtitles': subs,
            'thumbnail': thumbnail
        }
