import json
import re

from .common import InfoExtractor
from ..utils import (
    classproperty,
    int_or_none,
    traverse_obj,
    urljoin
)


class BrainPOPBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'brainpop'
    _ORIGIN = ''  # So that _VALID_URL doesn't crash
    _LOGIN_ERRORS = {
        1502: 'The username and password you entered did not match.',  # LOGIN_FAILED
        1503: 'Payment method is expired.',  # LOGIN_FAILED_ACCOUNT_NOT_ACTIVE
        1506: 'Your BrainPOP plan has expired.',  # LOGIN_FAILED_ACCOUNT_EXPIRED
        1507: 'Terms not accepted.',  # LOGIN_FAILED_TERMS_NOT_ACCEPTED
        1508: 'Account not activated.',  # LOGIN_FAILED_SUBSCRIPTION_NOT_ACTIVE
        1512: 'The maximum number of devices permitted are logged in with your account right now.',  # LOGIN_FAILED_LOGIN_LIMIT_REACHED
        1513: 'You are trying to access your account from outside of its allowed IP range.',  # LOGIN_FAILED_INVALID_IP
        1514: 'Individual accounts are not included in your plan. Try again with your shared username and password.',  # LOGIN_FAILED_MBP_DISABLED
        1515: 'Account not activated.',  # LOGIN_FAILED_TEACHER_NOT_ACTIVE
        1523: 'That username and password won\'t work on this BrainPOP site.',  # LOGIN_FAILED_NO_ACCESS
        1524: 'You\'ll need to join a class before you can login.',  # LOGIN_FAILED_STUDENT_NO_PERIOD
        1526: 'Your account is locked. Reset your password, or ask a teacher or administrator for help.',  # LOGIN_FAILED_ACCOUNT_LOCKED
    }

    @classproperty
    def _VALID_URL(cls):
        root = re.escape(cls._ORIGIN).replace(r'https:', r'https?:').replace(r'www\.', r'(?:www\.)?')
        return rf'{root}/(?P<slug>[^/]+/[^/]+/(?P<id>[^/?#&]+))'

    def _assemble_formats(self, slug, format_id, display_id, token='', extra_fields={}):
        formats = []
        formats = self._extract_m3u8_formats(
            f'{urljoin(self._HLS_URL, slug)}.m3u8?{token}',
            display_id, 'mp4', m3u8_id=f'{format_id}-hls', fatal=False)
        formats.append({
            'format_id': format_id,
            'url': f'{urljoin(self._VIDEO_URL, slug)}?{token}',
        })
        for f in formats:
            f.update(extra_fields)
        return formats

    def _extract_adaptive_formats(self, data, token, display_id, key_format='%s', extra_fields={}):
        formats = []
        additional_key_formats = {
            '%s': {},
            'ad_%s': {
                'format_note': 'Audio description',
                'source_preference': -2
            }
        }
        for additional_key_format, additional_key_fields in additional_key_formats.items():
            for key_quality, key_index in enumerate(('high', 'low')):
                full_key_index = additional_key_format % (key_format % key_index)
                if data.get(full_key_index):
                    formats.extend(self._assemble_formats(data[full_key_index], full_key_index, display_id, token, {
                        'quality': -1 - key_quality,
                        **additional_key_fields,
                        **extra_fields
                    }))
        return formats

    def _perform_login(self, username, password):
        login_res = self._download_json(
            'https://api.brainpop.com/api/login', None,
            data=json.dumps({'username': username, 'password': password}).encode(),
            headers={
                'Content-Type': 'application/json',
                'Referer': self._ORIGIN
            }, note='Logging in', errnote='Unable to log in', expected_status=400)
        status_code = int_or_none(login_res['status_code'])
        if status_code != 1505:
            self.report_warning(
                f'Unable to login: {self._LOGIN_ERRORS.get(status_code) or login_res.get("message")}'
                or f'Got status code {status_code}')


class BrainPOPIE(BrainPOPBaseIE):
    _ORIGIN = 'https://www.brainpop.com'
    _VIDEO_URL = 'https://svideos.brainpop.com'
    _HLS_URL = 'https://hls.brainpop.com'
    _CDN_URL = 'https://cdn.brainpop.com'
    _TESTS = [{
        'url': 'https://www.brainpop.com/health/conflictresolution/martinlutherkingjr/movie?ref=null',
        'md5': '3ead374233ae74c7f1b0029a01c972f0',
        'info_dict': {
            'id': '1f3259fa457292b4',
            'ext': 'mp4',
            'title': 'Martin Luther King, Jr.',
            'display_id': 'martinlutherkingjr',
            'description': 'md5:f403dbb2bf3ccc7cf4c59d9e43e3c349',
        },
    }, {
        'url': 'https://www.brainpop.com/science/space/bigbang/',
        'md5': '9a1ff0e77444dd9e437354eb669c87ec',
        'info_dict': {
            'id': 'acae52cd48c99acf',
            'ext': 'mp4',
            'title': 'Big Bang',
            'display_id': 'bigbang',
            'description': 'md5:3e53b766b0f116f631b13f4cae185d38',
        },
        'skip': 'Requires login',
    }]

    def _real_extract(self, url):
        slug, display_id = self._match_valid_url(url).group('slug', 'id')
        movie_data = self._download_json(
            f'https://api.brainpop.com/api/content/published/bp/en/{slug}/movie?full=1', display_id,
            'Downloading movie data JSON', 'Unable to download movie data')['data']
        topic_data = traverse_obj(self._download_json(
            f'https://api.brainpop.com/api/content/published/bp/en/{slug}?full=1', display_id,
            'Downloading topic data JSON', 'Unable to download topic data', fatal=False),
            ('data', 'topic'), expected_type=dict) or movie_data['topic']

        if not traverse_obj(movie_data, ('access', 'allow')):
            reason = traverse_obj(movie_data, ('access', 'reason'))
            if 'logged' in reason:
                self.raise_login_required(reason, metadata_available=True)
            else:
                self.raise_no_formats(reason, video_id=display_id)
        movie_feature = movie_data['feature']
        movie_feature_data = movie_feature['data']

        formats, subtitles = [], {}
        formats.extend(self._extract_adaptive_formats(movie_feature_data, movie_feature_data.get('token', ''), display_id, '%s_v2', {
            'language': movie_feature.get('language') or 'en',
            'language_preference': 10
        }))
        for lang, localized_feature in traverse_obj(movie_feature, 'localization', default={}, expected_type=dict).items():
            formats.extend(self._extract_adaptive_formats(localized_feature, localized_feature.get('token', ''), display_id, '%s_v2', {
                'language': lang,
                'language_preference': -10
            }))

        # TODO: Do localization fields also have subtitles?
        for name, url in movie_feature_data.items():
            lang = self._search_regex(
                r'^subtitles_(?P<lang>\w+)$', name, 'subtitle metadata', default=None)
            if lang and url:
                subtitles.setdefault(lang, []).append({
                    'url': urljoin(self._CDN_URL, url)
                })

        return {
            'id': topic_data['topic_id'],
            'display_id': display_id,
            'title': topic_data.get('name'),
            'description': topic_data.get('synopsis'),
            'formats': formats,
            'subtitles': subtitles,
        }


class BrainPOPLegacyBaseIE(BrainPOPBaseIE):
    def _parse_js_topic_data(self, topic_data, display_id, token):
        movie_data = topic_data['movies']
        # TODO: Are there non-burned subtitles?
        formats = self._extract_adaptive_formats(movie_data, token, display_id)

        return {
            'id': topic_data['EntryID'],
            'display_id': display_id,
            'title': topic_data.get('name'),
            'alt_title': topic_data.get('title'),
            'description': topic_data.get('synopsis'),
            'formats': formats,
        }

    def _real_extract(self, url):
        slug, display_id = self._match_valid_url(url).group('slug', 'id')
        webpage = self._download_webpage(url, display_id)
        topic_data = self._search_json(
            r'var\s+content\s*=\s*', webpage, 'content data',
            display_id, end_pattern=';')['category']['unit']['topic']
        token = self._search_regex(r'ec_token\s*:\s*[\'"]([^\'"]+)', webpage, 'video token')
        return self._parse_js_topic_data(topic_data, display_id, token)


class BrainPOPJrIE(BrainPOPLegacyBaseIE):
    _ORIGIN = 'https://jr.brainpop.com'
    _VIDEO_URL = 'https://svideos-jr.brainpop.com'
    _HLS_URL = 'https://hls-jr.brainpop.com'
    _CDN_URL = 'https://cdn-jr.brainpop.com'
    _TESTS = [{
        'url': 'https://jr.brainpop.com/health/feelingsandsel/emotions/',
        'md5': '04e0561bb21770f305a0ce6cf0d869ab',
        'info_dict': {
            'id': '347',
            'ext': 'mp4',
            'title': 'Emotions',
            'display_id': 'emotions',
        },
    }, {
        'url': 'https://jr.brainpop.com/science/habitats/arctichabitats/',
        'md5': 'b0ed063bbd1910df00220ee29340f5d6',
        'info_dict': {
            'id': '29',
            'ext': 'mp4',
            'title': 'Arctic Habitats',
            'display_id': 'arctichabitats',
        },
        'skip': 'Requires login',
    }]


class BrainPOPELLIE(BrainPOPLegacyBaseIE):
    _ORIGIN = 'https://ell.brainpop.com'
    _VIDEO_URL = 'https://svideos-esl.brainpop.com'
    _HLS_URL = 'https://hls-esl.brainpop.com'
    _CDN_URL = 'https://cdn-esl.brainpop.com'
    _TESTS = [{
        'url': 'https://ell.brainpop.com/level1/unit1/lesson1/',
        'md5': 'a2012700cfb774acb7ad2e8834eed0d0',
        'info_dict': {
            'id': '1',
            'ext': 'mp4',
            'title': 'Lesson 1',
            'display_id': 'lesson1',
            'alt_title': 'Personal Pronouns',
        },
    }, {
        'url': 'https://ell.brainpop.com/level3/unit6/lesson5/',
        'md5': 'be19c8292c87b24aacfb5fda2f3f8363',
        'info_dict': {
            'id': '101',
            'ext': 'mp4',
            'title': 'Lesson 5',
            'display_id': 'lesson5',
            'alt_title': 'Review: Unit 6',
        },
        'skip': 'Requires login',
    }]


class BrainPOPEspIE(BrainPOPLegacyBaseIE):
    IE_DESC = 'BrainPOP Español'
    _ORIGIN = 'https://esp.brainpop.com'
    _VIDEO_URL = 'https://svideos.brainpop.com'
    _HLS_URL = 'https://hls.brainpop.com'
    _CDN_URL = 'https://cdn.brainpop.com/mx'
    _TESTS = [{
        'url': 'https://esp.brainpop.com/ciencia/la_diversidad_de_la_vida/ecosistemas/',
        'md5': 'cb3f062db2b3c5240ddfcfde7108f8c9',
        'info_dict': {
            'id': '3893',
            'ext': 'mp4',
            'title': 'Ecosistemas',
            'display_id': 'ecosistemas',
            'description': 'md5:80fc55b07e241f8c8f2aa8d74deaf3c3',
        },
    }, {
        'url': 'https://esp.brainpop.com/espanol/la_escritura/emily_dickinson/',
        'md5': '98c1b9559e0e33777209c425cda7dac4',
        'info_dict': {
            'id': '7146',
            'ext': 'mp4',
            'title': 'Emily Dickinson',
            'display_id': 'emily_dickinson',
            'description': 'md5:2795ad87b1d239c9711c1e92ab5a978b',
        },
        'skip': 'Requires login',
    }]


class BrainPOPFrIE(BrainPOPLegacyBaseIE):
    IE_DESC = 'BrainPOP Français'
    _ORIGIN = 'https://fr.brainpop.com'
    _VIDEO_URL = 'https://svideos.brainpop.com'
    _HLS_URL = 'https://hls.brainpop.com'
    _CDN_URL = 'https://cdn.brainpop.com/fr'
    _TESTS = [{
        'url': 'https://fr.brainpop.com/sciencesdelaterre/energie/sourcesdenergie/',
        'md5': '97e7f48af8af93f8a2be11709f239371',
        'info_dict': {
            'id': '1651',
            'ext': 'mp4',
            'title': 'Sources d\'énergie',
            'display_id': 'sourcesdenergie',
            'description': 'md5:7eece350f019a21ef9f64d4088b2d857',
        },
    }, {
        'url': 'https://fr.brainpop.com/francais/ecrire/plagiat/',
        'md5': '0cf2b4f89804d0dd4a360a51310d445a',
        'info_dict': {
            'id': '5803',
            'ext': 'mp4',
            'title': 'Plagiat',
            'display_id': 'plagiat',
            'description': 'md5:4496d87127ace28e8b1eda116e77cd2b',
        },
        'skip': 'Requires login',
    }]


class BrainPOPIlIE(BrainPOPLegacyBaseIE):
    IE_DESC = 'BrainPOP Hebrew'
    _ORIGIN = 'https://il.brainpop.com'
    _VIDEO_URL = 'https://svideos.brainpop.com'
    _HLS_URL = 'https://hls.brainpop.com'
    _CDN_URL = 'https://cdn.brainpop.com/he'
    _TESTS = [{
        'url': 'https://il.brainpop.com/category_9/subcategory_150/subjects_3782/',
        'md5': '9e4ea9dc60ecd385a6e5ca12ccf31641',
        'info_dict': {
            'id': '3782',
            'ext': 'mp4',
            'title': 'md5:e993632fcda0545d9205602ec314ad67',
            'display_id': 'subjects_3782',
            'description': 'md5:4cc084a8012beb01f037724423a4d4ed',
        },
    }]
