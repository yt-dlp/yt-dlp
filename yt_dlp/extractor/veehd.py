import re
import json

from .common import InfoExtractor
from ..compat import (
    compat_urllib_parse_unquote,
    compat_urlparse,
)
from ..utils import (
    ExtractorError,
    clean_html,
    get_element_by_id,
)


class VeeHDIE(InfoExtractor):
    _VALID_URL = r'https?://veehd\.com/video/(?P<id>\d+)'

    # Seems VeeHD videos have multiple copies on several servers, all of
    # whom have different MD5 checksums, so omit md5 field in all tests
    _TESTS = [{
        'url': 'http://veehd.com/video/4639434_Solar-Sinter',
        'info_dict': {
            'id': '4639434',
            'ext': 'mp4',
            'title': 'Solar Sinter',
            'uploader_id': 'VideoEyes',
            'description': 'md5:46a840e8692ddbaffb5f81d9885cb457',
        },
        'skip': 'Video deleted',
    }, {
        'url': 'http://veehd.com/video/4905758_Elysian-Fields-Channeling',
        'info_dict': {
            'id': '4905758',
            'ext': 'mp4',
            'title': 'Elysian Fields - Channeling',
            'description': 'md5:360e4e95fdab58aefbea0f2a19e5604b',
            'uploader_id': 'spotted',
        }
    }, {
        'url': 'http://veehd.com/video/2046729_2012-2009-DivX-Trailer',
        'info_dict': {
            'id': '2046729',
            'ext': 'avi',
            'title': '2012 (2009) DivX Trailer',
            'description': 'md5:75435ee95255e6a9838ac6f6f3a2396b',
            'uploader_id': 'Movie_Trailers',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # VeeHD seems to send garbage on the first request.
        # See https://github.com/ytdl-org/youtube-dl/issues/2102
        self._download_webpage(url, video_id, 'Requesting webpage')
        webpage = self._download_webpage(url, video_id)

        if 'This video has been removed<' in webpage:
            raise ExtractorError('Video %s has been removed' % video_id, expected=True)

        player_path = self._search_regex(
            r'\$\("#playeriframe"\).attr\({src : "(.+?)"',
            webpage, 'player path')
        player_url = compat_urlparse.urljoin(url, player_path)

        self._download_webpage(player_url, video_id, 'Requesting player page')
        player_page = self._download_webpage(
            player_url, video_id, 'Downloading player page')

        video_url = None

        config_json = self._search_regex(
            r'value=\'config=({.+?})\'', player_page, 'config json', default=None)

        if config_json:
            config = json.loads(config_json)
            video_url = compat_urllib_parse_unquote(config['clip']['url'])

        if not video_url:
            video_url = self._html_search_regex(
                r'<embed[^>]+type="video/divx"[^>]+src="([^"]+)"',
                player_page, 'video url', default=None)

        if not video_url:
            iframe_src = self._search_regex(
                r'<iframe[^>]+src="/?([^"]+)"', player_page, 'iframe url')
            iframe_url = 'http://veehd.com/%s' % iframe_src

            self._download_webpage(iframe_url, video_id, 'Requesting iframe page')
            iframe_page = self._download_webpage(
                iframe_url, video_id, 'Downloading iframe page')

            video_url = self._search_regex(
                r"file\s*:\s*'([^']+)'", iframe_page, 'video url')

        title = clean_html(get_element_by_id('videoName', webpage).rpartition('|')[0])
        uploader_id = self._html_search_regex(
            r'<a href="/profile/\d+">(.+?)</a>',
            webpage, 'uploader')
        thumbnail = self._search_regex(
            r'<img id="veehdpreview" src="(.+?)"',
            webpage, 'thumbnail')
        description = self._html_search_regex(
            r'<td class="infodropdown".*?<div>(.*?)<ul',
            webpage, 'description', flags=re.DOTALL)

        return {
            '_type': 'video',
            'id': video_id,
            'title': title,
            'url': video_url,
            'uploader_id': uploader_id,
            'thumbnail': thumbnail,
            'description': description,
        }
