# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    determine_ext,
    ExtractorError,
    float_or_none,
    get_element_by_class,
    get_element_by_id,
    parse_duration,
    remove_end,
    urlencode_postdata,
    urljoin,
)


class TeamTreeHouseIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?teamtreehouse\.com/library/(?P<id>[^/]+)'
    _TESTS = [{
        # Course
        'url': 'https://teamtreehouse.com/library/introduction-to-user-authentication-in-php',
        'info_dict': {
            'id': 'introduction-to-user-authentication-in-php',
            'title': 'Introduction to User Authentication in PHP',
            'description': 'md5:405d7b4287a159b27ddf30ca72b5b053',
        },
        'playlist_mincount': 24,
    }, {
        # WorkShop
        'url': 'https://teamtreehouse.com/library/deploying-a-react-app',
        'info_dict': {
            'id': 'deploying-a-react-app',
            'title': 'Deploying a React App',
            'description': 'md5:10a82e3ddff18c14ac13581c9b8e5921',
        },
        'playlist_mincount': 4,
    }, {
        # Video
        'url': 'https://teamtreehouse.com/library/application-overview-2',
        'info_dict': {
            'id': 'application-overview-2',
            'ext': 'mp4',
            'title': 'Application Overview',
            'description': 'md5:4b0a234385c27140a4378de5f1e15127',
        },
        'expected_warnings': ['This is just a preview'],
    }]
    _NETRC_MACHINE = 'teamtreehouse'

    def _real_initialize(self):
        email, password = self._get_login_info()
        if email is None:
            return

        signin_page = self._download_webpage(
            'https://teamtreehouse.com/signin',
            None, 'Downloading signin page')
        data = self._form_hidden_inputs('new_user_session', signin_page)
        data.update({
            'user_session[email]': email,
            'user_session[password]': password,
        })
        error_message = get_element_by_class('error-message', self._download_webpage(
            'https://teamtreehouse.com/person_session',
            None, 'Logging in', data=urlencode_postdata(data)))
        if error_message:
            raise ExtractorError(clean_html(error_message), expected=True)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        title = self._html_search_meta(['og:title', 'twitter:title'], webpage)
        description = self._html_search_meta(
            ['description', 'og:description', 'twitter:description'], webpage)
        entries = self._parse_html5_media_entries(url, webpage, display_id)
        if entries:
            info = entries[0]

            for subtitles in info.get('subtitles', {}).values():
                for subtitle in subtitles:
                    subtitle['ext'] = determine_ext(subtitle['url'], 'srt')

            is_preview = 'data-preview="true"' in webpage
            if is_preview:
                self.report_warning(
                    'This is just a preview. You need to be signed in with a Basic account to download the entire video.', display_id)
                duration = 30
            else:
                duration = float_or_none(self._search_regex(
                    r'data-duration="(\d+)"', webpage, 'duration'), 1000)
                if not duration:
                    duration = parse_duration(get_element_by_id(
                        'video-duration', webpage))

            info.update({
                'id': display_id,
                'title': title,
                'description': description,
                'duration': duration,
            })
            return info
        else:
            def extract_urls(html, extract_info=None):
                for path in re.findall(r'<a[^>]+href="([^"]+)"', html):
                    page_url = urljoin(url, path)
                    entry = {
                        '_type': 'url_transparent',
                        'id': self._match_id(page_url),
                        'url': page_url,
                        'id_key': self.ie_key(),
                    }
                    if extract_info:
                        entry.update(extract_info)
                    entries.append(entry)

            workshop_videos = self._search_regex(
                r'(?s)<ul[^>]+id="workshop-videos"[^>]*>(.+?)</ul>',
                webpage, 'workshop videos', default=None)
            if workshop_videos:
                extract_urls(workshop_videos)
            else:
                stages_path = self._search_regex(
                    r'(?s)<div[^>]+id="syllabus-stages"[^>]+data-url="([^"]+)"',
                    webpage, 'stages path')
                if stages_path:
                    stages_page = self._download_webpage(
                        urljoin(url, stages_path), display_id, 'Downloading stages page')
                    for chapter_number, (chapter, steps_list) in enumerate(re.findall(r'(?s)<h2[^>]*>\s*(.+?)\s*</h2>.+?<ul[^>]*>(.+?)</ul>', stages_page), 1):
                        extract_urls(steps_list, {
                            'chapter': chapter,
                            'chapter_number': chapter_number,
                        })
                    title = remove_end(title, ' Course')

            return self.playlist_result(
                entries, display_id, title, description)
