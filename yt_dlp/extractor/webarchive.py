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
    _VALID_URL = r"""(?x)^
                (?:https?://|//)?web\.archive\.org\/
                    (?:web/)? 
                    (?:[0-9A-Za-z_*]+/)? # /web and the version index is optional
                (?:https?:\/\/)?
                (?:
                    (?:\w+\.)?youtube\.com\/watch\?v= # Youtube URL
                    |(wayback-fakeurl\.archive\.org\/yt\/) # Or optionally, also support the internal fake url
                )    
                (?P<id>[0-9A-Za-z_-]{11})(?(1).+)?(?:\#|&|$)
                """

    _INTERNAL_URL_TEMPLATE = "https://web.archive.org/web/2oe_/http://wayback-fakeurl.archive.org/yt/%s"
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

    def _real_extract(self, url):
        video_id = self._match_id(url)
        # Use link translator mentioned in https://github.com/ytdl-org/youtube-dl/issues/13655
        internal_fake_url = self._INTERNAL_URL_TEMPLATE % video_id
        video_file_webpage = self._request_webpage(
            HEADRequest(internal_fake_url), video_id, errnote="Video is not archived or issue with web.archive.org")
        video_file_url = compat_urllib_parse_unquote(video_file_webpage.url)
        video_file_url_qs = compat_parse_qs(compat_urlparse.urlparse(video_file_url).query)

        # Attempt to recover any ext & format info from playback url
        format = {'url': video_file_url}
        itag = try_get(video_file_url_qs, lambda x: x['itag'][0])
        if itag and itag in YoutubeIE._formats:
            format.update(YoutubeIE._formats[itag])
            format.update({'format_id': itag})
        else:
            mime = try_get(video_file_url_qs, lambda x: x['mime'][0])
            ext = mimetype2ext(mime) or determine_ext(video_file_url)
            format.update({'ext': ext})
        return {
            'id': video_id,
            'title': None,  # In this case we are not able to get a title reliably.
            'formats': [format],
            'webpage_url': url,
            'duration': str_to_int(try_get(video_file_url_qs, lambda x: x['dur'][0]))
        }
