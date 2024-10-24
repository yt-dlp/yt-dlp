import base64

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    str_or_none,
    try_get,
    url_or_none,
    urlencode_postdata,
    urljoin,
)


class PlatziBaseIE(InfoExtractor):
    _LOGIN_URL = 'https://platzi.com/login/'
    _NETRC_MACHINE = 'platzi'

    def _perform_login(self, username, password):
        login_page = self._download_webpage(
            self._LOGIN_URL, None, 'Downloading login page')

        login_form = self._hidden_inputs(login_page)

        login_form.update({
            'email': username,
            'password': password,
        })

        urlh = self._request_webpage(
            self._LOGIN_URL, None, 'Logging in',
            data=urlencode_postdata(login_form),
            headers={'Referer': self._LOGIN_URL})

        # login succeeded
        if 'platzi.com/login' not in urlh.url:
            return

        login_error = self._webpage_read_content(
            urlh, self._LOGIN_URL, None, 'Downloading login error page')

        login = self._parse_json(
            self._search_regex(
                r'login\s*=\s*({.+?})(?:\s*;|\s*</script)', login_error, 'login'),
            None)

        for kind in ('error', 'password', 'nonFields'):
            error = str_or_none(login.get(f'{kind}Error'))
            if error:
                raise ExtractorError(
                    f'Unable to login: {error}', expected=True)
        raise ExtractorError('Unable to log in')


class PlatziIE(PlatziBaseIE):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            platzi\.com/clases|           # es version
                            courses\.platzi\.com/classes  # en version
                        )/[^/]+/(?P<id>\d+)-[^/?\#&]+
                    '''

    _TESTS = [{
        'url': 'https://platzi.com/clases/1311-next-js/12074-creando-nuestra-primera-pagina/',
        'md5': '8f56448241005b561c10f11a595b37e3',
        'info_dict': {
            'id': '12074',
            'ext': 'mp4',
            'title': 'Creando nuestra primera página',
            'description': 'md5:4c866e45034fc76412fbf6e60ae008bc',
            'duration': 420,
        },
        'skip': 'Requires platzi account credentials',
    }, {
        'url': 'https://courses.platzi.com/classes/1367-communication-codestream/13430-background/',
        'info_dict': {
            'id': '13430',
            'ext': 'mp4',
            'title': 'Background',
            'description': 'md5:49c83c09404b15e6e71defaf87f6b305',
            'duration': 360,
        },
        'skip': 'Requires platzi account credentials',
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        lecture_id = self._match_id(url)

        webpage = self._download_webpage(url, lecture_id)

        data = self._parse_json(
            self._search_regex(
                # client_data may contain "};" so that we have to try more
                # strict regex first
                (r'client_data\s*=\s*({.+?})\s*;\s*\n',
                 r'client_data\s*=\s*({.+?})\s*;'),
                webpage, 'client data'),
            lecture_id)

        material = data['initialState']['material']
        desc = material['description']
        title = desc['title']

        formats = []
        for server_id, server in material['videos'].items():
            if not isinstance(server, dict):
                continue
            for format_id in ('hls', 'dash'):
                format_url = url_or_none(server.get(format_id))
                if not format_url:
                    continue
                if format_id == 'hls':
                    formats.extend(self._extract_m3u8_formats(
                        format_url, lecture_id, 'mp4',
                        entry_protocol='m3u8_native', m3u8_id=format_id,
                        note=f'Downloading {server_id} m3u8 information',
                        fatal=False))
                elif format_id == 'dash':
                    formats.extend(self._extract_mpd_formats(
                        format_url, lecture_id, mpd_id=format_id,
                        note=f'Downloading {server_id} MPD manifest',
                        fatal=False))

        content = str_or_none(desc.get('content'))
        description = (clean_html(base64.b64decode(content).decode('utf-8'))
                       if content else None)
        duration = int_or_none(material.get('duration'), invscale=60)

        return {
            'id': lecture_id,
            'title': title,
            'description': description,
            'duration': duration,
            'formats': formats,
        }


class PlatziCourseIE(PlatziBaseIE):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            platzi\.com/clases|           # es version
                            courses\.platzi\.com/classes  # en version
                        )/(?P<id>[^/?\#&]+)
                    '''
    _TESTS = [{
        'url': 'https://platzi.com/clases/next-js/',
        'info_dict': {
            'id': '1311',
            'title': 'Curso de Next.js',
        },
        'playlist_count': 22,
    }, {
        'url': 'https://courses.platzi.com/classes/communication-codestream/',
        'info_dict': {
            'id': '1367',
            'title': 'Codestream Course',
        },
        'playlist_count': 14,
    }]

    @classmethod
    def suitable(cls, url):
        return False if PlatziIE.suitable(url) else super().suitable(url)

    def _real_extract(self, url):
        course_name = self._match_id(url)

        webpage = self._download_webpage(url, course_name)

        props = self._parse_json(
            self._search_regex(r'data\s*=\s*({.+?})\s*;', webpage, 'data'),
            course_name)['initialProps']

        entries = []
        for chapter_num, chapter in enumerate(props['concepts'], 1):
            if not isinstance(chapter, dict):
                continue
            materials = chapter.get('materials')
            if not materials or not isinstance(materials, list):
                continue
            chapter_title = chapter.get('title')
            chapter_id = str_or_none(chapter.get('id'))
            for material in materials:
                if not isinstance(material, dict):
                    continue
                if material.get('material_type') != 'video':
                    continue
                video_url = urljoin(url, material.get('url'))
                if not video_url:
                    continue
                entries.append({
                    '_type': 'url_transparent',
                    'url': video_url,
                    'title': str_or_none(material.get('name')),
                    'id': str_or_none(material.get('id')),
                    'ie_key': PlatziIE.ie_key(),
                    'chapter': chapter_title,
                    'chapter_number': chapter_num,
                    'chapter_id': chapter_id,
                })

        course_id = str(try_get(props, lambda x: x['course']['id']))
        course_title = try_get(props, lambda x: x['course']['name'], str)

        return self.playlist_result(entries, course_id, course_title)
