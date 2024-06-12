from .common import InfoExtractor
from ..utils import int_or_none, urljoin


class StarTrekIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'(?P<base>https?://(?:intl|www)\.startrek\.com)/videos/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://intl.startrek.com/videos/watch-welcoming-jess-bush-to-the-ready-room',
        'md5': '491df5035c9d4dc7f63c79caaf9c839e',
        'info_dict': {
            'id': 'watch-welcoming-jess-bush-to-the-ready-room',
            'ext': 'mp4',
            'title': 'WATCH: Welcoming Jess Bush to The Ready Room',
            'duration': 1888,
            'timestamp': 1655388000,
            'upload_date': '20220616',
            'description': 'md5:1ffee884e3920afbdd6dd04e926a1221',
            'thumbnail': r're:https://(?:intl|www)\.startrek\.com/sites/default/files/styles/video_1920x1080/public/images/2022-06/pp_14794_rr_thumb_107_yt_16x9\.jpg(?:\?.+)?',
            'subtitles': {'en-US': [{
                'url': r're:https://(?:intl|www)\.startrek\.com/sites/default/files/video/captions/2022-06/TRR_SNW_107_v4\.vtt',
            }, {
                'url': 'https://media.startrek.com/2022/06/16/2043801155561/1069981_hls/trr_snw_107_v4-c4bfc25d/stream_vtt.m3u8',
            }]},
        },
    }, {
        'url': 'https://www.startrek.com/videos/watch-ethan-peck-and-gia-sandhu-beam-down-to-the-ready-room',
        'md5': 'f5ad74fbb86e91e0882fc0a333178d1d',
        'info_dict': {
            'id': 'watch-ethan-peck-and-gia-sandhu-beam-down-to-the-ready-room',
            'ext': 'mp4',
            'title': 'WATCH: Ethan Peck and Gia Sandhu Beam Down to The Ready Room',
            'duration': 1986,
            'timestamp': 1654221600,
            'upload_date': '20220603',
            'description': 'md5:b3aa0edacfe119386567362dec8ed51b',
            'thumbnail': r're:https://www\.startrek\.com/sites/default/files/styles/video_1920x1080/public/images/2022-06/pp_14792_rr_thumb_105_yt_16x9_1.jpg(?:\?.+)?',
            'subtitles': {'en-US': [{
                'url': r're:https://(?:intl|www)\.startrek\.com/sites/default/files/video/captions/2022-06/TRR_SNW_105_v5\.vtt',
            }]},
        },
    }]

    def _real_extract(self, url):
        urlbase, video_id = self._match_valid_url(url).group('base', 'id')
        webpage = self._download_webpage(url, video_id)

        player = self._search_regex(
            r'(<\s*div\s+id\s*=\s*"cvp-player-[^<]+<\s*/div\s*>)', webpage, 'player')

        hls = self._html_search_regex(r'\bdata-hls\s*=\s*"([^"]+)"', player, 'HLS URL')
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(hls, video_id, 'mp4')

        captions = self._html_search_regex(
            r'\bdata-captions-url\s*=\s*"([^"]+)"', player, 'captions URL', fatal=False)
        if captions:
            subtitles.setdefault('en-US', [])[:0] = [{'url': urljoin(urlbase, captions)}]

        # NB: Most of the data in the json_ld is undesirable
        json_ld = self._search_json_ld(webpage, video_id, fatal=False)

        return {
            'id': video_id,
            'title': self._html_search_regex(
                r'\bdata-title\s*=\s*"([^"]+)"', player, 'title', json_ld.get('title')),
            'description': self._html_search_regex(
                r'(?s)<\s*div\s+class\s*=\s*"header-body"\s*>(.+?)<\s*/div\s*>',
                webpage, 'description', fatal=False),
            'duration': int_or_none(self._html_search_regex(
                r'\bdata-duration\s*=\s*"(\d+)"', player, 'duration', fatal=False)),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': urljoin(urlbase, self._html_search_regex(
                r'\bdata-poster-url\s*=\s*"([^"]+)"', player, 'thumbnail', fatal=False)),
            'timestamp': json_ld.get('timestamp'),
        }
