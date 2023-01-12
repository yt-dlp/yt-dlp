import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    determine_ext,
    ExtractorError,
    float_or_none,
    int_or_none,
    str_or_none,
    url_or_none,
    urlencode_postdata,
    urljoin,
)


class LecturioBaseIE(InfoExtractor):
    _API_BASE_URL = 'https://app.lecturio.com/api/en/latest/html5/'
    _LOGIN_URL = 'https://app.lecturio.com/en/login'
    _NETRC_MACHINE = 'lecturio'

    def _perform_login(self, username, password):
        # Sets some cookies
        _, urlh = self._download_webpage_handle(
            self._LOGIN_URL, None, 'Downloading login popup')

        def is_logged(url_handle):
            return self._LOGIN_URL not in url_handle.geturl()

        # Already logged in
        if is_logged(urlh):
            return

        login_form = {
            'signin[email]': username,
            'signin[password]': password,
            'signin[remember]': 'on',
        }

        response, urlh = self._download_webpage_handle(
            self._LOGIN_URL, None, 'Logging in',
            data=urlencode_postdata(login_form))

        # Logged in successfully
        if is_logged(urlh):
            return

        errors = self._html_search_regex(
            r'(?s)<ul[^>]+class=["\']error_list[^>]+>(.+?)</ul>', response,
            'errors', default=None)
        if errors:
            raise ExtractorError('Unable to login: %s' % errors, expected=True)
        raise ExtractorError('Unable to log in')


class LecturioIE(LecturioBaseIE):
    _VALID_URL = r'''(?x)
                    https://
                        (?:
                            app\.lecturio\.com/([^/]+/(?P<nt>[^/?#&]+)\.lecture|(?:\#/)?lecture/c/\d+/(?P<id>\d+))|
                            (?:www\.)?lecturio\.de/[^/]+/(?P<nt_de>[^/?#&]+)\.vortrag
                        )
                    '''
    _TESTS = [{
        'url': 'https://app.lecturio.com/medical-courses/important-concepts-and-terms-introduction-to-microbiology.lecture#tab/videos',
        'md5': '9a42cf1d8282a6311bf7211bbde26fde',
        'info_dict': {
            'id': '39634',
            'ext': 'mp4',
            'title': 'Important Concepts and Terms — Introduction to Microbiology',
        },
        'skip': 'Requires lecturio account credentials',
    }, {
        'url': 'https://www.lecturio.de/jura/oeffentliches-recht-staatsexamen.vortrag',
        'only_matching': True,
    }, {
        'url': 'https://app.lecturio.com/#/lecture/c/6434/39634',
        'only_matching': True,
    }]

    _CC_LANGS = {
        'Arabic': 'ar',
        'Bulgarian': 'bg',
        'German': 'de',
        'English': 'en',
        'Spanish': 'es',
        'Persian': 'fa',
        'French': 'fr',
        'Japanese': 'ja',
        'Polish': 'pl',
        'Pashto': 'ps',
        'Russian': 'ru',
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        nt = mobj.group('nt') or mobj.group('nt_de')
        lecture_id = mobj.group('id')
        display_id = nt or lecture_id
        api_path = 'lectures/' + lecture_id if lecture_id else 'lecture/' + nt + '.json'
        video = self._download_json(
            self._API_BASE_URL + api_path, display_id)
        title = video['title'].strip()
        if not lecture_id:
            pid = video.get('productId') or video.get('uid')
            if pid:
                spid = pid.split('_')
                if spid and len(spid) == 2:
                    lecture_id = spid[1]

        formats = []
        for format_ in video['content']['media']:
            if not isinstance(format_, dict):
                continue
            file_ = format_.get('file')
            if not file_:
                continue
            ext = determine_ext(file_)
            if ext == 'smil':
                # smil contains only broken RTMP formats anyway
                continue
            file_url = url_or_none(file_)
            if not file_url:
                continue
            label = str_or_none(format_.get('label'))
            filesize = int_or_none(format_.get('fileSize'))
            f = {
                'url': file_url,
                'format_id': label,
                'filesize': float_or_none(filesize, invscale=1000)
            }
            if label:
                mobj = re.match(r'(\d+)p\s*\(([^)]+)\)', label)
                if mobj:
                    f.update({
                        'format_id': mobj.group(2),
                        'height': int(mobj.group(1)),
                    })
            formats.append(f)

        subtitles = {}
        automatic_captions = {}
        captions = video.get('captions') or []
        for cc in captions:
            cc_url = cc.get('url')
            if not cc_url:
                continue
            cc_label = cc.get('translatedCode')
            lang = cc.get('languageCode') or self._search_regex(
                r'/([a-z]{2})_', cc_url, 'lang',
                default=cc_label.split()[0] if cc_label else 'en')
            original_lang = self._search_regex(
                r'/[a-z]{2}_([a-z]{2})_', cc_url, 'original lang',
                default=None)
            sub_dict = (automatic_captions
                        if 'auto-translated' in cc_label or original_lang
                        else subtitles)
            sub_dict.setdefault(self._CC_LANGS.get(lang, lang), []).append({
                'url': cc_url,
            })

        return {
            'id': lecture_id or nt,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
            'automatic_captions': automatic_captions,
        }


class LecturioCourseIE(LecturioBaseIE):
    _VALID_URL = r'https://app\.lecturio\.com/(?:[^/]+/(?P<nt>[^/?#&]+)\.course|(?:#/)?course/c/(?P<id>\d+))'
    _TESTS = [{
        'url': 'https://app.lecturio.com/medical-courses/microbiology-introduction.course#/',
        'info_dict': {
            'id': 'microbiology-introduction',
            'title': 'Microbiology: Introduction',
            'description': 'md5:13da8500c25880c6016ae1e6d78c386a',
        },
        'playlist_count': 45,
        'skip': 'Requires lecturio account credentials',
    }, {
        'url': 'https://app.lecturio.com/#/course/c/6434',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        nt, course_id = self._match_valid_url(url).groups()
        display_id = nt or course_id
        api_path = 'courses/' + course_id if course_id else 'course/content/' + nt + '.json'
        course = self._download_json(
            self._API_BASE_URL + api_path, display_id)
        entries = []
        for lecture in course.get('lectures', []):
            lecture_id = str_or_none(lecture.get('id'))
            lecture_url = lecture.get('url')
            if lecture_url:
                lecture_url = urljoin(url, lecture_url)
            else:
                lecture_url = 'https://app.lecturio.com/#/lecture/c/%s/%s' % (course_id, lecture_id)
            entries.append(self.url_result(
                lecture_url, ie=LecturioIE.ie_key(), video_id=lecture_id))
        return self.playlist_result(
            entries, display_id, course.get('title'),
            clean_html(course.get('description')))


class LecturioDeCourseIE(LecturioBaseIE):
    _VALID_URL = r'https://(?:www\.)?lecturio\.de/[^/]+/(?P<id>[^/?#&]+)\.kurs'
    _TEST = {
        'url': 'https://www.lecturio.de/jura/grundrechte.kurs',
        'only_matching': True,
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        entries = []
        for mobj in re.finditer(
                r'(?s)<td[^>]+\bdata-lecture-id=["\'](?P<id>\d+).+?\bhref=(["\'])(?P<url>(?:(?!\2).)+\.vortrag)\b[^>]+>',
                webpage):
            lecture_url = urljoin(url, mobj.group('url'))
            lecture_id = mobj.group('id')
            entries.append(self.url_result(
                lecture_url, ie=LecturioIE.ie_key(), video_id=lecture_id))

        title = self._search_regex(
            r'<h1[^>]*>([^<]+)', webpage, 'title', default=None)

        return self.playlist_result(entries, display_id, title)
