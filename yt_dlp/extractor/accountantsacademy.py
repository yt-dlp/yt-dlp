import itertools
import json
import time

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    jwt_decode_hs256,
    parse_duration,
    parse_qs,
    str_or_none,
    unified_strdate,
    url_or_none,
    urljoin,
)
from ..utils.traversal import traverse_obj


class AccountantsAcademyBaseIE(InfoExtractor):
    _BASE_URL_RE = r'https://(?:platform|www)\.accountantsacademy\.be'
    _ACCESS_TOKEN = None
    _REFRESH_TOKEN = None
    _CACHE_KEY = 'AccountantsAcademy_data'
    _NETRC_MACHINE = 'AccountantsAcademy'

    @staticmethod
    def _is_jwt_expired(token):
        return jwt_decode_hs256(token)['exp'] - time.time() < 300

    def cached_tokens(self):
        if self._ACCESS_TOKEN and not self._is_jwt_expired(self._ACCESS_TOKEN):
            return self._ACCESS_TOKEN
        elif self._REFRESH_TOKEN:
            self._refresh_access_token()
            return True
        else:
            self._ACCESS_TOKEN, self._REFRESH_TOKEN = self.cache.load(
                self._NETRC_MACHINE, self._CACHE_KEY, default=[None, None])
            if self._ACCESS_TOKEN and not self._is_jwt_expired(self._ACCESS_TOKEN):
                return self._ACCESS_TOKEN
            elif self._REFRESH_TOKEN:
                self._refresh_access_token()
                return True

        return None

    def _refresh_access_token(self):
        refresh_data = traverse_obj(self._call_api(
            None,
            note='Refreshing access token',
            operationname=None,
            variables={'refresh_token': self._REFRESH_TOKEN},
            query='''
                mutation RefreshToken($refresh_token: String!) {
                    refreshToken(refresh_token: $refresh_token) {
                        access_token
                        refresh_token
                    }
                }
            ''',
        ), ('refreshToken'))

        self._ACCESS_TOKEN = refresh_data.get('access_token')
        if not self._ACCESS_TOKEN:
            raise ExtractorError('Unable to refresh: no access token found')
        self._REFRESH_TOKEN = refresh_data.get('refresh_token')
        self.cache.store(self._NETRC_MACHINE, self._CACHE_KEY, [self._ACCESS_TOKEN, self._REFRESH_TOKEN])

    def _perform_login(self, username, password):
        if username.lower() == 'token' and password:
            self._ACCESS_TOKEN = password
            return
        elif self.cached_tokens():
            return

        login = traverse_obj(self._call_api(
            None,
            note='Logging in',
            operationname='login',
            variables={
                'email': username,
                'password': password,
                'admin': False,
            },
            query='''
                mutation login($email: String!, $password: String!, $admin: Boolean) {
                    login(loginInput: {email: $email, password: $password, admin: $admin}) {
                        access_token
                        refresh_token
                    }
                }
            ''',
        ), ('login'))

        self._ACCESS_TOKEN = login.get('access_token')
        if not self._ACCESS_TOKEN:
            raise ExtractorError('Login failed: no access token found')
        self._REFRESH_TOKEN = login.get('refresh_token')
        self.cache.store(self._NETRC_MACHINE, self._CACHE_KEY, [self._ACCESS_TOKEN, self._REFRESH_TOKEN])

    def _call_api(self, video_id, query, operationname, variables, note='Downloading JSON metadata', **kwargs):
        headers = kwargs.get('headers') or {}
        if self._ACCESS_TOKEN:
            headers['Authorization'] = f'Bearer {self._ACCESS_TOKEN}'

        data = self._download_json(
            'https://platform.accountantsacademy.be/graphql',
            video_id,
            data=json.dumps({
                'operationname': operationname,
                'query': query,
                'variables': variables,
            }).encode(),
            headers={
                **headers,
                'referer': 'https://platform.accountantsacademy.be/',
                'x-academy-host': 'platform.accountantsacademy.be',
                'content-type': 'application/json',
            },
            note=note,
        )
        errors = data.get('errors')
        msg = traverse_obj(errors, (..., 'message', {str}), default='', get_all=False)
        is_expected = msg in ('Invalid credentials',)

        if errors and msg == 'Unauthorized':
            self.raise_login_required()
        elif errors and 'api-key' in msg.lower():
            self.to_screen('Access token expired refreshing token')
            self._refresh_access_token()
            return self._call_api(video_id, query, operationname, variables)
        elif errors and 'token not found or expired' in msg.lower():
            self.report_warning('refresh token expired, retrying with credentials')
            self._ACCESS_TOKEN, self._REFRESH_TOKEN = None, None
            self.cache.store(self._NETRC_MACHINE, self._CACHE_KEY, [self._ACCESS_TOKEN, self._REFRESH_TOKEN])
            self._perform_login(*self._get_login_info())
            return self._call_api(video_id, query, operationname, variables)
        elif errors:
            raise ExtractorError(msg, expected=is_expected)

        return data['data']

    def _parse_cf_formats_and_subtitles(self, video_id, data):
        if isinstance(data, list):
            data = data[0]
        elif data is None:
            return None, None
        cf_stream = data.get('cf_stream')
        if not cf_stream:
            return None, None

        formats, subtitles = [], {}
        for fmt_name, fmt_url in traverse_obj(cf_stream, ('playback')).items():
            ext = determine_ext(fmt_url)
            if ext == 'm3u8':
                fmts = self._extract_m3u8_formats(fmt_url, video_id, m3u8_id=fmt_name)
            elif ext == 'mpd':
                fmts = self._extract_mpd_formats(fmt_url, video_id, mpd_id=fmt_name)
            else:
                self.report_warning(f'Skipping: got unsupported url {fmt_url}')
                continue
            formats.extend(fmts)

        if signed_url := cf_stream.get('signedBucketURL'):
            formats.append({
                'url': signed_url,
                'format_id': 'signedbucket',
            })

        for subs in cf_stream.get('textTracks'):
            lang = subs.get('lang') or 'be'
            url = subs.get('url')
            if not url:
                continue

            subtitles.setdefault(lang, []).append({
                'url': url,
                'ext': determine_ext(url) or 'vtt',
            })

        return formats, subtitles

    def _parse_cf_metadata(self, data):
        if isinstance(data, list):
            data = data[0]

        cf_stream = data.get('cf_stream')
        if not cf_stream:
            return {}

        return {
            **traverse_obj(cf_stream, ({
                'duration': ('duration', {parse_duration}),
                'thumbnail': ('thumbnail', {url_or_none}),
            }))}


class AccountantsAcademyUnitIE(AccountantsAcademyBaseIE):
    IE_NAME = 'accountantsacademy:unit'
    _VALID_URL = fr'{AccountantsAcademyBaseIE._BASE_URL_RE}/courses/unit/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://platform.accountantsacademy.be/courses/unit/69a00b9df4a816be8441d6bb',
        'info_dict': {
            'id': '69a00b9df4a816be8441d6bb',
            'ext': 'mp4',
            'title': 'Deel 1: Het kader (8min)',
            'thumbnail': 'https://customer-4zaf5uyu3v4cn0to.cloudflarestream.com/515a33c62ce035095f38f41c0c772c57/thumbnails/thumbnail.jpg',
        },
        'skip': 'Require login',
    }, {
        'url': 'https://platform.accountantsacademy.be/courses/unit/69a00ec3e8041ce15763cb95',
        'info_dict': {
            'id': '69a00ec3e8041ce15763cb95',
            'ext': 'mp4',
            'title': 'Deel 3: Tips om ergonomisch te werken (9min)',
            'thumbnail': 'https://customer-4zaf5uyu3v4cn0to.cloudflarestream.com/b4e997525df0f23c93541cfd11d50301/thumbnails/thumbnail.jpg',
        },
        'skip': 'Require login',
    }, {
        'url': 'https://platform.accountantsacademy.be/courses/unit/69a01021e8041ce1576411ed',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        unit_id = self._match_id(url)

        _UNIT_QUERY = '''
            query publicUnit($id: String!) {
                fetchUnitById(unitIdInput: {_id: $id}) {
                    ... on VideoUnit {
                        _id
                        name
                        cf_stream {
                            duration
                            thumbnail
                            playback {
                                hls
                                dash
                            }
                            signedBucketURL
                            textTracks {
                                lang
                                url
                            }
                        }
                    }
                }
            }
        '''

        metadata = traverse_obj(self._call_api(
            unit_id,
            operationname='publicUnit',
            variables={'id': unit_id},
            query=_UNIT_QUERY), ('fetchUnitById'))

        formats, subtitles = self._parse_cf_formats_and_subtitles(unit_id, metadata)
        if not formats or not subtitles:
            self.raise_no_formats('There is no video in this Unit')

        return {
            'id': unit_id,
            'title': str_or_none(metadata.get('name')),
            'formats': formats,
            'subtitles': subtitles,
            **self._parse_cf_metadata(metadata),
        }


class AccountantsAcademyIE(AccountantsAcademyBaseIE):
    IE_NAME = 'accountantsacademy:single_course'
    _VALID_URL = fr'{AccountantsAcademyBaseIE._BASE_URL_RE}/courses/(?!unit)(?P<id>[^/#&?]+)'
    _TESTS = [{
        'url': 'https://platform.accountantsacademy.be/courses/ergonomie-2',
        'info_dict': {
            'id': 'ergonomie-2',
            'title': 'Ergonomie',
        },
        'playlist_count': 3,
    }, {
        'url': 'https://platform.accountantsacademy.be/courses/newsflash-software-januari-2026',
        'info_dict': {
            'id': 'newsflash-software-januari-2026',
        },
        'playlist_count': 1,
        'title': 'Newsflash Software - Januari 2026',
    }, {
        'url': 'https://platform.accountantsacademy.be/courses/een-moderne-cyberaanval-van-a-tot-z',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        slug = self._match_id(url)

        metadata = traverse_obj(self._call_api(
            slug,
            operationname='courseBySlug',
            variables={'slug': slug},
            query='''
            query courseBySlug($slug: String!) {
                fetchCourseBySlug(courseSlugInput: {slug: $slug}) {
                    name
                    image {
                        url
                    }
                    description
                    short_description
                    lecturer
                    published
                    liked
                    meta
                    language
                    contents {
                        _id
                        title
                        units {
                            ... on ContentUnit {
                                _id
                            }
                            ... on VideoUnit {
                                cf_stream {
                                    duration
                                    thumbnail
                                    playback {
                                        hls
                                        dash
                                    }
                                    signedBucketURL
                                    textTracks {
                                        lang
                                        url
                                    }
                                }
                                __typename
                            }
                        }
                    }
                }
            }
            '''), ('fetchCourseBySlug'))

        creator = traverse_obj(metadata, ('lecturer', {str_or_none}))
        title = metadata.get('name') or f'course by {creator}'

        unit_metadata = {
            'creator': creator,
            **traverse_obj(metadata, {
                'lecturer': ('lecturer', {str_or_none}),
                'upload_date': ('meta', 'publication_date', {unified_strdate}),
                'modified_date': ('published', {unified_strdate}),
                'owner_id': ('owner', {str_or_none}),
            })}

        def entries(metadata):
            for units in metadata.get('contents', []):
                title = units.get('title', '')
                unit_id = units.get('_id')
                if 'afsluitende toets' in title.lower() or 'feedbackformulier' in title.lower():
                    continue
                for unit in traverse_obj(units, ('units', lambda _, v: v.get('__typename') == 'VideoUnit'), default=[]):
                    if not unit.get('cf_stream') or not unit:
                        continue
                    formats, subtitles = self._parse_cf_formats_and_subtitles(unit_id, unit)
                    if not formats and subtitles:
                        continue

                    yield {
                        'id': unit_id,
                        'title': title,
                        'formats': formats,
                        'subtitles': subtitles,
                        **self._parse_cf_metadata(metadata),
                        **unit_metadata,
                    }

        return self.playlist_result(
            entries=entries(metadata), playlist_id=slug,
            playlist_title=title,
            playlist_description=traverse_obj(metadata, ('short_description', 'description')),
        )


class AccountantsAcademyCoursesIE(AccountantsAcademyBaseIE):
    _VALID_URL = fr'{AccountantsAcademyBaseIE._BASE_URL_RE}/library/courses[^"]+'
    IE_NAME = 'accountantsacademy:courses'
    _TESTS = [{
        'url': 'https://platform.accountantsacademy.be/library/courses?page=1&type=634f0caadecc47f03abb46a6',
        'info_dict': {
            'id': 'All Courses',
        },
        'playlist_mincount': 3,
    }, {
        'url': 'https://platform.accountantsacademy.be/library/courses?cat=634bb8a30610e2e7f808d38a&page=1&type=634f0caadecc47f03abb46a6',
        'info_dict': {
            'id': 'All Courses',
        },
        'playlist_mincount': 3,
    }]

    def make_variables(self, url, page=1):
        parsed_url = parse_qs(url)

        if ppage := parsed_url.get('page'):
            page = int(ppage[0])
        if query := parsed_url.get('query', ''):
            pass
        if category := traverse_obj(parsed_url, ('cat'), ('category'), default=[]):
            pass
        if types := traverse_obj(parsed_url, ('type'), default=[]):
            types = [
                t.split('.')[-1] if '.' in t else t
                for t in types
            ]

        return {
            'variables': {
                'limit': 12,
                'page': page,
                'query': query,
                'type': types,
                'category': category,
            }}

    def _real_extract(self, url):
        video_id = 'All Courses'

        def entries(url):
            count_result = []
            for page_num in itertools.count(1):
                page = traverse_obj(self._call_api(
                    video_id,
                    note=f'Dowloading page {page_num}',
                    operationname='courses',
                    variables=self.make_variables(url, page_num),
                    query='''
                    query courses($query: String, $duration: [Float!], $type: [String!], $certificationType: [String!], $category: [String!], $level: [String!], $language: [String!], $source: [String!], $status: Boolean, $revision_date: [Int!], $page: Float, $limit: Float) {
                        fetchCourses(
                            filter: {query: $query, type: $type, certificationType: $certificationType, category: $category, level: $level, status: $status, language: $language, source: $source, page: $page, limit: $limit, revision_date: $revision_date, duration: $duration}
                        ) {
                            count
                            results {
                                _id
                                slug
                            }
                        }
                    }
                    '''), ('fetchCourses'))

                results = page.get('results')
                if not results:
                    break
                count_result.extend(results)
                for result in results:
                    cid = result.get('_id')
                    slug = '/courses/' + result.get('slug')
                    curl = urljoin('https://platform.accountantsacademy.be', slug)
                    yield self.url_result(curl, ie=AccountantsAcademyIE.ie_key(), video_id=cid)

                if page.get('count') >= len(count_result):
                    break

        return self.playlist_result(entries(url), video_id)
