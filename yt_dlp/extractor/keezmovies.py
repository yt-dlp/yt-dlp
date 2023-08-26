import re

from .common import InfoExtractor
from ..aes import aes_decrypt_text
from ..compat import compat_urllib_parse_unquote
from ..utils import (
    determine_ext,
    format_field,
    int_or_none,
    str_to_int,
    strip_or_none,
    url_or_none,
)


class KeezMoviesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?keezmovies\.com/video/(?:(?P<display_id>[^/]+)-)?(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.keezmovies.com/video/arab-wife-want-it-so-bad-i-see-she-thirsty-and-has-tiny-money-18070681',
        'md5': '2ac69cdb882055f71d82db4311732a1a',
        'info_dict': {
            'id': '18070681',
            'display_id': 'arab-wife-want-it-so-bad-i-see-she-thirsty-and-has-tiny-money',
            'ext': 'mp4',
            'title': 'Arab wife want it so bad I see she thirsty and has tiny money.',
            'thumbnail': None,
            'view_count': int,
            'age_limit': 18,
        }
    }, {
        'url': 'http://www.keezmovies.com/video/18070681',
        'only_matching': True,
    }]

    def _extract_info(self, url, fatal=True):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        display_id = (mobj.group('display_id')
                      if 'display_id' in mobj.groupdict()
                      else None) or mobj.group('id')

        webpage = self._download_webpage(
            url, display_id, headers={'Cookie': 'age_verified=1'})

        formats = []
        format_urls = set()

        title = None
        thumbnail = None
        duration = None
        encrypted = False

        def extract_format(format_url, height=None):
            format_url = url_or_none(format_url)
            if not format_url or not format_url.startswith(('http', '//')):
                return
            if format_url in format_urls:
                return
            format_urls.add(format_url)
            tbr = int_or_none(self._search_regex(
                r'[/_](\d+)[kK][/_]', format_url, 'tbr', default=None))
            if not height:
                height = int_or_none(self._search_regex(
                    r'[/_](\d+)[pP][/_]', format_url, 'height', default=None))
            if encrypted:
                format_url = aes_decrypt_text(
                    video_url, title, 32).decode('utf-8')
            formats.append({
                'url': format_url,
                'format_id': format_field(height, None, '%dp'),
                'height': height,
                'tbr': tbr,
            })

        flashvars = self._parse_json(
            self._search_regex(
                r'flashvars\s*=\s*({.+?});', webpage,
                'flashvars', default='{}'),
            display_id, fatal=False)

        if flashvars:
            title = flashvars.get('video_title')
            thumbnail = flashvars.get('image_url')
            duration = int_or_none(flashvars.get('video_duration'))
            encrypted = flashvars.get('encrypted') is True
            for key, value in flashvars.items():
                mobj = re.search(r'quality_(\d+)[pP]', key)
                if mobj:
                    extract_format(value, int(mobj.group(1)))
            video_url = flashvars.get('video_url')
            if video_url and determine_ext(video_url, None):
                extract_format(video_url)

        video_url = self._html_search_regex(
            r'flashvars\.video_url\s*=\s*(["\'])(?P<url>http.+?)\1',
            webpage, 'video url', default=None, group='url')
        if video_url:
            extract_format(compat_urllib_parse_unquote(video_url))

        if not formats:
            if 'title="This video is no longer available"' in webpage:
                self.raise_no_formats(
                    'Video %s is no longer available' % video_id, expected=True)

        if not title:
            title = self._html_search_regex(
                r'<h1[^>]*>([^<]+)', webpage, 'title')

        return webpage, {
            'id': video_id,
            'display_id': display_id,
            'title': strip_or_none(title),
            'thumbnail': thumbnail,
            'duration': duration,
            'age_limit': 18,
            'formats': formats,
        }

    def _real_extract(self, url):
        webpage, info = self._extract_info(url, fatal=False)
        if not info['formats']:
            return self.url_result(url, 'Generic')
        info['view_count'] = str_to_int(self._search_regex(
            r'<b>([\d,.]+)</b> Views?', webpage, 'view count', fatal=False))
        return info
