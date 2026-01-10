
from .common import InfoExtractor
from ..utils import ExtractorError


class VidmolyIE(InfoExtractor):
    IE_NAME = 'vidmoly'
    IE_DESC = 'Vidmoly video hosting'
    _VALID_URL = r'https?://(?:www\.)?vidmoly\.(?:net|to)/embed-(?P<id>[a-zA-Z0-9]+)\.html'

    _HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Origin': 'https://vidmoly.net',
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        def download(u):
            return self._download_webpage(
                u,
                video_id,
                headers={
                    **self._HEADERS,
                    'Referer': u,
                },
            )

        webpage = download(url)

        video_url = self._search_regex(
            r'file\s*:\s*"([^"]+)"',
            webpage,
            'video url',
            fatal=False,
        )
        # Page d'attente : token dans un bloc js
        if not video_url:
            token = self._search_regex(
                r'\?g=([a-f0-9]{32})',
                webpage,
                'vidmoly token',
                fatal=False,
            )
            if not token:
                raise ExtractorError('Vidmoly token not found', expected=True)

            webpage = download(f'{url}?g={token}')

            video_url = self._search_regex(
                r'file\s*:\s*"([^"]+)"',
                webpage,
                'video url',
            )

        if 'm3u8' in video_url:
            formats = self._extract_m3u8_formats(
                video_url,
                video_id,
                ext='mp4',
                headers={
                    **self._HEADERS,
                    'Referer': url,
                },
                m3u8_id='hls',
            )
        else:
            formats = [{
                'url': video_url,
                'ext': 'mp4',
                'headers': {
                    **self._HEADERS,
                    'Referer': url,
                },
            }]

        return {
            'id': video_id,
            'title': video_id,
            'formats': formats,
        }
