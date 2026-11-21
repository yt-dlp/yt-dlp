import re

from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import (
    determine_ext,
    extract_attributes,
    get_elements_by_class,
    int_or_none,
    urlhandle_detect_ext,
    urljoin,
)


class UrortPlaylistIE(InfoExtractor):
    IE_DESC = 'NRK P3 Urørt Playlist'
    _VALID_URL = r'https?://(?:www\.)?urort\.p3\.no/(?:artist|playlist)/(?P<id>[^/?#]+)$'

    _TESTS = [{
        'note': 'artist playlist',
        'url': 'https://urort.p3.no/artist/Gerilja',
        'info_dict': {
            'id': str,
            'title': 'Gerilja',
            'description': 'Hør Gerilja\'s låter på Urørt netsiden | ',
        },
        'playlist_mincount': 10,
    }, {
        'note': 'track playlist',
        'url': 'https://urort.p3.no/playlist/rock',
        'info_dict': {
            'id': str,
            'title': 'Rock/metall',
            'description': 'Anbefalte låter i sjangeren rock/metall | NRK P3 Urørt',
        },
        'playlist_mincount': 100,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)
        playlist_divs = get_elements_by_class('list-track-artist', webpage)
        if not playlist_divs:
            playlist_divs = get_elements_by_class('list-track-container', webpage)
        track_containers = []
        if playlist_divs:
            track_containers = get_elements_by_class('track-container', playlist_divs[0])
        if not track_containers:
            return {}
        entries = []
        for track_container in track_containers:
            info_divs = get_elements_by_class('info', track_container)
            title_divs = get_elements_by_class('title', info_divs[0])
            entries.extend([self.url_result(
                urljoin(url, x)) for x in re.findall(r'<a[^>]+href="([^"]+)"', title_divs[0])])
        return self.playlist_result(entries, playlist_id,
                                    self._og_search_title(webpage).replace(' | NRK P3 Urørt', ''),
                                    description=self._og_search_description(webpage))


class UrortIE(InfoExtractor):
    IE_DESC = 'NRK P3 Urørt'
    _VALID_URL = r'https?://(?:www\.)?urort\.p3\.no/track/[^/]+/(?P<id>[^/&?#$]+)'

    _TESTS = [{
        'note': 'MP4 AAC and default empty PNG thunbnail',
        'url': 'https://urort.p3.no/track/Gerilja/the-bomb',
        'md5': '9eee22c88598e285a3b4fa06ac387f79',
        'info_dict': {
            'id': '1356',
            'display_id': 'the-bomb',
            'ext': 'm4a',
            'title': 'Gerilja: The Bomb',
            'thumbnail': r're:^https?://.+\.(jpg|png)',
        },
    }, {
        'note': 'MP3 and custom thunbnail',
        'url': 'https://urort.p3.no/track/lokal-politikk/svarteper-1',
        'md5': 'b9cc2b97820016a89b1140f11cf78fac',
        'info_dict': {
            'id': '191567',
            'display_id': 'svarteper-1',
            'ext': 'mp3',
            'title': 'Lokal Politikk : Svarteper',
            'thumbnail': r're:^https?://',
        },
    }, {
        'note': 'WAV and custom thunbnail',
        'url': 'https://urort.p3.no/track/girl-group/shut-your-mouth-sometimes',
        'md5': '625873985ccdbbc37d05078d8927a522',
        'info_dict': {
            'id': '224148',
            'display_id': 'shut-your-mouth-sometimes',
            'ext': 'wav',
            'title': 'Girl Group: Shut Your Mouth (Sometimes) ',
            'thumbnail': r're:^https?://',
        },
    }]

    def _real_extract(self, url):
        title_id = self._match_id(url)
        webpage = self._download_webpage(url, title_id)
        track_info_divs = get_elements_by_class('track-info-page track', webpage)
        cover_divs = get_elements_by_class('cover-page', track_info_divs[0])
        if cover_divs:
            thumbnail = self._search_regex(
                r'<img[^>]+\bsrc=(["\'])(?P<value>(?:(?!\1).)+)\1', cover_divs[0], 'thumbnail',
                default=None, group='value') or self._html_search_meta(
                    ['og:image', 'twitter:image'], webpage, 'thumbnail', default=None)

        track_info_div = self._search_regex(r'(<div[^>]+\bclass="[^"]*track-info["\s][^>]*>)',
                                            track_info_divs[0], 'media URL', default=None)
        video_url = extract_attributes(track_info_div)['data-trackurl']
        video_id = extract_attributes(track_info_div).get('data-trackid') or title_id

        # usually no media type known or extension found
        ext = determine_ext(video_url)
        filesize = None
        if ext == 'unknown_video':
            urlh = self._request_webpage(
                HEADRequest(video_url), video_id, fatal=False, note='Checking media type')
            if urlh and urlh.status == 200:
                ext = urlhandle_detect_ext(urlh)
                filesize = int_or_none(urlh.headers.get('Content-Length', None))

        return {
            'display_id': title_id,
            'id': video_id,
            'url': video_url,
            'ext': ext,
            'filesize': filesize,
            'title': self._og_search_title(webpage).replace(' | NRK P3 Urørt', ''),
            'thumbnail': thumbnail,
        }
