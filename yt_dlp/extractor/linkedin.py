import itertools
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    extract_attributes,
    float_or_none,
    int_or_none,
    srt_subtitles_timecode,
    mimetype2ext,
    traverse_obj,
    try_get,
    url_or_none,
    urlencode_postdata,
    urljoin,
)


class LinkedInBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'linkedin'
    _logged_in = False

    def _perform_login(self, username, password):
        if self._logged_in:
            return

        login_page = self._download_webpage(
            self._LOGIN_URL, None, 'Downloading login page')
        action_url = urljoin(self._LOGIN_URL, self._search_regex(
            r'<form[^>]+action=(["\'])(?P<url>.+?)\1', login_page, 'post url',
            default='https://www.linkedin.com/uas/login-submit', group='url'))
        data = self._hidden_inputs(login_page)
        data.update({
            'session_key': username,
            'session_password': password,
        })
        login_submit_page = self._download_webpage(
            action_url, None, 'Logging in',
            data=urlencode_postdata(data))
        error = self._search_regex(
            r'<span[^>]+class="error"[^>]*>\s*(.+?)\s*</span>',
            login_submit_page, 'error', default=None)
        if error:
            raise ExtractorError(error, expected=True)
        LinkedInBaseIE._logged_in = True


class LinkedInLearningBaseIE(LinkedInBaseIE):
    _LOGIN_URL = 'https://www.linkedin.com/uas/login?trk=learning'

    def _call_api(self, course_slug, fields, video_slug=None, resolution=None):
        query = {
            'courseSlug': course_slug,
            'fields': fields,
            'q': 'slugs',
        }
        sub = ''
        if video_slug:
            query.update({
                'videoSlug': video_slug,
                'resolution': '_%s' % resolution,
            })
            sub = ' %dp' % resolution
        api_url = 'https://www.linkedin.com/learning-api/detailedCourses'
        if not self._get_cookies(api_url).get('JSESSIONID'):
            self.raise_login_required()
        return self._download_json(
            api_url, video_slug, 'Downloading%s JSON metadata' % sub, headers={
                'Csrf-Token': self._get_cookies(api_url)['JSESSIONID'].value,
            }, query=query)['elements'][0]

    def _get_urn_id(self, video_data):
        urn = video_data.get('urn')
        if urn:
            mobj = re.search(r'urn:li:lyndaCourse:\d+,(\d+)', urn)
            if mobj:
                return mobj.group(1)

    def _get_video_id(self, video_data, course_slug, video_slug):
        return self._get_urn_id(video_data) or '%s/%s' % (course_slug, video_slug)


class LinkedInIE(LinkedInBaseIE):
    _VALID_URL = r'https?://(?:www\.)?linkedin\.com/posts/[^/?#]+-(?P<id>\d+)-\w{4}/?(?:[?#]|$)'
    _TESTS = [{
        'url': 'https://www.linkedin.com/posts/mishalkhawaja_sendinblueviews-toronto-digitalmarketing-ugcPost-6850898786781339649-mM20',
        'info_dict': {
            'id': '6850898786781339649',
            'ext': 'mp4',
            'title': 'Mishal K. on LinkedIn: #sendinblueviews #toronto #digitalmarketing #nowhiring #sendinblue…',
            'description': 'md5:2998a31f6f479376dd62831f53a80f71',
            'uploader': 'Mishal K.',
            'thumbnail': 're:^https?://media.licdn.com/dms/image/.*$',
            'like_count': int
        },
    }, {
        'url': 'https://www.linkedin.com/posts/the-mathworks_2_what-is-mathworks-cloud-center-activity-7151241570371948544-4Gu7',
        'info_dict': {
            'id': '7151241570371948544',
            'ext': 'mp4',
            'title': 'MathWorks on LinkedIn: What Is MathWorks Cloud Center?',
            'description': 'md5:95f9d4eeb6337882fb47eefe13d7a40c',
            'uploader': 'MathWorks',
            'thumbnail': 're:^https?://media.licdn.com/dms/image/.*$',
            'like_count': int,
            'subtitles': 'mincount:1'
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        video_attrs = extract_attributes(self._search_regex(r'(<video[^>]+>)', webpage, 'video'))
        sources = self._parse_json(video_attrs['data-sources'], video_id)
        formats = [{
            'url': source['src'],
            'ext': mimetype2ext(source.get('type')),
            'tbr': float_or_none(source.get('data-bitrate'), scale=1000),
        } for source in sources]
        subtitles = {'en': [{
            'url': video_attrs['data-captions-url'],
            'ext': 'vtt',
        }]} if url_or_none(video_attrs.get('data-captions-url')) else {}

        return {
            'id': video_id,
            'formats': formats,
            'title': self._og_search_title(webpage, default=None) or self._html_extract_title(webpage),
            'like_count': int_or_none(self._search_regex(
                r'\bdata-num-reactions="(\d+)"', webpage, 'reactions', default=None)),
            'uploader': traverse_obj(
                self._yield_json_ld(webpage, video_id),
                (lambda _, v: v['@type'] == 'SocialMediaPosting', 'author', 'name', {str}), get_all=False),
            'thumbnail': self._og_search_thumbnail(webpage),
            'description': self._og_search_description(webpage, default=None),
            'subtitles': subtitles,
        }


class LinkedInLearningIE(LinkedInLearningBaseIE):
    IE_NAME = 'linkedin:learning'
    _VALID_URL = r'https?://(?:www\.)?linkedin\.com/learning/(?P<course_slug>[^/]+)/(?P<id>[^/?#]+)'
    _TEST = {
        'url': 'https://www.linkedin.com/learning/programming-foundations-fundamentals/welcome?autoplay=true',
        'md5': 'a1d74422ff0d5e66a792deb996693167',
        'info_dict': {
            'id': '90426',
            'ext': 'mp4',
            'title': 'Welcome',
            'timestamp': 1430396150.82,
            'upload_date': '20150430',
        },
    }

    def json2srt(self, transcript_lines, duration=None):
        srt_data = ''
        for line, (line_dict, next_dict) in enumerate(itertools.zip_longest(transcript_lines, transcript_lines[1:])):
            start_time, caption = line_dict['transcriptStartAt'] / 1000, line_dict['caption']
            end_time = next_dict['transcriptStartAt'] / 1000 if next_dict else duration or start_time + 1
            srt_data += '%d\n%s --> %s\n%s\n\n' % (line + 1, srt_subtitles_timecode(start_time),
                                                   srt_subtitles_timecode(end_time),
                                                   caption)
        return srt_data

    def _real_extract(self, url):
        course_slug, video_slug = self._match_valid_url(url).groups()

        formats = []
        for width, height in ((640, 360), (960, 540), (1280, 720)):
            video_data = self._call_api(
                course_slug, 'selectedVideo', video_slug, height)['selectedVideo']

            video_url_data = video_data.get('url') or {}
            progressive_url = video_url_data.get('progressiveUrl')
            if progressive_url:
                formats.append({
                    'format_id': 'progressive-%dp' % height,
                    'url': progressive_url,
                    'ext': 'mp4',
                    'height': height,
                    'width': width,
                    'source_preference': 1,
                })

        title = video_data['title']

        audio_url = video_data.get('audio', {}).get('progressiveUrl')
        if audio_url:
            formats.append({
                'abr': 64,
                'ext': 'm4a',
                'format_id': 'audio',
                'url': audio_url,
                'vcodec': 'none',
            })

        streaming_url = video_url_data.get('streamingUrl')
        if streaming_url:
            formats.extend(self._extract_m3u8_formats(
                streaming_url, video_slug, 'mp4',
                'm3u8_native', m3u8_id='hls', fatal=False))

        subtitles = {}
        duration = int_or_none(video_data.get('durationInSeconds'))
        transcript_lines = try_get(video_data, lambda x: x['transcript']['lines'], expected_type=list)
        if transcript_lines:
            subtitles['en'] = [{
                'ext': 'srt',
                'data': self.json2srt(transcript_lines, duration)
            }]

        return {
            'id': self._get_video_id(video_data, course_slug, video_slug),
            'title': title,
            'formats': formats,
            'thumbnail': video_data.get('defaultThumbnail'),
            'timestamp': float_or_none(video_data.get('publishedOn'), 1000),
            'duration': duration,
            'subtitles': subtitles,
            # It seems like this would be correctly handled by default
            # However, unless someone can confirm this, the old
            # behaviour is being kept as-is
            '_format_sort_fields': ('res', 'source_preference')
        }


class LinkedInLearningCourseIE(LinkedInLearningBaseIE):
    IE_NAME = 'linkedin:learning:course'
    _VALID_URL = r'https?://(?:www\.)?linkedin\.com/learning/(?P<id>[^/?#]+)'
    _TEST = {
        'url': 'https://www.linkedin.com/learning/programming-foundations-fundamentals',
        'info_dict': {
            'id': 'programming-foundations-fundamentals',
            'title': 'Programming Foundations: Fundamentals',
            'description': 'md5:76e580b017694eb89dc8e8923fff5c86',
        },
        'playlist_mincount': 61,
    }

    @classmethod
    def suitable(cls, url):
        return False if LinkedInLearningIE.suitable(url) else super(LinkedInLearningCourseIE, cls).suitable(url)

    def _real_extract(self, url):
        course_slug = self._match_id(url)
        course_data = self._call_api(course_slug, 'chapters,description,title')

        entries = []
        for chapter_number, chapter in enumerate(course_data.get('chapters', []), 1):
            chapter_title = chapter.get('title')
            chapter_id = self._get_urn_id(chapter)
            for video in chapter.get('videos', []):
                video_slug = video.get('slug')
                if not video_slug:
                    continue
                entries.append({
                    '_type': 'url_transparent',
                    'id': self._get_video_id(video, course_slug, video_slug),
                    'title': video.get('title'),
                    'url': 'https://www.linkedin.com/learning/%s/%s' % (course_slug, video_slug),
                    'chapter': chapter_title,
                    'chapter_number': chapter_number,
                    'chapter_id': chapter_id,
                    'ie_key': LinkedInLearningIE.ie_key(),
                })

        return self.playlist_result(
            entries, course_slug,
            course_data.get('title'),
            course_data.get('description'))
