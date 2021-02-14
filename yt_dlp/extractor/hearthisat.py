# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_urlparse
from ..utils import (
    HEADRequest,
    KNOWN_EXTENSIONS,
    sanitized_Request,
    str_to_int,
    urlencode_postdata,
    urlhandle_detect_ext,
)


class HearThisAtIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?hearthis\.at/(?P<artist>[^/]+)/(?P<title>[A-Za-z0-9\-]+)/?$'
    _PLAYLIST_URL = 'https://hearthis.at/playlist.php'
    _TESTS = [{
        'url': 'https://hearthis.at/moofi/dr-kreep',
        'md5': 'ab6ec33c8fed6556029337c7885eb4e0',
        'info_dict': {
            'id': '150939',
            'ext': 'wav',
            'title': 'Moofi - Dr. Kreep',
            'thumbnail': r're:^https?://.*\.jpg$',
            'timestamp': 1421564134,
            'description': 'Listen to Dr. Kreep by Moofi on hearthis.at - Modular, Eurorack, Mutable Intruments Braids, Valhalla-DSP',
            'upload_date': '20150118',
            'comment_count': int,
            'view_count': int,
            'like_count': int,
            'duration': 71,
            'categories': ['Experimental'],
        }
    }, {
        # 'download' link redirects to the original webpage
        'url': 'https://hearthis.at/twitchsf/dj-jim-hopkins-totally-bitchin-80s-dance-mix/',
        'md5': '5980ceb7c461605d30f1f039df160c6e',
        'info_dict': {
            'id': '811296',
            'ext': 'mp3',
            'title': 'TwitchSF - DJ Jim Hopkins -  Totally Bitchin\' 80\'s Dance Mix!',
            'description': 'Listen to DJ Jim Hopkins -  Totally Bitchin\' 80\'s Dance Mix! by TwitchSF on hearthis.at - Dance',
            'upload_date': '20160328',
            'timestamp': 1459186146,
            'thumbnail': r're:^https?://.*\.jpg$',
            'comment_count': int,
            'view_count': int,
            'like_count': int,
            'duration': 4360,
            'categories': ['Dance'],
        },
    }]

    def _real_extract(self, url):
        m = re.match(self._VALID_URL, url)
        display_id = '{artist:s} - {title:s}'.format(**m.groupdict())

        webpage = self._download_webpage(url, display_id)
        track_id = self._search_regex(
            r'intTrackId\s*=\s*(\d+)', webpage, 'track ID')

        payload = urlencode_postdata({'tracks[]': track_id})
        req = sanitized_Request(self._PLAYLIST_URL, payload)
        req.add_header('Content-type', 'application/x-www-form-urlencoded')

        track = self._download_json(req, track_id, 'Downloading playlist')[0]
        title = '{artist:s} - {title:s}'.format(**track)

        categories = None
        if track.get('category'):
            categories = [track['category']]

        description = self._og_search_description(webpage)
        thumbnail = self._og_search_thumbnail(webpage)

        meta_span = r'<span[^>]+class="%s".*?</i>([^<]+)</span>'
        view_count = str_to_int(self._search_regex(
            meta_span % 'plays_count', webpage, 'view count', fatal=False))
        like_count = str_to_int(self._search_regex(
            meta_span % 'likes_count', webpage, 'like count', fatal=False))
        comment_count = str_to_int(self._search_regex(
            meta_span % 'comment_count', webpage, 'comment count', fatal=False))
        duration = str_to_int(self._search_regex(
            r'data-length="(\d+)', webpage, 'duration', fatal=False))
        timestamp = str_to_int(self._search_regex(
            r'<span[^>]+class="calctime"[^>]+data-time="(\d+)', webpage, 'timestamp', fatal=False))

        formats = []
        mp3_url = self._search_regex(
            r'(?s)<a class="player-link"\s+(?:[a-zA-Z0-9_:-]+="[^"]+"\s+)*?data-mp3="([^"]+)"',
            webpage, 'mp3 URL', fatal=False)
        if mp3_url:
            formats.append({
                'format_id': 'mp3',
                'vcodec': 'none',
                'acodec': 'mp3',
                'url': mp3_url,
            })
        download_path = self._search_regex(
            r'<a class="[^"]*download_fct[^"]*"\s+href="([^"]+)"',
            webpage, 'download URL', default=None)
        if download_path:
            download_url = compat_urlparse.urljoin(url, download_path)
            ext_req = HEADRequest(download_url)
            ext_handle = self._request_webpage(
                ext_req, display_id, note='Determining extension')
            ext = urlhandle_detect_ext(ext_handle)
            if ext in KNOWN_EXTENSIONS:
                formats.append({
                    'format_id': 'download',
                    'vcodec': 'none',
                    'ext': ext,
                    'url': download_url,
                    'preference': 2,  # Usually better quality
                })
        self._sort_formats(formats)

        return {
            'id': track_id,
            'display_id': display_id,
            'title': title,
            'formats': formats,
            'thumbnail': thumbnail,
            'description': description,
            'duration': duration,
            'timestamp': timestamp,
            'view_count': view_count,
            'comment_count': comment_count,
            'like_count': like_count,
            'categories': categories,
        }
