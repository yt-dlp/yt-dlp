import re

from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import (
    determine_ext,
    extract_attributes,
    get_elements_by_class,
    urlhandle_detect_ext,
    urljoin,
)


class UrortPlaylistIE(InfoExtractor):
    IE_DESC = 'NRK P3 Urørt Playlist'
    _VALID_URL = r'https?://(?:www\.)?urort\.p3\.no/(?:artist|playlist)/(?P<id>[^/?#]+)$'

    # FIXME: make a proper playlist test
    _TEST = {
        'url': 'https://urort.p3.no/artist/Gerilja',
        'md5': '5ed31a924be8a05e47812678a86e127b',
        'info_dict': {
            'id': '33124-24',
            'ext': 'mp3',
            'title': 'The Bomb',
            'thumbnail': r're:^https?://.+\.jpg',
            'uploader': 'Gerilja',
            'uploader_id': 'Gerilja',
            'upload_date': '20100323',
        },
        'params': {
            'matchtitle': '^The Bomb$',  # To test, we want just one video
        },
    }

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

        return {
            '_type': 'playlist',
            'id': playlist_id,
            'entries': entries,
            'title': self._og_search_title(webpage).replace(' | NRK P3 Urørt', ''),
        }


class UrortIE(InfoExtractor):
    IE_DESC = 'NRK P3 Urørt'
    _VALID_URL = r'https?://(?:www\.)?urort\.p3\.no/track/[^/]+/(?P<id>[^/&?#$]+)'

    _TEST = {
        'url': 'https://urort.p3.no/track/Gerilja/the-bomb',
        'md5': '5ed31a924be8a05e47812678a86e127b',
        'info_dict': {
            'id': '33124-24',
            'ext': 'mp3',
            'title': 'The Bomb',
            'thumbnail': r're:^https?://.+\.jpg',
            'uploader': 'Gerilja',
            'uploader_id': 'Gerilja',
            'upload_date': '20100323',
        },
        'params': {
            'matchtitle': '^The Bomb$',  # To test, we want just one video
        },
    }

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
        if ext == 'unknown_video':
            urlh = self._request_webpage(
                HEADRequest(video_url), video_id, fatal=False, note='Checking media type')
            if urlh and urlh.status == 200:
                ext = urlhandle_detect_ext(urlh)

        return {
            'display_id': title_id,
            'id': video_id,
            'url': video_url,
            'ext': ext,
            'title': self._og_search_title(webpage).replace(' | NRK P3 Urørt', ''),
            'thumbnail': thumbnail,
        }
