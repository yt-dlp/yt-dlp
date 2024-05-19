import re

from .common import InfoExtractor

from ..compat import (
    compat_urlparse,
)

from ..utils import (
    urlencode_postdata,
    urljoin,
    int_or_none,
    clean_html,
    ExtractorError
)


class AluraIE(InfoExtractor):
    _VALID_URL = r'https?://(?:cursos\.)?alura\.com\.br/course/(?P<course_name>[^/]+)/task/(?P<id>\d+)'
    _LOGIN_URL = 'https://cursos.alura.com.br/loginForm?urlAfterLogin=/loginForm'
    _VIDEO_URL = 'https://cursos.alura.com.br/course/%s/task/%s/video'
    _NETRC_MACHINE = 'alura'
    _TESTS = [{
        'url': 'https://cursos.alura.com.br/course/clojure-mutabilidade-com-atoms-e-refs/task/60095',
        'info_dict': {
            'id': '60095',
            'ext': 'mp4',
            'title': 'Referências, ref-set e alter'
        },
        'skip': 'Requires alura account credentials'},
        {
            # URL without video
            'url': 'https://cursos.alura.com.br/course/clojure-mutabilidade-com-atoms-e-refs/task/60098',
            'only_matching': True},
        {
            'url': 'https://cursos.alura.com.br/course/fundamentos-market-digital/task/55219',
            'only_matching': True}
    ]

    def _real_extract(self, url):

        course, video_id = self._match_valid_url(url).group('course_name', 'id')
        video_url = self._VIDEO_URL % (course, video_id)

        video_dict = self._download_json(video_url, video_id, 'Searching for videos')

        if video_dict:
            webpage = self._download_webpage(url, video_id)
            video_title = clean_html(self._search_regex(
                r'<span[^>]+class=(["\'])task-body-header-title-text\1[^>]*>(?P<title>[^<]+)',
                webpage, 'title', group='title'))

            formats = []
            for video_obj in video_dict:
                video_url_m3u8 = video_obj.get('mp4')
                video_format = self._extract_m3u8_formats(
                    video_url_m3u8, None, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False)
                for f in video_format:
                    m = re.search(r'^[\w \W]*-(?P<res>\w*).mp4[\W \w]*', f['url'])
                    if m:
                        if not f.get('height'):
                            f['height'] = int('720' if m.group('res') == 'hd' else '480')
                formats.extend(video_format)

            return {
                'id': video_id,
                'title': video_title,
                "formats": formats
            }

    def _perform_login(self, username, password):

        login_page = self._download_webpage(
            self._LOGIN_URL, None, 'Downloading login popup')

        def is_logged(webpage):
            return any(re.search(p, webpage) for p in (
                r'href=[\"|\']?/signout[\"|\']',
                r'>Logout<'))

        # already logged in
        if is_logged(login_page):
            return

        login_form = self._hidden_inputs(login_page)

        login_form.update({
            'username': username,
            'password': password,
        })

        post_url = self._search_regex(
            r'<form[^>]+class=["|\']signin-form["|\'] action=["|\'](?P<url>.+?)["|\']', login_page,
            'post url', default=self._LOGIN_URL, group='url')

        if not post_url.startswith('http'):
            post_url = compat_urlparse.urljoin(self._LOGIN_URL, post_url)

        response = self._download_webpage(
            post_url, None, 'Logging in',
            data=urlencode_postdata(login_form),
            headers={'Content-Type': 'application/x-www-form-urlencoded'})

        if not is_logged(response):
            error = self._html_search_regex(
                r'(?s)<p[^>]+class="alert-message[^"]*">(.+?)</p>',
                response, 'error message', default=None)
            if error:
                raise ExtractorError('Unable to login: %s' % error, expected=True)
            raise ExtractorError('Unable to log in')


class AluraCourseIE(AluraIE):  # XXX: Do not subclass from concrete IE

    _VALID_URL = r'https?://(?:cursos\.)?alura\.com\.br/course/(?P<id>[^/]+)'
    _LOGIN_URL = 'https://cursos.alura.com.br/loginForm?urlAfterLogin=/loginForm'
    _NETRC_MACHINE = 'aluracourse'
    _TESTS = [{
        'url': 'https://cursos.alura.com.br/course/clojure-mutabilidade-com-atoms-e-refs',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if AluraIE.suitable(url) else super(AluraCourseIE, cls).suitable(url)

    def _real_extract(self, url):

        course_path = self._match_id(url)
        webpage = self._download_webpage(url, course_path)

        course_title = self._search_regex(
            r'<h1.*?>(.*?)<strong>(?P<course_title>.*?)</strong></h[0-9]>', webpage,
            'course title', default=course_path, group='course_title')

        entries = []
        if webpage:
            for path in re.findall(r'<a\b(?=[^>]* class="[^"]*(?<=[" ])courseSectionList-section[" ])(?=[^>]* href="([^"]*))', webpage):
                page_url = urljoin(url, path)
                section_path = self._download_webpage(page_url, course_path)
                for path_video in re.findall(r'<a\b(?=[^>]* class="[^"]*(?<=[" ])task-menu-nav-item-link-VIDEO[" ])(?=[^>]* href="([^"]*))', section_path):
                    chapter = clean_html(
                        self._search_regex(
                            r'<h3[^>]+class=(["\'])task-menu-section-title-text\1[^>]*>(?P<chapter>[^<]+)',
                            section_path,
                            'chapter',
                            group='chapter'))

                    chapter_number = int_or_none(
                        self._search_regex(
                            r'<span[^>]+class=(["\'])task-menu-section-title-number[^>]*>(.*?)<strong>(?P<chapter_number>[^<]+)</strong>',
                            section_path,
                            'chapter number',
                            group='chapter_number'))
                    video_url = urljoin(url, path_video)

                    entry = {
                        '_type': 'url_transparent',
                        'id': self._match_id(video_url),
                        'url': video_url,
                        'id_key': self.ie_key(),
                        'chapter': chapter,
                        'chapter_number': chapter_number
                    }
                    entries.append(entry)
        return self.playlist_result(entries, course_path, course_title)
