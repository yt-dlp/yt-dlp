import re

from .common import InfoExtractor
from ..compat import compat_str, compat_urlparse
from ..networking import Request
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    determine_ext,
    extract_attributes,
    float_or_none,
    int_or_none,
    js_to_json,
    smuggle_url,
    try_get,
    unescapeHTML,
    unsmuggle_url,
    url_or_none,
    urlencode_postdata,
)


class UdemyIE(InfoExtractor):
    IE_NAME = 'udemy'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:[^/]+\.)?udemy\.com/
                        (?:
                            [^#]+\#/lecture/|
                            lecture/view/?\?lectureId=|
                            [^/]+/learn/v4/t/lecture/
                        )
                        (?P<id>\d+)
                    '''
    _LOGIN_URL = 'https://www.udemy.com/join/login-popup/?displayType=ajax&showSkipButton=1'
    _ORIGIN_URL = 'https://www.udemy.com'
    _NETRC_MACHINE = 'udemy'

    _TESTS = [{
        'url': 'https://www.udemy.com/java-tutorial/#/lecture/172757',
        'md5': '98eda5b657e752cf945d8445e261b5c5',
        'info_dict': {
            'id': '160614',
            'ext': 'mp4',
            'title': 'Introduction and Installation',
            'description': 'md5:c0d51f6f21ef4ec65f091055a5eef876',
            'duration': 579.29,
        },
        'skip': 'Requires udemy account credentials',
    }, {
        # new URL schema
        'url': 'https://www.udemy.com/electric-bass-right-from-the-start/learn/v4/t/lecture/4580906',
        'only_matching': True,
    }, {
        # no url in outputs format entry
        'url': 'https://www.udemy.com/learn-web-development-complete-step-by-step-guide-to-success/learn/v4/t/lecture/4125812',
        'only_matching': True,
    }, {
        # only outputs rendition
        'url': 'https://www.udemy.com/how-you-can-help-your-local-community-5-amazing-examples/learn/v4/t/lecture/3225750?start=0',
        'only_matching': True,
    }, {
        'url': 'https://wipro.udemy.com/java-tutorial/#/lecture/172757',
        'only_matching': True,
    }]

    def _extract_course_info(self, webpage, video_id):
        course = self._parse_json(
            unescapeHTML(self._search_regex(
                r'ng-init=["\'].*\bcourse=({.+?})[;"\']',
                webpage, 'course', default='{}')),
            video_id, fatal=False) or {}
        course_id = course.get('id') or self._search_regex(
            [
                r'data-course-id=["\'](\d+)',
                r'&quot;courseId&quot;\s*:\s*(\d+)'
            ], webpage, 'course id')
        return course_id, course.get('title')

    def _enroll_course(self, base_url, webpage, course_id):
        def combine_url(base_url, url):
            return compat_urlparse.urljoin(base_url, url) if not url.startswith('http') else url

        checkout_url = unescapeHTML(self._search_regex(
            r'href=(["\'])(?P<url>(?:https?://(?:www\.)?udemy\.com)?/(?:payment|cart)/checkout/.+?)\1',
            webpage, 'checkout url', group='url', default=None))
        if checkout_url:
            raise ExtractorError(
                'Course %s is not free. You have to pay for it before you can download. '
                'Use this URL to confirm purchase: %s'
                % (course_id, combine_url(base_url, checkout_url)),
                expected=True)

        enroll_url = unescapeHTML(self._search_regex(
            r'href=(["\'])(?P<url>(?:https?://(?:www\.)?udemy\.com)?/course/subscribe/.+?)\1',
            webpage, 'enroll url', group='url', default=None))
        if enroll_url:
            webpage = self._download_webpage(
                combine_url(base_url, enroll_url),
                course_id, 'Enrolling in the course',
                headers={'Referer': base_url})
            if '>You have enrolled in' in webpage:
                self.to_screen('%s: Successfully enrolled in the course' % course_id)

    def _download_lecture(self, course_id, lecture_id):
        return self._download_json(
            'https://www.udemy.com/api-2.0/users/me/subscribed-courses/%s/lectures/%s?'
            % (course_id, lecture_id),
            lecture_id, 'Downloading lecture JSON', query={
                'fields[lecture]': 'title,description,view_html,asset',
                'fields[asset]': 'asset_type,stream_url,thumbnail_url,download_urls,stream_urls,captions,data,course_is_drmed',
            })

    def _handle_error(self, response):
        if not isinstance(response, dict):
            return
        error = response.get('error')
        if error:
            error_str = 'Udemy returned error #%s: %s' % (error.get('code'), error.get('message'))
            error_data = error.get('data')
            if error_data:
                error_str += ' - %s' % error_data.get('formErrors')
            raise ExtractorError(error_str, expected=True)

    def _download_webpage_handle(self, *args, **kwargs):
        headers = kwargs.get('headers', {}).copy()
        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.109 Safari/537.36'
        kwargs['headers'] = headers
        ret = super(UdemyIE, self)._download_webpage_handle(
            *args, **kwargs)
        if not ret:
            return ret
        webpage, _ = ret
        if any(p in webpage for p in (
                '>Please verify you are a human',
                'Access to this page has been denied because we believe you are using automation tools to browse the website',
                '"_pxCaptcha"')):
            raise ExtractorError(
                'Udemy asks you to solve a CAPTCHA. Login with browser, '
                'solve CAPTCHA, then export cookies and pass cookie file to '
                'yt-dlp with --cookies.', expected=True)
        return ret

    def _download_json(self, url_or_request, *args, **kwargs):
        headers = {
            'X-Udemy-Snail-Case': 'true',
            'X-Requested-With': 'XMLHttpRequest',
        }
        for cookie in self.cookiejar:
            if cookie.name == 'client_id':
                headers['X-Udemy-Client-Id'] = cookie.value
            elif cookie.name == 'access_token':
                headers['X-Udemy-Bearer-Token'] = cookie.value
                headers['X-Udemy-Authorization'] = 'Bearer %s' % cookie.value

        if isinstance(url_or_request, Request):
            url_or_request.headers.update(headers)
        else:
            url_or_request = Request(url_or_request, headers=headers)

        response = super(UdemyIE, self)._download_json(url_or_request, *args, **kwargs)
        self._handle_error(response)
        return response

    def _perform_login(self, username, password):
        login_popup = self._download_webpage(
            self._LOGIN_URL, None, 'Downloading login popup')

        def is_logged(webpage):
            return any(re.search(p, webpage) for p in (
                r'href=["\'](?:https://www\.udemy\.com)?/user/logout/',
                r'>Logout<'))

        # already logged in
        if is_logged(login_popup):
            return

        login_form = self._form_hidden_inputs('login-form', login_popup)

        login_form.update({
            'email': username,
            'password': password,
        })

        response = self._download_webpage(
            self._LOGIN_URL, None, 'Logging in',
            data=urlencode_postdata(login_form),
            headers={
                'Referer': self._ORIGIN_URL,
                'Origin': self._ORIGIN_URL,
            })

        if not is_logged(response):
            error = self._html_search_regex(
                r'(?s)<div[^>]+class="form-errors[^"]*">(.+?)</div>',
                response, 'error message', default=None)
            if error:
                raise ExtractorError('Unable to login: %s' % error, expected=True)
            raise ExtractorError('Unable to log in')

    def _real_extract(self, url):
        lecture_id = self._match_id(url)
        course_id = unsmuggle_url(url, {})[1].get('course_id')

        webpage = None
        if not course_id:
            webpage = self._download_webpage(url, lecture_id)
            course_id, _ = self._extract_course_info(webpage, lecture_id)

        try:
            lecture = self._download_lecture(course_id, lecture_id)
        except ExtractorError as e:
            # Error could possibly mean we are not enrolled in the course
            if isinstance(e.cause, HTTPError) and e.cause.status == 403:
                webpage = webpage or self._download_webpage(url, lecture_id)
                self._enroll_course(url, webpage, course_id)
                lecture = self._download_lecture(course_id, lecture_id)
            else:
                raise

        title = lecture['title']
        description = lecture.get('description')

        asset = lecture['asset']

        asset_type = asset.get('asset_type') or asset.get('assetType')
        if asset_type != 'Video':
            raise ExtractorError(
                'Lecture %s is not a video' % lecture_id, expected=True)

        stream_url = asset.get('stream_url') or asset.get('streamUrl')
        if stream_url:
            youtube_url = self._search_regex(
                r'(https?://www\.youtube\.com/watch\?v=.*)', stream_url, 'youtube URL', default=None)
            if youtube_url:
                return self.url_result(youtube_url, 'Youtube')

        video_id = compat_str(asset['id'])
        thumbnail = asset.get('thumbnail_url') or asset.get('thumbnailUrl')
        duration = float_or_none(asset.get('data', {}).get('duration'))

        subtitles = {}
        automatic_captions = {}

        formats = []

        def extract_output_format(src, f_id):
            return {
                'url': src.get('url'),
                'format_id': '%sp' % (src.get('height') or f_id),
                'width': int_or_none(src.get('width')),
                'height': int_or_none(src.get('height')),
                'vbr': int_or_none(src.get('video_bitrate_in_kbps')),
                'vcodec': src.get('video_codec'),
                'fps': int_or_none(src.get('frame_rate')),
                'abr': int_or_none(src.get('audio_bitrate_in_kbps')),
                'acodec': src.get('audio_codec'),
                'asr': int_or_none(src.get('audio_sample_rate')),
                'tbr': int_or_none(src.get('total_bitrate_in_kbps')),
                'filesize': int_or_none(src.get('file_size_in_bytes')),
            }

        outputs = asset.get('data', {}).get('outputs')
        if not isinstance(outputs, dict):
            outputs = {}

        def add_output_format_meta(f, key):
            output = outputs.get(key)
            if isinstance(output, dict):
                output_format = extract_output_format(output, key)
                output_format.update(f)
                return output_format
            return f

        def extract_formats(source_list):
            if not isinstance(source_list, list):
                return
            for source in source_list:
                video_url = url_or_none(source.get('file') or source.get('src'))
                if not video_url:
                    continue
                if source.get('type') == 'application/x-mpegURL' or determine_ext(video_url) == 'm3u8':
                    formats.extend(self._extract_m3u8_formats(
                        video_url, video_id, 'mp4', entry_protocol='m3u8_native',
                        m3u8_id='hls', fatal=False))
                    continue
                format_id = source.get('label')
                f = {
                    'url': video_url,
                    'format_id': '%sp' % format_id,
                    'height': int_or_none(format_id),
                }
                if format_id:
                    # Some videos contain additional metadata (e.g.
                    # https://www.udemy.com/ios9-swift/learn/#/lecture/3383208)
                    f = add_output_format_meta(f, format_id)
                formats.append(f)

        def extract_subtitles(track_list):
            if not isinstance(track_list, list):
                return
            for track in track_list:
                if not isinstance(track, dict):
                    continue
                if track.get('kind') != 'captions':
                    continue
                src = url_or_none(track.get('src'))
                if not src:
                    continue
                lang = track.get('language') or track.get(
                    'srclang') or track.get('label')
                sub_dict = automatic_captions if track.get(
                    'autogenerated') is True else subtitles
                sub_dict.setdefault(lang, []).append({
                    'url': src,
                })

        for url_kind in ('download', 'stream'):
            urls = asset.get('%s_urls' % url_kind)
            if isinstance(urls, dict):
                extract_formats(urls.get('Video'))

        captions = asset.get('captions')
        if isinstance(captions, list):
            for cc in captions:
                if not isinstance(cc, dict):
                    continue
                cc_url = url_or_none(cc.get('url'))
                if not cc_url:
                    continue
                lang = try_get(cc, lambda x: x['locale']['locale'], compat_str)
                sub_dict = (automatic_captions if cc.get('source') == 'auto'
                            else subtitles)
                sub_dict.setdefault(lang or 'en', []).append({
                    'url': cc_url,
                })

        view_html = lecture.get('view_html')
        if view_html:
            view_html_urls = set()
            for source in re.findall(r'<source[^>]+>', view_html):
                attributes = extract_attributes(source)
                src = attributes.get('src')
                if not src:
                    continue
                res = attributes.get('data-res')
                height = int_or_none(res)
                if src in view_html_urls:
                    continue
                view_html_urls.add(src)
                if attributes.get('type') == 'application/x-mpegURL' or determine_ext(src) == 'm3u8':
                    m3u8_formats = self._extract_m3u8_formats(
                        src, video_id, 'mp4', entry_protocol='m3u8_native',
                        m3u8_id='hls', fatal=False)
                    for f in m3u8_formats:
                        m = re.search(r'/hls_(?P<height>\d{3,4})_(?P<tbr>\d{2,})/', f['url'])
                        if m:
                            if not f.get('height'):
                                f['height'] = int(m.group('height'))
                            if not f.get('tbr'):
                                f['tbr'] = int(m.group('tbr'))
                    formats.extend(m3u8_formats)
                else:
                    formats.append(add_output_format_meta({
                        'url': src,
                        'format_id': '%dp' % height if height else None,
                        'height': height,
                    }, res))

            # react rendition since 2017.04.15 (see
            # https://github.com/ytdl-org/youtube-dl/issues/12744)
            data = self._parse_json(
                self._search_regex(
                    r'videojs-setup-data=(["\'])(?P<data>{.+?})\1', view_html,
                    'setup data', default='{}', group='data'), video_id,
                transform_source=unescapeHTML, fatal=False)
            if data and isinstance(data, dict):
                extract_formats(data.get('sources'))
                if not duration:
                    duration = int_or_none(data.get('duration'))
                extract_subtitles(data.get('tracks'))

            if not subtitles and not automatic_captions:
                text_tracks = self._parse_json(
                    self._search_regex(
                        r'text-tracks=(["\'])(?P<data>\[.+?\])\1', view_html,
                        'text tracks', default='{}', group='data'), video_id,
                    transform_source=lambda s: js_to_json(unescapeHTML(s)),
                    fatal=False)
                extract_subtitles(text_tracks)

        if not formats and outputs:
            for format_id, output in outputs.items():
                f = extract_output_format(output, format_id)
                if f.get('url'):
                    formats.append(f)

        if not formats and asset.get('course_is_drmed'):
            self.report_drm(video_id)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'formats': formats,
            'subtitles': subtitles,
            'automatic_captions': automatic_captions,
        }


class UdemyCourseIE(UdemyIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'udemy:course'
    _VALID_URL = r'https?://(?:[^/]+\.)?udemy\.com/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.udemy.com/java-tutorial/',
        'only_matching': True,
    }, {
        'url': 'https://wipro.udemy.com/java-tutorial/',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if UdemyIE.suitable(url) else super(UdemyCourseIE, cls).suitable(url)

    def _real_extract(self, url):
        course_path = self._match_id(url)

        webpage = self._download_webpage(url, course_path)

        course_id, title = self._extract_course_info(webpage, course_path)

        self._enroll_course(url, webpage, course_id)

        response = self._download_json(
            'https://www.udemy.com/api-2.0/courses/%s/cached-subscriber-curriculum-items' % course_id,
            course_id, 'Downloading course curriculum', query={
                'fields[chapter]': 'title,object_index',
                'fields[lecture]': 'title,asset',
                'page_size': '1000',
            })

        entries = []
        chapter, chapter_number = [None] * 2
        for entry in response['results']:
            clazz = entry.get('_class')
            if clazz == 'lecture':
                asset = entry.get('asset')
                if isinstance(asset, dict):
                    asset_type = asset.get('asset_type') or asset.get('assetType')
                    if asset_type != 'Video':
                        continue
                lecture_id = entry.get('id')
                if lecture_id:
                    entry = {
                        '_type': 'url_transparent',
                        'url': smuggle_url(
                            f'https://www.udemy.com/{course_path}/learn/v4/t/lecture/{entry["id"]}',
                            {'course_id': course_id}),
                        'title': entry.get('title'),
                        'ie_key': UdemyIE.ie_key(),
                    }
                    if chapter_number:
                        entry['chapter_number'] = chapter_number
                    if chapter:
                        entry['chapter'] = chapter
                    entries.append(entry)
            elif clazz == 'chapter':
                chapter_number = entry.get('object_index')
                chapter = entry.get('title')

        return self.playlist_result(entries, course_id, title)
