from .common import InfoExtractor


class ClubhouseIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?clubhouse\.com/room/(?P<id>[a-z0-9A-Z]+)'

    _TESTS = [{
        'url': 'https://www.clubhouse.com/room/PN50O4GG',
        'info_dict': {
            'id': 'PN50O4GG',
            'ext': 'ts',
            'title': '香港消費券轉會！八達通、PayMe、BoC Pay、Tap＆Go、AlipayHK、WeChat Pay 邊個最有伏'
        }
    }]

    def _real_extract(self, url):
        id = self._match_id(url)

        data_json = self._download_json(f'https://www.clubhouse.com/web_api/get_replay_channel/{id}', id)['replay']
        info_json = data_json.get('source_channel') or {}

        formats, subtitles = self._extract_m3u8_formats_and_subtitles('https://www.clubhouse.com' + data_json['audio_m3u8_url'], id, ext='ts')
        self._sort_formats(formats)

        return {
            'id': id,
            'title': info_json.get('topic'),
            'formats': formats,
            'subtitles': subtitles
        }
