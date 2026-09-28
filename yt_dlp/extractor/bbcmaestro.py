import re

from .common import InfoExtractor
from ..utils import orderedSet, smuggle_url, unsmuggle_url


class BBCMaestroComIE(InfoExtractor):
    _VALID_URL = (
        r'https?://(?:www\.)?bbcmaestro\.com/courses/(?P<id>[^?]+)'
    )
    _TESTS = [{
        'url': 'https://www.bbcmaestro.com/courses/julia-donaldson/writing-children-s-picture-books/trailer',
        'info_dict': {
            'id': 'julia-donaldson/writing-children-s-picture-books/trailer',
            'ext': 'mp4',
            'title': 'Course trailer',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _do_extract_video(self, url, webpage, video_id):
        if '/lessons/' not in url:
            title = 'Course trailer'
        else:
            title = self._html_search_regex(
                r'<h1\b[^>]*lesson[^>]*title[^>]*>\s*(.+?)\s*</h1>',
                webpage,
                name='title',
                flags=re.RegexFlag.S,
            )

        m3u8_url = self._html_search_regex(
            r'<source[^>]+src="?\'?(\S+\.m3u8)',
            webpage,
            'video URL',
        )
        formats = []
        if m3u8_url:
            formats = self._extract_m3u8_formats(
                m3u8_url=m3u8_url,
                video_id=video_id,
                ext='mp4',
                m3u8_id='hls',
                fatal=False,
            )

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
        }

    def _do_extract_playlist(self, url, webpage):
        # Twitter Title usually: <Lesson Title> - <Author> | <Course Title>
        twitter_title = self._html_search_meta(
            ['twitter:title'],
            webpage,
            fatal=True,
        )
        playlist_title = (
            twitter_title
            .split('-', maxsplit=1)[-1]
            .replace('|', '-')
        )

        url_without_query_parameters = url.split('?', maxsplit=1)[0]
        self.write_debug(f'url_without_query_parameters: {url_without_query_parameters}')
        playlist_id = self._search_regex(
            pattern=r'.*/courses/([^/]+/[^/]+).*',
            string=url_without_query_parameters,
            name='Playlist ID (from URL)',
            fatal=True,
        )
        self.write_debug(f'playlist_id: {playlist_id}')
        entries = [
            self.url_result(
                smuggle_url(
                    f'https://www.bbcmaestro.com/courses/{playlist_id}/lessons/{item_video_id}',
                    {'forcevideo': True},
                ),
                ie=BBCMaestroComIE.ie_key(),
            )
            for item_video_id in orderedSet(re.findall(
                r'href=[^>]*/courses/' + re.escape(playlist_id) + r'/lessons/([^?]+)',
                webpage,
            ))
        ]
        # self.write_debug('entries: %r' % entries)
        return self.playlist_result(
            entries=entries,
            playlist_id=playlist_id,
            playlist_title=playlist_title,
        )

    def _check_login_provided(self):
        if not self._cookies_passed:
            self.raise_login_required('Login details are needed to download this content', method='cookies')

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        self.write_debug(f'Extracting from: {url}')
        video_id = self._match_id(url)
        self.write_debug(f'Video ID: {video_id}')
        webpage = self._download_webpage(url, video_id)

        is_private_course_content = ('/lessons/' in url)
        is_login_required = is_private_course_content
        if is_login_required:
            # Note: We can only download the course trailer without login
            self._check_login_provided()

        is_playlist = (
            is_private_course_content
            and not smuggled_data.get('forcevideo')
            and not self.get_param('noplaylist')
        )

        if is_playlist:
            return self._do_extract_playlist(url, webpage=webpage)
        return self._do_extract_video(url, webpage=webpage, video_id=video_id)
