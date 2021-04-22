# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class WebArchiveIE(InfoExtractor):
    _VALID_URL = r'https?:\/\/(?:www\.)?web\.archive\.org\/web\/([0-9]+)\/https?:\/\/(?:www\.)?youtube\.com\/watch\?v=(?P<id>[0-9A-Za-z_-]{1,11})$'
    _TEST = {
        'url': 'https://web.archive.org/web/20150415002341/https://www.youtube.com/watch?v=aYAGB11YrSs',
        'md5': 'ec44dc1177ae37189a8606d4ca1113ae',
        'info_dict': {
            'url': 'https://web.archive.org/web/2oe_/http://wayback-fakeurl.archive.org/yt/aYAGB11YrSs',
            'id': 'aYAGB11YrSs',
            'ext': 'mp4',
            'title': 'Team Fortress 2 - Sandviches!',
            'author': 'Zeurel',
        }
    }

    def _real_extract(self, url):
        # Get video ID and page
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        # Extract title and author
        title = self._html_search_regex(r'<title>(.+?)</title>', webpage, 'title').strip()
        author = self._html_search_regex(r'"author":"([a-zA-Z0-9]+)"', webpage, 'author').strip()

        # Parse title
        if title.endswith(' - YouTube'):
            title = title[:-10]

        # Use link translator mentioned in https://github.com/ytdl-org/youtube-dl/issues/13655
        link_stub = "https://web.archive.org/web/2oe_/http://wayback-fakeurl.archive.org/yt/"

        # Extract hash from url
        hash_idx = url.find("watch?v=") + len("watch?v=")
        youtube_hash = url[hash_idx:]

        # If there's an ampersand, cut off before it
        ampersand = youtube_hash.find('&')
        if ampersand != -1:
            youtube_hash = youtube_hash[:ampersand]

        # Recreate the fixed pattern url and return
        reconstructed_url = link_stub + youtube_hash
        return {
            'url': reconstructed_url,
            'id': video_id,
            'title': title,
            'author': author,
            'ext': "mp4"
        }
