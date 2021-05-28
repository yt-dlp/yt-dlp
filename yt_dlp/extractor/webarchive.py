# coding: utf-8
from __future__ import unicode_literals
from .common import InfoExtractor
from .youtube import YoutubeIE
from compat import (
    compat_urllib_parse_unquote,
    compat_urlparse,compat_parse_qs
)
from ..utils import (
    determine_ext,
    HEADRequest,
    mimetype2ext,
    str_to_int,
    try_get
)


class YoutubeWebArchiveIE(InfoExtractor):
    # TODO
    # - Regex needs a lot more work
    #       * fails on: https://web.archive.org/web/20120712231619oe/https://www.youtube.com/watch?v=AkhihxRKcrs (the date id can be anything, even *)
    #       * also fails on anything after the video id (e.g. &list)
    #       * support http://wayback-fakeurl.archive.org/yt/<video id> urls too
    # - Put in archiveorg.py
    _VALID_URL = r'https?:\/\/(?:www\.)?web\.archive\.org\/web\/([0-9]+)\/https?:\/\/(?:www\.)?youtube\.com\/watch\?v=(?P<id>[0-9A-Za-z_-]{1,11})$'
    # _TEST = {
    #     'url': 'https://web.archive.org/web/20150415002341/https://www.youtube.com/watch?v=aYAGB11YrSs',
    #     'md5': 'ec44dc1177ae37189a8606d4ca1113ae',
    #     'info_dict': {
    #         'url': 'https://web.archive.org/web/2oe_/http://wayback-fakeurl.archive.org/yt/aYAGB11YrSs',
    #         'id': 'aYAGB11YrSs',
    #         'ext': 'mp4',
    #     },
    #}
    # https://web.archive.org/web/20120712202131/http://www.youtube.com/watch?v=Y2FzcnAaYiM&gl=US&hl=en
    # also test on very old videos (<2010)

    _WAYBACK_FAKEURL = "https://web.archive.org/web/2oe_/http://wayback-fakeurl.archive.org/yt/"

    def _real_extract(self, url):
        # Get video ID and page
        video_id = self._match_id(url)
        # Use link translator mentioned in https://github.com/ytdl-org/youtube-dl/issues/13655
        video_url = self._WAYBACK_FAKEURL + video_id
        file_webpage = self._request_webpage(
            HEADRequest(video_url), video_id, errnote="video not archived or issue with web.archive.org")
        file_url = compat_urllib_parse_unquote(file_webpage.url)
        file_url_qs = compat_parse_qs(compat_urlparse.urlparse(file_url).query)

        # Attempt to recover any ext & format info from playback url
        itag = try_get(file_url_qs, lambda x: x['itag'][0])
        format = {'url': file_url}
        if itag and itag in YoutubeIE._formats:
            format.update(YoutubeIE._formats[itag])
            format.update({'format_id': itag})
        else:
            mime = try_get(file_url_qs, lambda x: x['mime'][0])
            ext = mimetype2ext(mime) or determine_ext(video_url)
            format.update({'ext': ext})
        return {
            'id': video_id,
            'title': None,
            'formats': [format],
            'webpage_url': url,
            'duration': str_to_int(try_get(file_url_qs, lambda x: x['dur'][0]))
        }
