# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class YoutubeWebArchiveIE(InfoExtractor):
    # TODO
    # - Regex needs a lot more work
    #       fails on: https://web.archive.org/web/20120712231619oe/https://www.youtube.com/watch?v=AkhihxRKcrs (the date id can be anything, even *)
    #       also fails on anything after the video id (e.g. playlist)
    # - Format - this is not always MP4
    #       The format is sometimes present in the videoplayback url
    #       Possibly could do a HEAD request to the fakeurl.archive.org to get the archived videoplayback url, and extract from there
    # - Put this in archiveorg.py
    # - Tests for videos that are archived but not on Youtube
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
        # Use link translator mentioned in https://github.com/ytdl-org/youtube-dl/issues/13655
        video_url = "https://web.archive.org/web/2oe_/http://wayback-fakeurl.archive.org/yt/" + video_id
        return {
            'url': video_url,
            'title': None,
            'id': video_id,
            'ext': None,
            'ie_key': 'YoutubeWebArchive'
        }
