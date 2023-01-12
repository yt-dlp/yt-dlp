import re

from .common import InfoExtractor
from ..utils import parse_duration


class Canalc2IE(InfoExtractor):
    IE_NAME = 'canalc2.tv'
    _VALID_URL = r'https?://(?:(?:www\.)?canalc2\.tv/video/|archives-canalc2\.u-strasbg\.fr/video\.asp\?.*\bidVideo=)(?P<id>\d+)'

    _TESTS = [{
        'url': 'http://www.canalc2.tv/video/12163',
        'md5': '060158428b650f896c542dfbb3d6487f',
        'info_dict': {
            'id': '12163',
            'ext': 'mp4',
            'title': 'Terrasses du Numérique',
            'duration': 122,
        },
    }, {
        'url': 'http://archives-canalc2.u-strasbg.fr/video.asp?idVideo=11427&voir=oui',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            'http://www.canalc2.tv/video/%s' % video_id, video_id)

        title = self._html_search_regex(
            r'(?s)class="[^"]*col_description[^"]*">.*?<h3>(.+?)</h3>',
            webpage, 'title')

        formats = []
        for _, video_url in re.findall(r'file\s*=\s*(["\'])(.+?)\1', webpage):
            if video_url.startswith('rtmp://'):
                rtmp = re.search(
                    r'^(?P<url>rtmp://[^/]+/(?P<app>.+/))(?P<play_path>mp4:.+)$', video_url)
                formats.append({
                    'url': rtmp.group('url'),
                    'format_id': 'rtmp',
                    'ext': 'flv',
                    'app': rtmp.group('app'),
                    'play_path': rtmp.group('play_path'),
                    'page_url': url,
                })
            else:
                formats.append({
                    'url': video_url,
                    'format_id': 'http',
                })

        if formats:
            info = {
                'formats': formats,
            }
        else:
            info = self._parse_html5_media_entries(url, webpage, url)[0]

        info.update({
            'id': video_id,
            'title': title,
            'duration': parse_duration(self._search_regex(
                r'id=["\']video_duree["\'][^>]*>([^<]+)',
                webpage, 'duration', fatal=False)),
        })
        return info
