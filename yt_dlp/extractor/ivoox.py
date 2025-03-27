from .common import InfoExtractor
from datetime import datetime
import json

class IvooxIE(InfoExtractor):
    _VALID_URL = (
        r'https?://(?:www\.)?ivoox\.com/.*_rf_(?P<id>[0-9]+)_1\.html',
        r'https?://go\.ivoox\.com/rf/(?P<id>[0-9]+)'
    )
    _TESTS = [
    {
        'url': 'https://www.ivoox.com/dex-08x30-rostros-del-mal-los-asesinos-en-audios-mp3_rf_143594959_1.html',
        'md5': 'f3cc6b8db8995e0c95604deb6a8f0f2f',
        'info_dict': {
            # For videos, only the 'id' and 'ext' fields are required to RUN the test:
            'id': '143594959',
            'ext': 'mp3',
            'timestamp': 1742727600,
            'author': 'Santiago Camacho',
            'channel': 'DIAS EXTRAÑOS con Santiago Camacho',
            'title': 'DEx 08x30 Rostros del mal: Los asesinos en serie que aterrorizaron España',
        }
    },
    {
        'url': 'https://go.ivoox.com/rf/143594959',
        'md5': 'f3cc6b8db8995e0c95604deb6a8f0f2f',
        'info_dict': {
            # For videos, only the 'id' and 'ext' fields are required to RUN the test:
            'id': '143594959',
            'ext': 'mp3',
            'timestamp': 1742727600,
            'author': 'Santiago Camacho',
            'channel': 'DIAS EXTRAÑOS con Santiago Camacho',
            'title': 'DEx 08x30 Rostros del mal: Los asesinos en serie que aterrorizaron España',
        }
    },
    ]

    def _real_extract(self, url):
        media_id = self._match_id(url)
        webpage = self._download_webpage(url, media_id)

        # Extract the podcast info
        date = datetime.fromisoformat(self._html_search_regex(r'data-prm-pubdate="(.+?)"', webpage, 'title'))
        timestamp = int(datetime.timestamp(date))
        author = self._html_search_regex(r'data-prm-author="(.+?)"', webpage, 'title')
        podcast = self._html_search_regex(r'data-prm-podname="(.+?)"', webpage, 'title')
        title = self._html_search_regex(r'data-prm-title="(.+?)"', webpage, 'title')

        # Extract the download URL
        headers={
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'identity',
            'Origin': 'https://www.ivoox.com',
            'Referer': 'https://www.ivoox.com/',
            'Priority': 'u=1, i'
        }
        metadata_url = f'https://vcore-web.ivoox.com/v1/public/audios/{media_id}/download-url'
        download_json = self._download_json(metadata_url, media_id, headers=headers)
        download_url = download_json['data']['downloadUrl']
        url = f'https://ivoox.com{download_url}'

        # Formats
        formats = [
            {
                'url': url,
                'ext': 'mp3',
                'format_id': 'mp3_default',
                'http_headers': headers
            }
        ]

        return {
            'id': media_id,
            'title': title,
            'uploader': author,
            'channel': podcast,
            'timestamp': timestamp,
            'description': self._og_search_description(webpage),
            'formats': formats,
        }