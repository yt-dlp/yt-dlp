# coding: utf-8
from __future__ import unicode_literals

import re
import json

from .common import InfoExtractor
from ..compat import (
    compat_HTTPError,
)

from ..utils import (
    ExtractorError,
    traverse_obj,
    urlencode_postdata,
)


class DigitalConcertHallIE(InfoExtractor):
    IE_DESC = 'DigitalConcertHall extractor'
    _VALID_URL = r'https?://(?:www\.)?digitalconcerthall\.com/(?P<language>[a-z]+)/concert/(?P<id>[0-9]+)'
    _LOGIN_URL = 'https://www.digitalconcerthall.com/en/login'
    _OAUTH_URL = 'https://api.digitalconcerthall.com/v2/oauth2/token'
    _ACCESS_TOKEN = 'none'
    _CLIENT_SECRET = '2ySLN+2Fwb'
    _NETRC_MACHINE = 'digitalconcerthall'
    # if you don't login, all you will get is trailers
    _LOGIN_REQUIRED = True
    _TESTS = [{
        'url': 'https://www.digitalconcerthall.com/en/concert/53785',
        'md5': 'TODO: md5 sum of the first 10241 bytes of the video file (use --test)',
        'info_dict': {
            'id': '53785',
            'language': 'en',
            'ext': 'mp4',
            'title': 'Video title goes here',
            'thumbnail': r're:^https?://.*/images/core/Phil.*\.jpg$',
        }
    }]

    def debug_out(self, args):
        if not self._downloader.params.get('verbose', False):
            return

        self.to_screen('[debug] %s' % args)

    def _login(self):
        username, password = self._get_login_info()
        if username is None:
            if self._LOGIN_REQUIRED:
                raise ExtractorError('No login info available, needed for using %s.' % self.IE_NAME, expected=True)
            return
        # first get JWT token
        data = {
            'affiliate': 'none',
            'grant_type': 'device',
            'device_vendor': 'unknown',
            'device_model': 'unknown',
            'app_id': 'dch.webapp',
            'app_distributor': 'berlinphil',
            'app_version': '1.0.0',
            'client_secret': self._CLIENT_SECRET,
        }
        try:
            token_response = self._download_json(
                self._OAUTH_URL,
                None, 'Obtaining token', data=urlencode_postdata(data), headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                })
        except ExtractorError as e:
            msg = 'Unable to obtain token'
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 401:
                resp = self._parse_json(e.cause.read().decode(), None, fatal=False)
                if resp:
                    error = resp.get('extra_info') or resp.get('error_description') or resp.get('error')
                    if error:
                        msg += ': ' + error
            raise ExtractorError('Unable to obtain token: ' + msg)
        self.debug_out("token_response: " + json.dumps(token_response))
        self._ACCESS_TOKEN = token_response.get('access_token')
        # now login
        data = {
            'grant_type': 'password',
            'username': username,
            'password': password,
        }
        try:
            self._download_json(
                self._OAUTH_URL,
                None, 'Logging in', data=urlencode_postdata(data), headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': self._LOGIN_URL,
                    'Authorization': 'Bearer ' + self._ACCESS_TOKEN
                })
        except ExtractorError as e:
            msg = 'Unable to login'
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 401:
                resp = self._parse_json(e.cause.read().decode(), None, fatal=False)
                if resp:
                    error = resp.get('extra_info') or resp.get('error_description') or resp.get('error')
                    if error:
                        msg += ': ' + error
            raise ExtractorError('Unable to log in: ' + msg)

    def _real_initialize(self):
        self._login()

    def _real_extract(self, url):
        language, video_id = self._match_valid_url(url).groups()
        if not language:
            language = 'en'
        self.debug_out("url: " + url + " video_id: " + video_id + " language: " + language)
        webpage = self._download_webpage(url, video_id)
        playlist_title = self._html_search_regex(r'<title>(.+?)</title>', webpage, 'title') or \
            self._og_search_title(webpage)
        self.debug_out("playlist_title: " + playlist_title)

        # use the API to get other information about the concert
        vid_info_dict = self._download_json(
            'https://api.digitalconcerthall.com/v2/concert/'
            + video_id, video_id, headers={'Accept': 'application/json',
                                           'Accept-Language': language})
        embedded = vid_info_dict.get('_embedded')
        entries = []
        for embed_type in embedded:
            # embed_type should be either 'work' or 'interview'
            # 'work' will be an array of one or more works
            for item in embedded.get(embed_type):
                if embed_type == 'interview':
                    item['is_interview'] = 1
                else:
                    item['is_interview'] = 0
                stream_href = traverse_obj(item,('_links','streams','href'))
                self.debug_out("JSON URL: " + 'https:' + stream_href)
                test_dict = self._download_json('https:' + stream_href, video_id,
                    headers={'Accept': 'application/json',
                    'Authorization': 'Bearer ' + self._ACCESS_TOKEN,
                    'Accept-Language': language})
                m3u8_url = traverse_obj(test_dict, ('channel', lambda x: x.startswith('vod_mixed'), 'stream', 0, 'url'), get_all=False)
                self.debug_out('stream URL: ' + m3u8_url)

                formats = self._extract_m3u8_formats(
                    m3u8_url, video_id, 'mp4', 'm3u8_native', fatal=False)
                self._sort_formats(formats)

                if item.get('is_interview') == 1:
                    title = "Interview - " + item.get('title', "unknown interview title")
                else:
                    title = (item.get('name_composer') if item.get('name_composer')
                            else 'unknown composer') + ' - ' + item.get('title', "unknown title")
                key = item.get('id')

                duration = item.get('duration_total')
                # append the duration in minutes to the title
                title = title + " (" + str(round(duration / 60)) + " min.)"
                self.debug_out("title: " + title)
                timestamp = traverse_obj(item,('date','published'))
                entries.append({
                    'id': key,
                    'title': title,
                    'url': m3u8_url,
                    'formats': formats,
                    'duration': duration,
                    'timestamp': timestamp,
                })
                # use playlist description for video description by default
                # but if the video has a description, use it
                description = test_dict.get('short_description') or item.get('short_description')
                if description:
                    entries[-1]['description'] = description
                if item.get('cuepoints'):
                    chapters = []
                    first_chapter = 1
                    for chapter in item.get('cuepoints'):
                        start_time = chapter.get('time')
                        # Often, the first chapter does not start at zero.  In this case,
                        # insert an intro chapter so that first chapter is the start of the music
                        if (first_chapter == 1) and (start_time != 0):
                            chapters.append({
                                'start_time': 0,
                                'end_time': start_time,
                                'title': '0. Intro'
                            })
                        first_chapter = 0
                        end_time = start_time + chapter.get('duration')
                        chapter_title = chapter.get('text')
                        chapters.append({
                            'start_time': start_time,
                            'end_time': end_time,
                            'title': chapter_title
                        })
                    entries[-1]['chapters'] = chapters

        return {
            '_type': 'playlist',
            'id': video_id,
            'title': playlist_title,
            'entries': entries,
        }
