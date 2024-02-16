from .common import InfoExtractor
from .jwplatform import JWPlatformIE
from ..utils import make_archive_id


class OneFootballIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?onefootball\.com/[a-z]{2}/video/[^/&?#]+-(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://onefootball.com/en/video/highlights-fc-zuerich-3-3-fc-basel-34012334',
        'info_dict': {
            'id': 'Y2VtcWAT',
            'ext': 'mp4',
            'title': 'Highlights: FC Zürich 3-3 FC Basel',
            'description': 'md5:33d9855cb790702c4fe42a513700aba8',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/Y2VtcWAT/poster.jpg?width=720',
            'timestamp': 1635874895,
            'upload_date': '20211102',
            'duration': 375.0,
            'tags': ['Football', 'Soccer', 'OneFootball'],
            '_old_archive_ids': ['onefootball 34012334'],
        },
        'params': {'skip_download': True},
        'expected_warnings': ['Failed to download m3u8 information'],
    }, {
        'url': 'https://onefootball.com/en/video/klopp-fumes-at-var-decisions-in-west-ham-defeat-34041020',
        'info_dict': {
            'id': 'leVJrMho',
            'ext': 'mp4',
            'title': 'Klopp fumes at VAR decisions in West Ham defeat',
            'description': 'md5:9c50371095a01ad3f63311c73d8f51a5',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/leVJrMho/poster.jpg?width=720',
            'timestamp': 1636315232,
            'upload_date': '20211107',
            'duration': 93.0,
            'tags': ['Football', 'Soccer', 'OneFootball'],
            '_old_archive_ids': ['onefootball 34041020'],
        },
        'params': {'skip_download': True}
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        data_json = self._search_json_ld(webpage, video_id, fatal=False)
        data_json.pop('url', None)
        m3u8_url = self._html_search_regex(r'(https://cdn\.jwplayer\.com/manifests/\w+\.m3u8)', webpage, 'm3u8_url')

        return self.url_result(
            m3u8_url, JWPlatformIE, video_id, _old_archive_ids=[make_archive_id(self, video_id)],
            **data_json, url_transparent=True)
