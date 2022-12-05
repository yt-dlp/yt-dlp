from codecs import decode

from .common import InfoExtractor


class WebcameraplIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<id>[^\.]+)\.webcamera\.pl/?'
    _TESTS = [{
        'url': 'https://warszawa-plac-zamkowy.webcamera.pl',
        'info_dict': {
            'id': 'warszawa-plac-zamkowy',
            'ext': 'mp4',
            'title': 'WIDOK NA PLAC ZAMKOWY W WARSZAWIE',
        }
    }, {
        'url': 'https://gdansk-stare-miasto.webcamera.pl/',
        'info_dict': {
            'id': 'gdansk-stare-miasto',
            'ext': 'mp4',
            'title': 'GDAŃSK - widok na Stare Miasto'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(r'<h1.*?>(.+?)</h1>', webpage, 'title')

        rot13_m3u8_url = self._search_regex(r'data-src="(uggc.+?\.z3h8)"', webpage, 'm3u8 url', fatal=False)
        if not rot13_m3u8_url:
            self.raise_no_formats('No video/audio found at the provided url.', expected=True)
        m3u8_url = decode(rot13_m3u8_url, 'rot-13')

        formats = self._extract_m3u8_formats(m3u8_url, video_id, ext='mp4')

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'url': m3u8_url,
            'ext': 'mp4',
        }
