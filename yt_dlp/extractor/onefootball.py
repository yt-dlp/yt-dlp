from .common import InfoExtractor


class OneFootballIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?onefootball\.com/[a-z]{2}/video/[^/&?#]+-(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://onefootball.com/en/video/highlights-fc-zuerich-3-3-fc-basel-34012334',
        'info_dict': {
            'id': '34012334',
            'ext': 'mp4',
            'title': 'Highlights: FC Zürich 3-3 FC Basel',
            'description': 'md5:33d9855cb790702c4fe42a513700aba8',
            'thumbnail': 'https://photobooth-api.onefootball.com/api/screenshot/https:%2F%2Fperegrine-api.onefootball.com%2Fv2%2Fphotobooth%2Fcms%2Fen%2F34012334',
            'timestamp': 1635874604,
            'upload_date': '20211102'
        },
        'params': {'skip_download': True}
    }, {
        'url': 'https://onefootball.com/en/video/klopp-fumes-at-var-decisions-in-west-ham-defeat-34041020',
        'info_dict': {
            'id': '34041020',
            'ext': 'mp4',
            'title': 'Klopp fumes at VAR decisions in West Ham defeat',
            'description': 'md5:9c50371095a01ad3f63311c73d8f51a5',
            'thumbnail': 'https://photobooth-api.onefootball.com/api/screenshot/https:%2F%2Fperegrine-api.onefootball.com%2Fv2%2Fphotobooth%2Fcms%2Fen%2F34041020',
            'timestamp': 1636314103,
            'upload_date': '20211107'
        },
        'params': {'skip_download': True}
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        webpage = self._download_webpage(url, id)
        data_json = self._search_json_ld(webpage, id)
        m3u8_url = self._html_search_regex(r'(https://cdn\.jwplayer\.com/manifests/.+\.m3u8)', webpage, 'm3u8_url')
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(m3u8_url, id)
        self._sort_formats(formats)
        return {
            'id': id,
            'title': data_json.get('title'),
            'description': data_json.get('description'),
            'thumbnail': data_json.get('thumbnail'),
            'timestamp': data_json.get('timestamp'),
            'formats': formats,
            'subtitles': subtitles,
        }
