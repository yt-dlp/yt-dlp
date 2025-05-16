from .common import InfoExtractor


class PandaVideoIE(InfoExtractor):
    _VALID_URL = r'https://[a-zA-Z0-9\-]+\.tv\.pandavideo\.com\.br/embed/\?v=(?P<id>[a-zA-Z0-9\-]+)'
    _EMBED_REGEX = [rf'<iframe[^>]+\bsrc=[\'"](?P<url>{_VALID_URL})']
    _WEBPAGE_TESTS = [{
        # Embedebd video test
        'url': 'https://www.pandavideo.com/',
        'info_dict': {
            'id': '1234567890',
            'ext': 'mp4',
            'title': 'Panda Video - Hospedagem de video',
        },
    }, {
        # Embedebd video test
        'url': 'https://help.pandavideo.com/pt-br/article/panda-video-e-mais-seguro-que-vimeo-1dicmr5/',
        'info_dict': {
            'id': '1234567890',
            'ext': 'mp4',
            'title': 'Panda Video - Hospedagem de video',
        },
    }]
    _TESTS = [{
        # Direct Link to video
        'url': 'https://player-vz-12fdccf8-e93.tv.pandavideo.com.br/embed/?v=fc6c9c66-ecc7-4828-a63a-5f3e6f481d7f',
        'info_dict': {
            'id': 'fc6c9c66-ecc7-4828-a63a-5f3e6f481d7f',
            'ext': 'mp4',
            'title': 'Panda Video - Hospedagem de video',
        },
    }, {
        # Direct Link to video
        'url': 'https://player-vz-ded14ebd-85a.tv.pandavideo.com.br/embed/?v=79cb9b0e-a64b-4485-8a44-47f36b292e4c',
        'info_dict': {
            'id': '79cb9b0e-a64b-4485-8a44-47f36b292e4c',
            'ext': 'mp4',
            'title': 'Panda Video - Hospedagem de video',
        },
    }, {
        # Direct Link to video
        'url': 'https://player-vz-ded14ebd-85a.tv.pandavideo.com.br/embed/?v=2bf42e2c-e804-4637-94c3-81f0b06dc64d',
        'info_dict': {
            'id': '2bf42e2c-e804-4637-94c3-81f0b06dc64d',
            'ext': 'mp4',
            'title': 'Panda Video - Hospedagem de video',
        },
    }, {
        # Invalid Link to video
        'url': 'https://player-vz-ded14ebd-85a.tv.pandavideo.com.br/embed/?v=2bf42e2c-e804-4637-94c3',
        'info_dict': {
            'id': '2bf42e2c-e804-4637-94c3',
            'ext': 'mp4',
            'title': '',
        },
    }, {
        # Direct Link to video
        'url': 'https://player-vz-ded14ebd-85a.tv.pandavideo.com.br/embed/?v=3b101f05-84aa-4de0-9b64-71f1855388af',
        'info_dict': {
            'id': '3b101f05-84aa-4de0-9b64-71f1855388af',
            'ext': 'mp4',
            'title': '',
        },
    }]

    def get_formats(self, link: str) -> str:
        parts = link.split('embed/?v=')
        return ''.join(parts) + '/playlist.m3u8'

    def _real_extract(self, url: str) -> dict:
        video_id = self._match_id(url)

        formats = self._extract_m3u8_formats(self.get_formats(url), video_id)
        webpage = self._download_webpage(url, video_id)
        title = self._html_search_regex(
            r'<title>([^<]+)</title>', webpage, 'title', default=None, fatal=False)
        description = self._html_search_regex(
            r'<meta name=["\']description["\'] content=["\']([^"\']+)["\']',
            webpage, 'description', default=None, fatal=False)
        return {
            'id': video_id,
            'url': url,
            'title': title,
            'description': description,
            'ext': 'mp4',
            'formats': formats,
        }
