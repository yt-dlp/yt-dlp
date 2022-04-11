import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    sanitized_Request,
    urlencode_postdata,
    xpath_text,
    xpath_with_ns,
)

_x = lambda p: xpath_with_ns(p, {'xspf': 'http://xspf.org/ns/0/'})


class NosVideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?nosvideo\.com/' + \
                 r'(?:embed/|\?v=)(?P<id>[A-Za-z0-9]{12})/?'
    _PLAYLIST_URL = 'http://nosvideo.com/xml/{xml_id:s}.xml'
    _FILE_DELETED_REGEX = r'<b>File Not Found</b>'
    _TEST = {
        'url': 'http://nosvideo.com/?v=mu8fle7g7rpq',
        'md5': '6124ed47130d8be3eacae635b071e6b6',
        'info_dict': {
            'id': 'mu8fle7g7rpq',
            'ext': 'mp4',
            'title': 'big_buck_bunny_480p_surround-fix.avi.mp4',
            'thumbnail': r're:^https?://.*\.jpg$',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        fields = {
            'id': video_id,
            'op': 'download1',
            'method_free': 'Continue to Video',
        }
        req = sanitized_Request(url, urlencode_postdata(fields))
        req.add_header('Content-type', 'application/x-www-form-urlencoded')
        webpage = self._download_webpage(req, video_id,
                                         'Downloading download page')
        if re.search(self._FILE_DELETED_REGEX, webpage) is not None:
            raise ExtractorError('Video %s does not exist' % video_id,
                                 expected=True)

        xml_id = self._search_regex(r'php\|([^\|]+)\|', webpage, 'XML ID')
        playlist_url = self._PLAYLIST_URL.format(xml_id=xml_id)
        playlist = self._download_xml(playlist_url, video_id)

        track = playlist.find(_x('.//xspf:track'))
        if track is None:
            raise ExtractorError(
                'XML playlist is missing the \'track\' element',
                expected=True)
        title = xpath_text(track, _x('./xspf:title'), 'title')
        url = xpath_text(track, _x('./xspf:file'), 'URL', fatal=True)
        thumbnail = xpath_text(track, _x('./xspf:image'), 'thumbnail')
        if title is not None:
            title = title.strip()

        formats = [{
            'format_id': 'sd',
            'url': url,
        }]

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'formats': formats,
        }
