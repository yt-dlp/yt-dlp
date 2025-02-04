import json

from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import ExtractorError, RegexNotFoundError, clean_html, traverse_obj, unified_timestamp


class TVWIE(InfoExtractor):
    BACKUP_API_KEY = '7WhiEBzijpritypp8bqcU7pfU9uicDR'

    _VALID_URL = r'https?://(?:www\.)?tvw\.org/video/(?P<slug>.+)-(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://tvw.org/video/billy-frank-jr-statue-maquette-unveiling-ceremony-2024011211/',
        'md5': '9ceb94fe2bb7fd726f74f16356825703',
        'info_dict': {
            'id': '2024011211',
            'display_id': 'billy-frank-jr-statue-maquette-unveiling-ceremony',
            'ext': 'mp4',
            'title': 'Billy Frank Jr. Statue Maquette Unveiling Ceremony',
            'thumbnail': r're:https?://invintus-client-images\.s3\.amazonaws\.com/.*\.jpg$',
            'description': 'md5:58a8150017d985b4f377e11ee8f6f36e',
            'timestamp': 1704902400,
            'upload_date': '20240110',
            'location': 'Legislative Building',
        }}, {
        'url': 'https://tvw.org/video/ebeys-landing-state-park-2024081007/',
        'md5': '71e87dae3deafd65d75ff3137b9a32fc',
        'info_dict': {
            'id': '2024081007',
            'display_id': 'ebeys-landing-state-park',
            'ext': 'mp4',
            'title': 'Ebey\'s Landing State Park',
            'thumbnail': r're:https?://invintus-client-images\.s3\.amazonaws\.com/.*\.jpg$',
            'description': 'md5:50c5bd73bde32fa6286a008dbc853386',
            'timestamp': 1724310900,
            'upload_date': '20240822',
            'location': 'Ebey’s Landing State Park',
        },
    }]

    def _get_subtitles(self, response):
        return {'en': [{'ext': 'vtt', 'url': response.get('captionPath')}]}

    def _get_thumbnail(self, response):
        return [{'url': response.get('videoThumbnail')}]

    def _get_description(self, response):
        return clean_html(response.get('description'))

    def _get_js_code(self, video_id, webpage):
        app_js_url = self._html_search_regex(
            r'<script[^>]+src=[\"\'](?P<app_js>.+?)[\"\'][^>]* id=\"invintus-app-js\">[^>]*</script>',
            webpage, 'app_js')
        return self._download_webpage(app_js_url, video_id, 'Downloading app.js API key')

    def _extract_formats(self, response, video_id, stream_url):
        extract_formats = lambda url, video_id: self._extract_m3u8_formats(url, video_id, 'mp4')

        try:
            return extract_formats(stream_url, video_id)
        except ExtractorError:
            self.report_warning('Failed to parse the m3u8 stream. Falling back to the backup stream if it exists.')
            try:
                stream_url = traverse_obj(response, ('streamingURIs', 'backup'))
                return extract_formats(stream_url, video_id)
            except ExtractorError:
                raise

    def _real_extract(self, url):
        video_id = self._match_id(url)
        slug = self._match_valid_url(url).group('slug')
        webpage = self._download_webpage(url, video_id)

        app_js_code = self._get_js_code(video_id, webpage)

        try:
            api_key = self._search_regex(r'embedderAuth[\s]*:[\s]*{[^}]+vendorKey:\"(?P<token>\w+?)\"}',
                                         app_js_code, 'token')
        except RegexNotFoundError:
            self.report_warning('Failed to extract the API key. Falling back to a hardcoded key.')
            api_key = self.BACKUP_API_KEY

        client_id = self._html_search_meta('clientID', webpage)

        try:
            headers = {'authorization': 'embedder', 'wsc-api-key': api_key}
            data = json.dumps({'clientID': client_id, 'eventID': video_id,
                               'showStreams': True}).encode('utf8')
            response = self._download_json('https://api.v3.invintus.com/v2/Event/getDetailed',
                                           video_id, headers=headers, data=data).get('data')
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError):
                self.write_debug(e.cause)
                response = self._parse_json(e.cause.response.read().decode(), video_id)['errors']
                if response['hasError'] is True:
                    raise ExtractorError('{} said: {}'.format(self.IE_NAME, response['error']), expected=True)
            raise

        stream_url = traverse_obj(response, ('streamingURIs', 'main'))
        formats = self._extract_formats(response, video_id, stream_url)

        return {
            'id': video_id,
            'display_id': slug,
            'title': response.get('title') or self._og_search_title(webpage),
            'description': self._get_description(response) or self._og_search_description(webpage),
            'formats': formats,
            'thumbnail': response.get('videoThumbnail'),
            'subtitles': self.extract_subtitles(response),
            'timestamp': unified_timestamp(response.get('startDateTime')),
            'location': response.get('locationName'),
        }
