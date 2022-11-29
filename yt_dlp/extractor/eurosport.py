from .common import InfoExtractor
from ..utils import traverse_obj


class EurosportIE(InfoExtractor):
    _VALID_URL = r'https?://www\.eurosport\.com/\w+/[\w-]+/\d+/[\w-]+_(?P<id>vid\d+)'
    _TESTS = [{
        'url': 'https://www.eurosport.com/tennis/roland-garros/2022/highlights-rafael-nadal-brushes-aside-caper-ruud-to-win-record-extending-14th-french-open-title_vid1694147/video.shtml',
        'info_dict': {
            'id': '2480939',
            'ext': 'mp4',
            'title': 'Highlights: Rafael Nadal brushes aside Caper Ruud to win record-extending 14th French Open title',
            'description': 'md5:b564db73ecfe4b14ebbd8e62a3692c76',
            'thumbnail': 'https://imgresizer.eurosport.com/unsafe/1280x960/smart/filters:format(jpeg)/origin-imgresizer.eurosport.com/2022/06/05/3388285-69245968-2560-1440.png',
            'duration': 195.0,
            'display_id': 'vid1694147',
            'timestamp': 1654446698,
            'upload_date': '20220605',
        }
    }, {
        'url': 'https://www.eurosport.com/tennis/roland-garros/2022/watch-the-top-five-shots-from-men-s-final-as-rafael-nadal-beats-casper-ruud-to-seal-14th-french-open_vid1694283/video.shtml',
        'info_dict': {
            'id': '2481254',
            'ext': 'mp4',
            'title': 'md5:149dcc5dfb38ab7352acc008cc9fb071',
            'duration': 130.0,
            'thumbnail': 'https://imgresizer.eurosport.com/unsafe/1280x960/smart/filters:format(jpeg)/origin-imgresizer.eurosport.com/2022/06/05/3388422-69248708-2560-1440.png',
            'description': 'md5:a0c8a7f6b285e48ae8ddbe7aa85cfee6',
            'display_id': 'vid1694283',
            'timestamp': 1654456090,
            'upload_date': '20220605',
        }
    }, {
        # geo-fence but can bypassed by xff
        'url': 'https://www.eurosport.com/cycling/tour-de-france-femmes/2022/incredible-ride-marlen-reusser-storms-to-stage-4-win-at-tour-de-france-femmes_vid1722221/video.shtml',
        'info_dict': {
            'id': '2582552',
            'ext': 'mp4',
            'title': '‘Incredible ride!’ - Marlen Reusser storms to Stage 4 win at Tour de France Femmes',
            'duration': 188.0,
            'display_id': 'vid1722221',
            'timestamp': 1658936167,
            'thumbnail': 'https://imgresizer.eurosport.com/unsafe/1280x960/smart/filters:format(jpeg)/origin-imgresizer.eurosport.com/2022/07/27/3423347-69852108-2560-1440.jpg',
            'description': 'md5:32bbe3a773ac132c57fb1e8cca4b7c71',
            'upload_date': '20220727',
        }
    }]

    _TOKEN = None

    # actually defined in https://netsport.eurosport.io/?variables={"databaseId":<databaseId>,"playoutType":"VDP"}&extensions={"persistedQuery":{"version":1 ..
    # but this method require to get sha256 hash
    _GEO_COUNTRIES = ['DE', 'NL', 'EU', 'IT', 'FR']  # Not complete list but it should work

    def _real_initialize(self):
        if EurosportIE._TOKEN is None:
            EurosportIE._TOKEN = self._download_json(
                'https://eu3-prod-direct.eurosport.com/token?realm=eurosport', None,
                'Trying to get token')['data']['attributes']['token']

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        json_data = self._download_json(
            f'https://eu3-prod-direct.eurosport.com/playback/v2/videoPlaybackInfo/sourceSystemId/eurosport-{display_id}',
            display_id, query={'usePreAuth': True}, headers={'Authorization': f'Bearer {EurosportIE._TOKEN}'})['data']

        json_ld_data = self._search_json_ld(webpage, display_id)

        formats, subtitles = [], {}
        for stream_type in json_data['attributes']['streaming']:
            if stream_type == 'hls':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    traverse_obj(json_data, ('attributes', 'streaming', stream_type, 'url')), display_id, ext='mp4')
            elif stream_type == 'dash':
                fmts, subs = self._extract_mpd_formats_and_subtitles(
                    traverse_obj(json_data, ('attributes', 'streaming', stream_type, 'url')), display_id)
            elif stream_type == 'mss':
                fmts, subs = self._extract_ism_formats_and_subtitles(
                    traverse_obj(json_data, ('attributes', 'streaming', stream_type, 'url')), display_id)

            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        return {
            'id': json_data['id'],
            'title': json_ld_data.get('title') or self._og_search_title(webpage),
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': json_ld_data.get('thumbnails'),
            'description': (json_ld_data.get('description')
                            or self._html_search_meta(['og:description', 'description'], webpage)),
            'duration': json_ld_data.get('duration'),
            'timestamp': json_ld_data.get('timestamp'),
        }
