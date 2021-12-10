# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor

from ..utils import (
    parse_resolution,
    traverse_obj,
    try_get,
    urlencode_postdata,
)


class DigitalConcertHallIE(InfoExtractor):
    IE_DESC = 'DigitalConcertHall extractor'
    _VALID_URL = r'https?://(?:www\.)?digitalconcerthall\.com/(?P<language>[a-z]+)/concert/(?P<id>[0-9]+)'
    _OAUTH_URL = 'https://api.digitalconcerthall.com/v2/oauth2/token'
    _ACCESS_TOKEN = 'none'
    _NETRC_MACHINE = 'digitalconcerthall'
    # if you don't login, all you will get is trailers
    _TESTS = [{
        'url': 'https://www.digitalconcerthall.com/en/concert/53201',
        'info_dict': {
            'id': '53201-1',
            'ext': 'mp4',
            'title': 'Kurt Weill - [Magic Night]',
            'thumbnail': r're:^https?://images.digitalconcerthall.com/cms/thumbnails.*\.jpg$',
            'upload_date': '20210624',
            'timestamp': 1624548600,
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _login(self):
        username, password = self._get_login_info()
        if not username:
            self.raise_login_required()
        token_response = self._download_json(
            self._OAUTH_URL,
            None, 'Obtaining token', errnote='Unable to obtain token', data=urlencode_postdata({
                'affiliate': 'none',
                'grant_type': 'device',
                'device_vendor': 'unknown',
                'app_id': 'dch.webapp',
                'app_version': '1.0.0',
                'client_secret': '2ySLN+2Fwb',
            }), headers={
                'Content-Type': 'application/x-www-form-urlencoded',
            })
        self._ACCESS_TOKEN = token_response['access_token']
        try:
            self._download_json(
                self._OAUTH_URL,
                None, note='Logging in', errnote='Unable to login', data=urlencode_postdata({
                    'grant_type': 'password',
                    'username': username,
                    'password': password,
                }), headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': 'https://www.digitalconcerthall.com',
                    'Authorization': 'Bearer ' + self._ACCESS_TOKEN
                })
        except Exception:
            self.raise_login_required(msg='Login info incorrect')

    def _real_initialize(self):
        self._login()

    def _real_extract(self, url):
        language, video_id = self._match_valid_url(url).groups()
        if not language:
            language = 'en'
        webpage = self._download_webpage(url, video_id)
        playlist_title = (self._html_search_regex(r'<title>(.+?)</title>', webpage, 'title')
                          or self._og_search_title(webpage))
        thumbnails = []
        thumbnail_url = (self._html_search_regex(r'(https?://images\.digitalconcerthall\.com/cms/thumbnails/.*\.jpg)',
                         webpage, 'thumbnail'))
        thumbnails.append({
            'url': thumbnail_url,
            **parse_resolution(thumbnail_url)
        })

        vid_info = self._download_json(
            f'https://api.digitalconcerthall.com/v2/concert/{video_id}', video_id, headers={
                'Accept': 'application/json',
                'Accept-Language': language
            })
        embedded = vid_info.get('_embedded')
        entries = []
        for embed_type in embedded:
            # embed_type should be either 'work' or 'interview'
            # 'work' will be an array of one or more works
            for item in embedded.get(embed_type):
                stream_href = traverse_obj(item, ('_links', 'streams', 'href'))
                stream_info = self._download_json(
                    self._proto_relative_url(stream_href), video_id,
                    headers={'Accept': 'application/json',
                             'Authorization': 'Bearer ' + self._ACCESS_TOKEN,
                             'Accept-Language': language})
                m3u8_url = traverse_obj(stream_info, ('channel', lambda x: x.startswith('vod_mixed'), 'stream', 0, 'url'), get_all=False)

                formats = self._extract_m3u8_formats(
                    m3u8_url, video_id, 'mp4', 'm3u8_native', fatal=False)
                self._sort_formats(formats)

                if embed_type == 'interview':
                    title = "Interview - " + item.get('title', "unknown interview title")
                else:
                    title = (item.get('name_composer') if item.get('name_composer')
                             else 'unknown composer') + ' - ' + item.get('title', "unknown title")
                key = item.get('id')

                duration = item.get('duration_total')
                timestamp = traverse_obj(item, ('date', 'published'))
                entries.append({
                    'id': key,
                    'title': title,
                    'url': m3u8_url,
                    'formats': formats,
                    'duration': duration,
                    'timestamp': timestamp,
                    'description': stream_info.get('short_description') or item.get('short_description'),
                    'thumbnails': thumbnails,
                })
                if item.get('cuepoints'):
                    chapters = [{
                        'start_time': chapter.get('time'),
                        'end_time': try_get(chapter, lambda x: x['time'] + x['duration']),
                        'title': chapter.get('text'),
                    } for chapter in item.get('cuepoints') or []]
                    if chapters and chapters[0]['start_time']:  # Chapters may not start from 0
                        chapters[:0] = [{'title': '0. Intro', 'start_time': 0, 'end_time': chapters[0]['start_time']}]
                    entries[-1]['chapters'] = chapters

        return {
            '_type': 'playlist',
            'id': video_id,
            'title': playlist_title,
            'entries': entries,
            'thumbnails': thumbnails,
        }
