import json

from .common import InfoExtractor
from ..utils import ExtractorError, clean_html, traverse_obj, unified_timestamp, url_or_none


class TvwIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tvw\.org/video/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://tvw.org/video/billy-frank-jr-statue-maquette-unveiling-ceremony-2024011211/',
        'md5': '9ceb94fe2bb7fd726f74f16356825703',
        'info_dict': {
            'id': '2024011211',
            'ext': 'mp4',
            'title': 'Billy Frank Jr. Statue Maquette Unveiling Ceremony',
            'thumbnail': r're:^https?://.*\.jpg$',
            'description': 'md5:58a8150017d985b4f377e11ee8f6f36e',
            'timestamp': 1704902400,
            'upload_date': '20240110',
            'location': 'Legislative Building',
        }}, {
        'url': 'https://tvw.org/video/ebeys-landing-state-park-2024081007/',
        'md5': '71e87dae3deafd65d75ff3137b9a32fc',
        'info_dict': {
            'id': '2024081007',
            'ext': 'mp4',
            'title': 'Ebey\'s Landing State Park',
            'thumbnail': r're:^https?://.*\.jpg$',
            'description': 'md5:50c5bd73bde32fa6286a008dbc853386',
            'timestamp': 1724310900,
            'upload_date': '20240822',
            'location': 'Ebey’s Landing State Park',
        }}, {
        'url': 'https://tvw.org/video/home-warranties-workgroup-2',
        'md5': 'f678789bf94d07da89809f213cf37150',
        'info_dict': {
            'id': '1999121000',
            'ext': 'mp4',
            'title': 'Home Warranties Workgroup',
            'thumbnail': r're:^https?://.*\.jpg$',
            'description': 'md5:861396cc523c9641d0dce690bc5c35f3',
            'timestamp': 946389600,
            'upload_date': '19991228',
        }}]

    def _extract_formats(self, response, video_id):
        extract_formats = lambda url, video_id: self._extract_m3u8_formats_and_subtitles(url, video_id, 'mp4')
        stream_urls = traverse_obj(response, 'streamingURIs', {
            'main': ('main', {url_or_none}),
            'backup': ('backup', {url_or_none}),
        })

        try:
            return extract_formats(stream_urls.get('main'), video_id)
        except ExtractorError:
            self.report_warning('Failed to parse the m3u8 stream. Falling back to the backup stream if it exists.')
            try:
                return extract_formats(stream_urls.get('backup'), video_id)
            except ExtractorError:
                raise

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        client_id = self._html_search_meta('clientID', webpage, fatal=True)
        video_id = self._html_search_meta('eventID', webpage, fatal=True)

        video_data = self._download_json('https://api.v3.invintus.com/v2/Event/getDetailed', video_id,
                                         headers={
                                             'authorization': 'embedder',
                                             'wsc-api-key': '7WhiEBzijpritypp8bqcU7pfU9uicDR',
                                         },
                                         data=json.dumps({
                                             'clientID': client_id,
                                             'eventID': video_id,
                                             'showStreams': True,
                                         }).encode()).get('data')

        formats, subtitles = self._extract_formats(video_data, video_id)

        return {
            'id': video_id,
            'formats': formats,
            **traverse_obj(video_data, {
                'title': ('title', {lambda x: x or self._og_search_title(webpage)}),
                'description': ('description', {lambda x: clean_html(x) or self._og_search_description(webpage)}),
                'subtitles': ('captionPath', {
                    lambda x: self._merge_subtitles({'en': [{'ext': 'vtt', 'url': x}]}, target=subtitles),
                }),
                'thumbnail': ('videoThumbnail', {url_or_none}),
                'timestamp': ('startDateTime', {unified_timestamp}),
                'location': ('locationName', {str}),
                'is_live': ('eventStatus', {lambda x: x == 'live'}),
            }),
        }
