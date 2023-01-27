import json
import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    traverse_obj,
    urljoin
)


class BrainPOPBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'brainpop'
    _LOGIN_ERRORS = {
        1502: 'The username and password you entered did not match.', # LOGIN_FAILED
        1503: 'Payment method is expired.', # LOGIN_FAILED_ACCOUNT_NOT_ACTIVE
        1506: 'Your BrainPOP plan has expired.', # LOGIN_FAILED_ACCOUNT_EXPIRED
        1507: 'Terms not accepted.', # LOGIN_FAILED_TERMS_NOT_ACCEPTED
        1508: 'Account not activated.', # LOGIN_FAILED_SUBSCRIPTION_NOT_ACTIVE
        1512: 'The maximum number of devices permitted are logged in with your account right now.', # LOGIN_FAILED_LOGIN_LIMIT_REACHED
        1513: 'You are trying to access your account from outside of its allowed IP range.', # LOGIN_FAILED_INVALID_IP
        1514: 'Individual accounts are not included in your plan. Try again with your shared username and password.', # LOGIN_FAILED_MBP_DISABLED
        1515: 'Account not activated.', # LOGIN_FAILED_TEACHER_NOT_ACTIVE
        1523: 'That username and password won\'t work on this BrainPOP site.', # LOGIN_FAILED_NO_ACCESS
        1524: 'You\'ll need to join a class before you can login.', # LOGIN_FAILED_STUDENT_NO_PERIOD
        1526: 'Your account is locked. Reset your password, or ask a teacher or administrator for help.', # LOGIN_FAILED_ACCOUNT_LOCKED
    }

    def _assemble_formats(self, slug, format_id, display_id, token='', quality=-1):
        formats = []
        formats.append({
            'format_id': format_id,
            'url': '%s?%s' % (urljoin(self._VIDEO_URL, slug), token),
            'quality': quality,
        })
        formats.extend(self._extract_m3u8_formats(
            '%s.m3u8?%s' % (urljoin(self._HLS_URL, slug), token),
            display_id, 'mp4', quality=quality, m3u8_id=f'{format_id}-hls', fatal=False))
        return formats

    def _perform_login(self, username, password):
        login_res = self._download_json(
            'https://api.brainpop.com/api/login', None,
            data=json.dumps({'password': password, 'username': username}).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Referer': self._ORIGIN
            }, note='Logging in', errnote='Unable to log in', expected_status=400)
        status_code = int_or_none(login_res['status_code'])
        if status_code != 1505:
            self.report_warning('Unable to login: %s' % (self._LOGIN_ERRORS.get(status_code)
                                or login_res.get('message') or f'Got status code {status_code}'))


class BrainPOPIE(BrainPOPBaseIE):
    _VALID_URL = r'https?://(?:www\.)?brainpop\.com\/(?P<slug>[^/]+/[^/]+/(?P<id>[^/?#&]+))'
    _VIDEO_URL = 'https://svideos.brainpop.com'
    _HLS_URL = 'https://hls.brainpop.com'
    _CDN_URL = 'https://cdn.brainpop.com'
    _ORIGIN = 'https://www.brainpop.com'

    def _real_extract(self, url):
        slug, display_id = self._match_valid_url(url).group('slug', 'id')
        movie_data = self._download_json(
            f'https://api.brainpop.com/api/content/published/bp/en/{slug}/movie?full=1', display_id,
            'Downloading movie data JSON', 'Unable to download movie data')['data']
        topic_data = self._download_json(
            f'https://api.brainpop.com/api/content/published/bp/en/{slug}?full=1', display_id,
            'Downloading topic data JSON', 'Unable to download topic data')['data']['topic']

        if not traverse_obj(movie_data, ('access', 'allow')):
            reason = traverse_obj(movie_data, ('access', 'reason'))
            if 'logged' in reason:
                self.raise_login_required(reason, metadata_available=True)
            else:
                self.raise_no_formats(reason, video_id=display_id)
        movie_feature = movie_data['feature']['data']
        token = movie_feature.get('token', '')
        formats, subtitles = [], {}

        if movie_feature.get('high_v2'):
            formats.extend(self._assemble_formats(movie_feature['high_v2'], 'high', display_id, token, -1))
        if movie_feature.get('low_v2'):
            formats.extend(self._assemble_formats(movie_feature['low_v2'], 'low', display_id, token, -2))

        for name, url in movie_feature.items():
            lang = self._search_regex(
                r'^subtitles_(?P<lang>\w+)$', name, 'subtitle metadata', default=None)
            if lang and url:
                subtitles.setdefault(lang, []).append({
                    'url': urljoin(self._CDN_URL, url)
                })

        return {
            'id': topic_data['topic_id'],
            'display_id': display_id,
            'title': topic_data['name'],
            'description': topic_data.get('synopsis'),
            'formats': formats,
            'subtitles': subtitles,
        }


class BrainPOPLegacyBaseIE(BrainPOPBaseIE):
    def _parse_js_topic_data(self, topic_data, display_id, token):
        movie_data = topic_data['movies']
        # TODO: Are there non-burned subtitles?
        formats = []
        if movie_data.get('high'):
            formats.extend(self._assemble_formats(movie_data['high'], 'high', display_id, token, -1))
        if movie_data.get('low'):
            formats.extend(self._assemble_formats(movie_data['low'], 'low', display_id, token, -2))

        return {
            'id': topic_data['EntryID'],
            'display_id': display_id,
            'title': topic_data['name'],
            'description': topic_data.get('synopsis'),
            'formats': formats
        }

    def _real_extract(self, url):
        slug, display_id = self._match_valid_url(url).group('slug', 'id')
        webpage = self._download_webpage(url, display_id)
        topic_data = self._parse_json(
            self._search_regex(r'var\s+content\s*=\s*({.+?});', webpage, 'content data'),
            display_id)['category']['unit']['topic']
        token = self._search_regex(r'ec_token\s*:\s*[\'"](.+)[\'"]', webpage, 'video token')
        return self._parse_js_topic_data(topic_data, display_id, token)


class BrainPOPJrIE(BrainPOPLegacyBaseIE):
    _VALID_URL = r'https?://jr\.brainpop\.com\/(?P<slug>[^/]+/[^/]+/(?P<id>[^/?#&]+))'
    _VIDEO_URL = 'https://svideos-jr.brainpop.com'
    _HLS_URL = 'https://hls-jr.brainpop.com'
    _CDN_URL = 'https://cdn-jr.brainpop.com'
    _ORIGIN = 'https://jr.brainpop.com'


class BrainPOPELLIE(BrainPOPLegacyBaseIE):
    _VALID_URL = r'https?://ell\.brainpop\.com\/(?P<slug>[^/]+/[^/]+/(?P<id>[^/?#&]+))'
    _VIDEO_URL = 'https://svideos-esl.brainpop.com'
    _HLS_URL = 'https://hls-esl.brainpop.com'
    _CDN_URL = 'https://cdn-esl.brainpop.com'
    _ORIGIN = 'https://ell.brainpop.com'


class BrainPOPEspIE(BrainPOPLegacyBaseIE):
    IE_DESC = 'BrainPOP Español'
    _VALID_URL = r'https?://esp\.brainpop\.com\/(?P<slug>[^/]+/[^/]+/(?P<id>[^/?#&]+))'
    _VIDEO_URL = 'https://svideos.brainpop.com'
    _HLS_URL = 'https://hls.brainpop.com'
    _CDN_URL = 'https://cdn.brainpop.com/mx'
    _ORIGIN = 'https://esp.brainpop.com'


class BrainPOPFrIE(BrainPOPLegacyBaseIE):
    IE_DESC = 'BrainPOP Français'
    _VALID_URL = r'https?://fr\.brainpop\.com\/(?P<slug>[^/]+/[^/]+/(?P<id>[^/?#&]+))'
    _VIDEO_URL = 'https://svideos.brainpop.com'
    _HLS_URL = 'https://hls.brainpop.com'
    _CDN_URL = 'https://cdn.brainpop.com/fr'
    _ORIGIN = 'https://fr.brainpop.com'

class BrainPOPIlIE(BrainPOPLegacyBaseIE):
    IE_DESC = 'BrainPOP Hebrew'
    _VALID_URL = r'https?://il\.brainpop\.com\/(?P<slug>[^/]+/[^/]+/(?P<id>[^/?#&]+))'
    _VIDEO_URL = 'https://svideos.brainpop.com'
    _HLS_URL = 'https://hls.brainpop.com'
    _CDN_URL = 'https://cdn.brainpop.com/he'
    _ORIGIN = 'https://il.brainpop.com'