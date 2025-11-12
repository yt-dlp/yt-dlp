import itertools
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    urlencode_postdata,
)


class LyndaBaseIE(InfoExtractor):
    _SIGNIN_URL = 'https://www.lynda.com/signin/lynda'
    _PASSWORD_URL = 'https://www.lynda.com/signin/password'
    _USER_URL = 'https://www.lynda.com/signin/user'
    _ACCOUNT_CREDENTIALS_HINT = 'Use --username and --password options to provide lynda.com account credentials.'
    _NETRC_MACHINE = 'lynda'

    @staticmethod
    def _check_error(json_string, key_or_keys):
        keys = [key_or_keys] if isinstance(key_or_keys, str) else key_or_keys
        for key in keys:
            error = json_string.get(key)
            if error:
                raise ExtractorError(f'Unable to login: {error}', expected=True)

    def _perform_login_step(self, form_html, fallback_action_url, extra_form_data, note, referrer_url):
        action_url = self._search_regex(
            r'<form[^>]+action=(["\'])(?P<url>.+?)\1', form_html,
            'post url', default=fallback_action_url, group='url')

        if not action_url.startswith('http'):
            action_url = urllib.parse.urljoin(self._SIGNIN_URL, action_url)

        form_data = self._hidden_inputs(form_html)
        form_data.update(extra_form_data)

        response = self._download_json(
            action_url, None, note,
            data=urlencode_postdata(form_data),
            headers={
                'Referer': referrer_url,
                'X-Requested-With': 'XMLHttpRequest',
            }, expected_status=(418, 500))

        self._check_error(response, ('email', 'password', 'ErrorMessage'))

        return response, action_url

    def _perform_login(self, username, password):
        # Step 1: download signin page
        signin_page = self._download_webpage(
            self._SIGNIN_URL, None, 'Downloading signin page')

        # Already logged in
        if any(re.search(p, signin_page) for p in (
                r'isLoggedIn\s*:\s*true', r'logout\.aspx', r'>Log out<')):
            return

        # Step 2: submit email
        signin_form = self._search_regex(
            r'(?s)(<form[^>]+data-form-name=["\']signin["\'][^>]*>.+?</form>)',
            signin_page, 'signin form')
        signin_page, signin_url = self._login_step(
            signin_form, self._PASSWORD_URL, {'email': username},
            'Submitting email', self._SIGNIN_URL)

        # Step 3: submit password
        password_form = signin_page['body']
        self._login_step(
            password_form, self._USER_URL, {'email': username, 'password': password},
            'Submitting password', signin_url)


class LyndaIE(LyndaBaseIE):
    IE_NAME = 'lynda'
    IE_DESC = 'lynda.com videos'
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?(?:lynda\.com|educourse\.ga)/
                        (?:
                            (?:[^/]+/){2,3}(?P<course_id>\d+)|
                            player/embed
                        )/
                        (?P<id>\d+)
                    '''

    _TIMECODE_REGEX = r'\[(?P<timecode>\d+:\d+:\d+[\.,]\d+)\]'

    _TESTS = [{
        'url': 'https://www.lynda.com/Bootstrap-tutorials/Using-exercise-files/110885/114408-4.html',
        # md5 is unstable
        'info_dict': {
            'id': '114408',
            'ext': 'mp4',
            'title': 'Using the exercise files',
            'duration': 68,
        },
    }, {
        'url': 'https://www.lynda.com/player/embed/133770?tr=foo=1;bar=g;fizz=rt&fs=0',
        'only_matching': True,
    }, {
        'url': 'https://educourse.ga/Bootstrap-tutorials/Using-exercise-files/110885/114408-4.html',
        'only_matching': True,
    }, {
        'url': 'https://www.lynda.com/de/Graphic-Design-tutorials/Willkommen-Grundlagen-guten-Gestaltung/393570/393572-4.html',
        'only_matching': True,
    }, {
        # Status="NotFound", Message="Transcript not found"
        'url': 'https://www.lynda.com/ASP-NET-tutorials/What-you-should-know/5034180/2811512-4.html',
        'only_matching': True,
    }]

    def _raise_unavailable(self, video_id):
        self.raise_login_required(
            f'Video {video_id} is only available for members')

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        course_id = mobj.group('course_id')

        query = {
            'videoId': video_id,
            'type': 'video',
        }

        video = self._download_json(
            'https://www.lynda.com/ajax/player', video_id,
            'Downloading video JSON', fatal=False, query=query)

        # Fallback scenario
        if not video:
            query['courseId'] = course_id

            play = self._download_json(
                f'https://www.lynda.com/ajax/course/{course_id}/{video_id}/play', video_id, 'Downloading play JSON')

            if not play:
                self._raise_unavailable(video_id)

            formats = []
            for formats_dict in play:
                urls = formats_dict.get('urls')
                if not isinstance(urls, dict):
                    continue
                cdn = formats_dict.get('name')
                for format_id, format_url in urls.items():
                    if not format_url:
                        continue
                    formats.append({
                        'url': format_url,
                        'format_id': f'{cdn}-{format_id}' if cdn else format_id,
                        'height': int_or_none(format_id),
                    })

            conviva = self._download_json(
                'https://www.lynda.com/ajax/player/conviva', video_id,
                'Downloading conviva JSON', query=query)

            return {
                'id': video_id,
                'title': conviva['VideoTitle'],
                'description': conviva.get('VideoDescription'),
                'release_year': int_or_none(conviva.get('ReleaseYear')),
                'duration': int_or_none(conviva.get('Duration')),
                'creator': conviva.get('Author'),
                'formats': formats,
            }

        if 'Status' in video:
            raise ExtractorError(
                'lynda returned error: {}'.format(video['Message']), expected=True)

        if video.get('HasAccess') is False:
            self._raise_unavailable(video_id)

        video_id = str(video.get('ID') or video_id)
        duration = int_or_none(video.get('DurationInSeconds'))
        title = video['Title']

        formats = []

        fmts = video.get('Formats')
        if fmts:
            formats.extend([{
                'url': f['Url'],
                'ext': f.get('Extension'),
                'width': int_or_none(f.get('Width')),
                'height': int_or_none(f.get('Height')),
                'filesize': int_or_none(f.get('FileSize')),
                'format_id': str(f.get('Resolution')) if f.get('Resolution') else None,
            } for f in fmts if f.get('Url')])

        prioritized_streams = video.get('PrioritizedStreams')
        if prioritized_streams:
            for prioritized_stream_id, prioritized_stream in prioritized_streams.items():
                formats.extend([{
                    'url': video_url,
                    'height': int_or_none(format_id),
                    'format_id': f'{prioritized_stream_id}-{format_id}',
                } for format_id, video_url in prioritized_stream.items()])

        self._check_formats(formats, video_id)

        subtitles = self.extract_subtitles(video_id)

        return {
            'id': video_id,
            'title': title,
            'duration': duration,
            'subtitles': subtitles,
            'formats': formats,
        }

    def _fix_subtitles(self, subs):
        srt = ''
        seq_counter = 0
        for seq_current, seq_next in itertools.pairwise(subs):
            m_current = re.match(self._TIMECODE_REGEX, seq_current['Timecode'])
            if m_current is None:
                continue
            m_next = re.match(self._TIMECODE_REGEX, seq_next['Timecode'])
            if m_next is None:
                continue
            appear_time = m_current.group('timecode')
            disappear_time = m_next.group('timecode')
            text = seq_current['Caption'].strip()
            if text:
                seq_counter += 1
                srt += f'{seq_counter}\r\n{appear_time} --> {disappear_time}\r\n{text}\r\n\r\n'
        if srt:
            return srt

    def _get_subtitles(self, video_id):
        url = f'https://www.lynda.com/ajax/player?videoId={video_id}&type=transcript'
        subs = self._download_webpage(
            url, video_id, 'Downloading subtitles JSON', fatal=False)
        if not subs or 'Status="NotFound"' in subs:
            return {}
        subs = self._parse_json(subs, video_id, fatal=False)
        if not subs:
            return {}
        fixed_subs = self._fix_subtitles(subs)
        if fixed_subs:
            return {'en': [{'ext': 'srt', 'data': fixed_subs}]}
        return {}


class LyndaCourseIE(LyndaBaseIE):
    IE_NAME = 'lynda:course'
    IE_DESC = 'lynda.com online courses'

    # Course link equals to welcome/introduction video link of same course
    # We will recognize it as course link
    _VALID_URL = r'https?://(?:www|m)\.(?:lynda\.com|educourse\.ga)/(?P<coursepath>(?:[^/]+/){2,3}(?P<courseid>\d+))-2\.html'

    _TESTS = [{
        'url': 'https://www.lynda.com/Graphic-Design-tutorials/Grundlagen-guten-Gestaltung/393570-2.html',
        'only_matching': True,
    }, {
        'url': 'https://www.lynda.com/de/Graphic-Design-tutorials/Grundlagen-guten-Gestaltung/393570-2.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        course_path = mobj.group('coursepath')
        course_id = mobj.group('courseid')

        item_template = f'https://www.lynda.com/{course_path}/%s-4.html'

        course = self._download_json(
            f'https://www.lynda.com/ajax/player?courseId={course_id}&type=course',
            course_id, 'Downloading course JSON', fatal=False)

        if not course:
            webpage = self._download_webpage(url, course_id)
            entries = [
                self.url_result(
                    item_template % video_id, ie=LyndaIE.ie_key(),
                    video_id=video_id)
                for video_id in re.findall(
                    r'data-video-id=["\'](\d+)', webpage)]
            return self.playlist_result(
                entries, course_id,
                self._og_search_title(webpage, fatal=False),
                self._og_search_description(webpage))

        if course.get('Status') == 'NotFound':
            raise ExtractorError(
                f'Course {course_id} does not exist', expected=True)

        unaccessible_videos = 0
        entries = []

        # Might want to extract videos right here from video['Formats'] as it seems 'Formats' is not provided
        # by single video API anymore

        for chapter in course['Chapters']:
            for video in chapter.get('Videos', []):
                if video.get('HasAccess') is False:
                    unaccessible_videos += 1
                    continue
                video_id = video.get('ID')
                if video_id:
                    entries.append({
                        '_type': 'url_transparent',
                        'url': item_template % video_id,
                        'ie_key': LyndaIE.ie_key(),
                        'chapter': chapter.get('Title'),
                        'chapter_number': int_or_none(chapter.get('ChapterIndex')),
                        'chapter_id': str(chapter.get('ID')),
                    })

        if unaccessible_videos > 0:
            self.report_warning(
                f'{unaccessible_videos} videos are only available for members (or paid members) '
                f'and will not be downloaded. {self._ACCOUNT_CREDENTIALS_HINT}')

        course_title = course.get('Title')
        course_description = course.get('Description')

        return self.playlist_result(entries, course_id, course_title, course_description)
