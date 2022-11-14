from .common import InfoExtractor
from ..compat import compat_urlparse
from ..utils import (
    fix_xml_ampersands,
    float_or_none,
    xpath_with_ns,
    xpath_text,
)


class KarriereVideosIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?karrierevideos\.at(?:/[^/]+)+/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'http://www.karrierevideos.at/berufsvideos/mittlere-hoehere-schulen/altenpflegerin',
        'info_dict': {
            'id': '32c91',
            'ext': 'flv',
            'title': 'AltenpflegerIn',
            'description': 'md5:dbadd1259fde2159a9b28667cb664ae2',
            'thumbnail': r're:^http://.*\.png',
        },
        'params': {
            # rtmp download
            'skip_download': True,
        }
    }, {
        # broken ampersands
        'url': 'http://www.karrierevideos.at/orientierung/vaeterkarenz-und-neue-chancen-fuer-muetter-baby-was-nun',
        'info_dict': {
            'id': '5sniu',
            'ext': 'flv',
            'title': 'Väterkarenz und neue Chancen für Mütter - "Baby - was nun?"',
            'description': 'md5:97092c6ad1fd7d38e9d6a5fdeb2bcc33',
            'thumbnail': r're:^http://.*\.png',
        },
        'params': {
            # rtmp download
            'skip_download': True,
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        title = (self._html_search_meta('title', webpage, default=None)
                 or self._search_regex(r'<h1 class="title">([^<]+)</h1>', webpage, 'video title'))

        video_id = self._search_regex(
            r'/config/video/(.+?)\.xml', webpage, 'video id')
        # Server returns malformed headers
        # Force Accept-Encoding: * to prevent gzipped results
        playlist = self._download_xml(
            'http://www.karrierevideos.at/player-playlist.xml.php?p=%s' % video_id,
            video_id, transform_source=fix_xml_ampersands,
            headers={'Accept-Encoding': '*'})

        NS_MAP = {
            'jwplayer': 'http://developer.longtailvideo.com/trac/wiki/FlashFormats'
        }

        def ns(path):
            return xpath_with_ns(path, NS_MAP)

        item = playlist.find('./tracklist/item')
        video_file = xpath_text(
            item, ns('./jwplayer:file'), 'video url', fatal=True)
        streamer = xpath_text(
            item, ns('./jwplayer:streamer'), 'streamer', fatal=True)

        uploader = xpath_text(
            item, ns('./jwplayer:author'), 'uploader')
        duration = float_or_none(
            xpath_text(item, ns('./jwplayer:duration'), 'duration'))

        description = self._html_search_regex(
            r'(?s)<div class="leadtext">(.+?)</div>',
            webpage, 'description')

        thumbnail = self._html_search_meta(
            'thumbnail', webpage, 'thumbnail')
        if thumbnail:
            thumbnail = compat_urlparse.urljoin(url, thumbnail)

        return {
            'id': video_id,
            'url': streamer.replace('rtmpt', 'rtmp'),
            'play_path': 'mp4:%s' % video_file,
            'ext': 'flv',
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'duration': duration,
        }
