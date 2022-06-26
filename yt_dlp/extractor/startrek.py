from .common import InfoExtractor
from ..utils import int_or_none, urljoin


class StarTrekIE(InfoExtractor):
    _VALID_URL = r'(?P<base>https://(?:intl|www)\.startrek\.com)/videos/(?P<id>[^/]+)'
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
            # Thumbnail seems to have some tracking parameters added, ignore those.
            'thumbnail': r're:https://intl\.startrek\.com/sites/default/files/styles/video_1920x1080/public/images/2022-06/pp_14794_rr_thumb_107_yt_16x9.jpg(?:\?.+)?',
        }
    }]

    def _real_extract(self, url):
        urlbase, video_id = self._match_valid_url(url).group('base', 'id')
        webpage = self._download_webpage(url, video_id)

        description = self._html_search_regex(
            r'(?s)<div class="header-body">(.+?)</div>',
            webpage, 'description', fatal=False)
        json_ld = self._search_json_ld(webpage, video_id, fatal=False)

        player = self._search_regex(r'(<div id="cvp-player-[^<]+</div>)', webpage, 'player')

        hls = self._html_search_regex(r' data-hls="([^"]+)" ', player, 'HLS URL')
        title = self._html_search_regex(r' data-title="([^"]+)" ', player, 'title', json_ld.get('title'))
        duration = int_or_none(
            self._html_search_regex(r' data-duration="(\d+)" ', player, 'duration', fatal=False))
        poster = urljoin(urlbase,
                         self._html_search_regex(r' data-poster-url="([^"]+)" ', player, 'thumbnail', fatal=False))

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(hls, video_id)
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'duration': duration,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': poster,
            'timestamp': json_ld.get('timestamp'),
        }
