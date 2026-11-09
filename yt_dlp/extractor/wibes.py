from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    parse_iso8601,
)


class WibesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?wibes\.ru/clips?/(?:[^/?#]+-)?(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://wibes.ru/clips/tak-chto-dlya-tebya-topstomatologiyamoskvazubyuhodza-8867952',
        'md5': '3cd6dc22f598afd8d58384772a7e899a',
        'info_dict': {
            'id': '8867952',
            'ext': 'mp4',
            'title': 'Так что для тебя топ? #стоматология#москва#зубы#уходзазубами#лечениезубов — Бодрая привычка — Wibes',
            'description': 'md5:15e9349acfe1781092bef6d138dffb24',
            'uploader': 'Бодрая привычка',
            'duration': 87,
            'thumbnail': 'http://wibes-01.wbbasket.ru/d46092e6-d0f9-11f1-a944-06856f5646e2/3487990a-93f1-4256-b0a1-08deace0f25e-small-preview.webp',
            'timestamp': 1792990677,
            'upload_date': '20261026',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        try:
            webpage = self._download_webpage(url, video_id, impersonate=True)
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 498:
                raise ExtractorError(
                    'Blocked by the site\'s anti-bot challenge (HTTP 498). Pass cookies from a '
                    'browser that has loaded the page, using --cookies-from-browser together '
                    'with a matching --impersonate target', expected=True)
            raise

        video_url = self._og_search_video_url(webpage)
        if determine_ext(video_url) == 'm3u8':
            formats = self._extract_m3u8_formats(
                video_url, video_id, 'mp4', m3u8_id='hls', headers={'Referer': url})
        else:
            formats = [{'url': video_url, 'http_headers': {'Referer': url}}]

        return {
            'id': video_id,
            'title': self._og_search_title(webpage, default=None) or self._html_extract_title(webpage),
            'description': self._og_search_description(webpage, default=None),
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'uploader': self._html_search_meta('ya:ovs:login', webpage, 'uploader', default=None),
            'duration': int_or_none(self._html_search_meta('video:duration', webpage, default=None)),
            'timestamp': parse_iso8601(
                self._html_search_meta('ya:ovs:upload_date', webpage, default=None)),
            'formats': formats,
        }
