from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    parse_duration,
)


class MojvideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?mojvideo\.com/video-(?P<display_id>[^/]+)/(?P<id>[a-f0-9]+)'
    _TEST = {
        'url': 'http://www.mojvideo.com/video-v-avtu-pred-mano-rdecelaska-alfi-nipic/3d1ed4497707730b2906',
        'md5': 'f7fd662cc8ce2be107b0d4f2c0483ae7',
        'info_dict': {
            'id': '3d1ed4497707730b2906',
            'display_id': 'v-avtu-pred-mano-rdecelaska-alfi-nipic',
            'ext': 'mp4',
            'title': 'V avtu pred mano rdečelaska - Alfi Nipič',
            'thumbnail': r're:^http://.*\.jpg$',
            'duration': 242,
        }
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        display_id = mobj.group('display_id')

        # XML is malformed
        playerapi = self._download_webpage(
            'http://www.mojvideo.com/playerapi.php?v=%s&t=1' % video_id, display_id)

        if '<error>true</error>' in playerapi:
            error_desc = self._html_search_regex(
                r'<errordesc>([^<]*)</errordesc>', playerapi, 'error description', fatal=False)
            raise ExtractorError('%s said: %s' % (self.IE_NAME, error_desc), expected=True)

        title = self._html_extract_title(playerapi)
        video_url = self._html_search_regex(
            r'<file>([^<]+)</file>', playerapi, 'video URL')
        thumbnail = self._html_search_regex(
            r'<preview>([^<]+)</preview>', playerapi, 'thumbnail', fatal=False)
        duration = parse_duration(self._html_search_regex(
            r'<duration>([^<]+)</duration>', playerapi, 'duration', fatal=False))

        return {
            'id': video_id,
            'display_id': display_id,
            'url': video_url,
            'title': title,
            'thumbnail': thumbnail,
            'duration': duration,
        }
