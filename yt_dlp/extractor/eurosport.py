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
    }]
    _TOKEN = None
    # actually defined in https://netsport.eurosport.io/?variables={"databaseId":<databaseId>,"playoutType":"VDP"}&extensions={"persistedQuery":{"version":1 ..
    # but this method require to get sha256 hash
    _GEO_COUNTRIES = ['de', 'lb', 'nl', 'it', 'fr', 'gb', 'eu']  # this is not complete list but countries in EU should work

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
            # actually they also serve mss, but i don't know how to extract that
            if stream_type == "hls":
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    traverse_obj(json_data, ('attributes', 'streaming', stream_type, 'url')), display_id, ext='mp4')
            elif stream_type == "dash":
                fmts, subs = self._extract_mpd_formats_and_subtitles(
                    traverse_obj(json_data, ('attributes', 'streaming', stream_type, 'url')), display_id)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        self._sort_formats(formats)

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
