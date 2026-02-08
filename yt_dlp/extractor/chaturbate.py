import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    lowercase_escape,
    url_or_none,
    urlencode_postdata,
)


class ChaturbateIE(InfoExtractor):
    _VALID_URL = r'https?://(?:[^/]+\.)?chaturbate\.(?P<tld>com|eu|global)/(?:fullvideo/?\?.*?\bb=)?(?P<id>[^/?&#]+)'
    _TESTS = [{
        'url': 'https://www.chaturbate.com/siswet19/',
        'info_dict': {
            'id': 'siswet19',
            'ext': 'mp4',
            'title': 're:^siswet19 [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'age_limit': 18,
            'is_live': True,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Room is offline',
    }, {
        'url': 'https://chaturbate.com/fullvideo/?b=caylin',
        'only_matching': True,
    }, {
        'url': 'https://en.chaturbate.com/siswet19/',
        'only_matching': True,
    }, {
        'url': 'https://chaturbate.eu/siswet19/',
        'only_matching': True,
    }, {
        'url': 'https://chaturbate.eu/fullvideo/?b=caylin',
        'only_matching': True,
    }, {
        'url': 'https://chaturbate.global/siswet19/',
        'only_matching': True,
    }]

    _ERROR_MAP = {
        'offline': 'Room is currently offline',
        'private': 'Room is currently in a private show',
        'away': 'Performer is currently away',
        'password protected': 'Room is password protected',
        'hidden': 'Hidden session in progress',
    }

    def _extract_from_api(self, video_id, tld):
        response = self._download_json(
            f'https://chaturbate.{tld}/get_edge_hls_url_ajax/', video_id,
            data=urlencode_postdata({'room_slug': video_id}),
            headers={
                **self.geo_verification_headers(),
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json',
            }, fatal=False, impersonate=True) or {}

        m3u8_url = response.get('url')
        if not m3u8_url:
            status = response.get('room_status')
            if error := self._ERROR_MAP.get(status):
                raise ExtractorError(error, expected=True)
            if status == 'public':
                self.raise_geo_restricted()
            self.report_warning(f'Got status "{status}" from API; falling back to webpage extraction')
            return None

        return {
            'id': video_id,
            'title': video_id,
            'thumbnail': f'https://roomimg.stream.highwebmedia.com/ri/{video_id}.jpg',
            'is_live': True,
            'age_limit': 18,
            'formats': self._extract_m3u8_formats(m3u8_url, video_id, ext='mp4', live=True),
        }

    def _extract_from_html(self, video_id, tld):
        webpage = self._download_webpage(
            f'https://chaturbate.{tld}/{video_id}/', video_id,
            headers=self.geo_verification_headers(), impersonate=True)

        found_m3u8_urls = []

        data = self._parse_json(
            self._search_regex(
                r'initialRoomDossier\s*=\s*(["\'])(?P<value>(?:(?!\1).)+)\1',
                webpage, 'data', default='{}', group='value'),
            video_id, transform_source=lowercase_escape, fatal=False)
        if data:
            m3u8_url = url_or_none(data.get('hls_source'))
            if m3u8_url:
                found_m3u8_urls.append(m3u8_url)

        if not found_m3u8_urls:
            for m in re.finditer(
                    r'(\\u002[27])(?P<url>http.+?\.m3u8.*?)\1', webpage):
                found_m3u8_urls.append(lowercase_escape(m.group('url')))

        if not found_m3u8_urls:
            for m in re.finditer(
                    r'(["\'])(?P<url>http.+?\.m3u8.*?)\1', webpage):
                found_m3u8_urls.append(m.group('url'))

        m3u8_urls = []
        for found_m3u8_url in found_m3u8_urls:
            m3u8_fast_url, m3u8_no_fast_url = found_m3u8_url, found_m3u8_url.replace('_fast', '')
            for m3u8_url in (m3u8_fast_url, m3u8_no_fast_url):
                if m3u8_url not in m3u8_urls:
                    m3u8_urls.append(m3u8_url)

        if not m3u8_urls:
            error = self._search_regex(
                [r'<span[^>]+class=(["\'])desc_span\1[^>]*>(?P<error>[^<]+)</span>',
                 r'<div[^>]+id=(["\'])defchat\1[^>]*>\s*<p><strong>(?P<error>[^<]+)<'],
                webpage, 'error', group='error', default=None)
            if not error:
                if any(p in webpage for p in (
                        self._ERROR_MAP['offline'], 'offline_tipping', 'tip_offline')):
                    error = self._ERROR_MAP['offline']
            if error:
                raise ExtractorError(error, expected=True)
            raise ExtractorError('Unable to find stream URL')

        formats = []
        for m3u8_url in m3u8_urls:
            for known_id in ('fast', 'slow'):
                if f'_{known_id}' in m3u8_url:
                    m3u8_id = known_id
                    break
            else:
                m3u8_id = None
            formats.extend(self._extract_m3u8_formats(
                m3u8_url, video_id, ext='mp4',
                # ffmpeg skips segments for fast m3u8
                preference=-10 if m3u8_id == 'fast' else None,
                m3u8_id=m3u8_id, fatal=False, live=True))

        return {
            'id': video_id,
            'title': video_id,
            'thumbnail': f'https://roomimg.stream.highwebmedia.com/ri/{video_id}.jpg',
            'age_limit': self._rta_search(webpage),
            'is_live': True,
            'formats': formats,
        }

    def _real_extract(self, url):
        video_id, tld = self._match_valid_url(url).group('id', 'tld')
        return self._extract_from_api(video_id, tld) or self._extract_from_html(video_id, tld)
