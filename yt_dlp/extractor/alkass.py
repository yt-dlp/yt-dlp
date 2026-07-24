from .common import InfoExtractor


class AlkassLiveIE(InfoExtractor):
    _VALID_URL = r'https?://shoof\.alkass\.net/live\?ch=(?P<id>.+)'
    _TESTS = [{
        'url': 'https://shoof.alkass.net/live?ch=one',
        'info_dict': {
            'id': '1',
            'title': r're:Alkass 1 \d{4}-\d{2}-\d{2} \d{2}:\d{2}',
            'thumbnail': 'https://www.alkass.net/images/new-1.png',
            'ext': 'mp4',
            'live_status': 'is_live',
        },
    }, {
        'url': 'https://shoof.alkass.net/live?ch=shoof1',
        'info_dict': {
            'id': '14',
            'title': r're:shoof1 \d{4}-\d{2}-\d{2} \d{2}:\d{2}',
            'thumbnail': 'https://www.alkass.net/images/shoof1.png',
            'ext': 'mp4',
            'live_status': 'is_live',
        },
    }, {
        'url': 'https://shoof.alkass.net/live?ch=fifteen',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        webname = self._match_id(url)

        streams = self._download_json('https://shoofapi.alkass.net/Shoof/live.php', webname)

        for stream in streams:
            if stream.get('webname') == webname:
                stream_id = str(stream.get('id'))
                return {
                    'id': stream_id,
                    'formats': self._extract_m3u8_formats(stream.get('body'), stream_id, 'mp4', m3u8_id='hls', live=True),
                    'title': stream.get('title'),
                    'thumbnail': stream.get('image'),
                    'is_live': True,
                }
        return None
