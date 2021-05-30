# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    get_element_by_class,
    int_or_none,
    parse_iso8601,
    str_or_none,
    strip_or_none,
    try_get,
    urlencode_postdata,
)


class VidioIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?vidio\.com/watch/(?P<id>\d+)-(?P<display_id>[^/?#&]+)'
    _TESTS = [{
        'url': 'http://www.vidio.com/watch/165683-dj_ambred-booyah-live-2015',
        'md5': 'cd2801394afc164e9775db6a140b91fe',
        'info_dict': {
            'id': '165683',
            'display_id': 'dj_ambred-booyah-live-2015',
            'ext': 'mp4',
            'title': 'DJ_AMBRED - Booyah (Live 2015)',
            'description': 'md5:27dc15f819b6a78a626490881adbadf8',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 149,
            'like_count': int,
            'uploader': 'TWELVE Pic',
            'timestamp': 1444902800,
            'upload_date': '20151015',
            'uploader_id': 'twelvepictures',
            'channel': 'Cover Music Video',
            'channel_id': '280236',
            'view_count': int,
            'dislike_count': int,
            'comment_count': int,
            'tags': 'count:4',
        },
    }, {
        'url': 'https://www.vidio.com/watch/77949-south-korea-test-fires-missile-that-can-strike-all-of-the-north',
        'only_matching': True,
    }, {
        # Premier-exclusive video
        'url': 'https://www.vidio.com/watch/1550718-stand-by-me-doraemon',
        'only_matching': True
    }]
    _LOGIN_URL = 'https://www.vidio.com/users/login'
    _NETRC_MACHINE = 'vidio'

    def _login(self):
        username, password = self._get_login_info()
        if username is None:
            return

        def is_logged_in():
            res = self._download_json(
                'https://www.vidio.com/interactions.json', None, 'Checking if logged in', fatal=False) or {}
            return bool(res.get('current_user'))

        if is_logged_in():
            return

        login_page = self._download_webpage(
            self._LOGIN_URL, None, 'Downloading log in page')

        login_form = self._form_hidden_inputs("login-form", login_page)
        login_form.update({
            'user[login]': username,
            'user[password]': password,
        })
        login_post, login_post_urlh = self._download_webpage_handle(
            self._LOGIN_URL, None, 'Logging in', data=urlencode_postdata(login_form), expected_status=[302, 401])

        if login_post_urlh.status == 401:
            reason = get_element_by_class('onboarding-form__general-error', login_post)
            if reason:
                raise ExtractorError(
                    'Unable to log in: %s' % reason, expected=True)
            raise ExtractorError('Unable to log in')

    def _real_initialize(self):
        self._api_key = self._download_json(
            'https://www.vidio.com/auth', None, data=b'')['api_key']
        self._login()

    def _real_extract(self, url):
        video_id, display_id = re.match(self._VALID_URL, url).groups()
        data = self._download_json(
            'https://api.vidio.com/videos/' + video_id, display_id, headers={
                'Content-Type': 'application/vnd.api+json',
                'X-API-KEY': self._api_key,
            })
        video = data['videos'][0]
        title = video['title'].strip()
        is_premium = video.get('is_premium')
        if is_premium:
            sources = self._download_json(
                'https://www.vidio.com/interactions_stream.json?video_id=%s&type=videos' % video_id,
                display_id, note='Downloading premier API JSON')
            if not (sources.get('source') or sources.get('source_dash')):
                self.raise_login_required('This video is only available for registered users with a premier subscription.')

            formats, subs = [], {}
            if sources.get('source'):
                hls_formats, hls_subs = self._extract_m3u8_formats_and_subtitles(
                    sources['source'], display_id, 'mp4', 'm3u8_native')
                formats.extend(hls_formats)
                subs.update(hls_subs)
            if sources.get('source_dash'):  # TODO: Find video example with source_dash
                dash_formats, dash_subs = self._extract_mpd_formats_and_subtitles(
                    sources['source_dash'], display_id, 'dash')
                formats.extend(dash_formats)
                subs.update(dash_subs)
        else:
            hls_url = data['clips'][0]['hls_url']
            formats, subs = self._extract_m3u8_formats_and_subtitles(
                hls_url, display_id, 'mp4', 'm3u8_native')

        self._sort_formats(formats)

        get_first = lambda x: try_get(data, lambda y: y[x + 's'][0], dict) or {}
        channel = get_first('channel')
        user = get_first('user')
        username = user.get('username')
        get_count = lambda x: int_or_none(video.get('total_' + x))

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': strip_or_none(video.get('description')),
            'thumbnail': video.get('image_url_medium'),
            'duration': int_or_none(video.get('duration')),
            'like_count': get_count('likes'),
            'formats': formats,
            'subtitles': subs,
            'uploader': user.get('name'),
            'timestamp': parse_iso8601(video.get('created_at')),
            'uploader_id': username,
            'uploader_url': 'https://www.vidio.com/@' + username if username else None,
            'channel': channel.get('name'),
            'channel_id': str_or_none(channel.get('id')),
            'view_count': get_count('view_count'),
            'dislike_count': get_count('dislikes'),
            'comment_count': get_count('comments'),
            'tags': video.get('tag_list'),
        }
