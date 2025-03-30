import datetime
import json

from .common import InfoExtractor


class IvooxIE(InfoExtractor):
    _VALID_URL = (
        r'https?://(?:www\.)?ivoox\.com/.*_rf_(?P<id>[0-9]+)_1\.html',
        r'https?://go\.ivoox\.com/rf/(?P<id>[0-9]+)',
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
            },
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
            },
        },
    ]

    def _real_extract(self, url):
        media_id = self._match_id(url)
        webpage = self._download_webpage(url, media_id)

        # Set the 'defaults' for the data we want to extract
        date = None
        timestamp = None
        author = None
        channel = None
        title = None
        thumbnail = None
        description = None

        # This platform embeds a JSON document with a lot of the chapter
        # information there; Try getting all the info from here first
        embedded_pattern = r'>({"@context":"https://schema.org/","@type":"PodcastEpisode".+?)</script>',
        embedded_metadata = self._html_search_regex(embedded_pattern, webpage, 'embedded metadata')
        try:
            metadata = json.loads(embedded_metadata)
            if metadata['@type'] == 'PodcastEpisode':
                title = metadata['name']
                thumbnail = metadata['image']
                description = metadata['description']
                y, m, d = metadata['datePublished'].split('-')
                date = datetime.datetime(int(y), int(m), int(d))
                timestamp = int(datetime.datetime.timestamp(date))
                if metadata.get('partOfSeries'):
                    channel = metadata['partOfSeries']['name']
        except Exception as e:
            self.report_warning(f'Failed to extract embedded json; Reason: {e}', media_id)

        # Fallback extraction of the the podcast info
        if date is None:
            self.report_warning('Fallback extration of date', media_id)
            date = datetime.datetime.fromisoformat(self._html_search_regex(r'data-prm-pubdate="(.+?)"', webpage, 'title'))
            timestamp = int(datetime.datetime.timestamp(date))
        if author is None:
            # Author uses fallback since it is not explicitly embedded elsewhere
            #self.report_warning('Fallback extration of author', media_id)
            author = self._html_search_regex(r'data-prm-author="(.+?)"', webpage, 'author')
        if channel is None:
            self.report_warning('Fallback extration of channel', media_id)
            channel = self._html_search_regex(r'data-prm-podname="(.+?)"', webpage, 'channel')
        if title is None:
            self.report_warning('Fallback extration of title', media_id)
            title = self._html_search_regex(r'data-prm-title="(.+?)"', webpage, 'title')
        if thumbnail is None:
            self.report_warning('Fallback extration of thumbnail', media_id, 'thumbnail')
            thumbnail = self._og_search_thumbnail(webpage)
        if description is None:
            self.report_warning('Fallback extration of description', media_id, 'description')
            description = self._og_search_description(webpage)

        # Extract the download URL
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'identity',
            'Origin': 'https://www.ivoox.com',
            'Referer': 'https://www.ivoox.com/',
            'Priority': 'u=1, i',
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
                'http_headers': headers,
            },
        ]

        return {
            'id': media_id,
            'title': title,
            'thumbnail': thumbnail,
            'uploader': author,
            'channel': channel,
            'timestamp': timestamp,
            'description': description,
            'formats': formats,
        }
