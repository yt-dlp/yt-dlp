from __future__ import unicode_literals

import itertools

from .common import InfoExtractor
from ..compat import compat_HTTPError
from ..utils import (
    ExtractorError,
    int_or_none,
    float_or_none,
    parse_iso8601,
    url_or_none,
)


class VidmeIE(InfoExtractor):
    IE_NAME = 'vidme'
    _VALID_URL = r'https?://vid\.me/(?:e/)?(?P<id>[\da-zA-Z]{,5})(?:[^\da-zA-Z]|$)'
    _TESTS = [{
        'url': 'https://vid.me/QNB',
        'md5': 'f42d05e7149aeaec5c037b17e5d3dc82',
        'info_dict': {
            'id': 'QNB',
            'ext': 'mp4',
            'title': 'Fishing for piranha - the easy way',
            'description': 'source: https://www.facebook.com/photo.php?v=312276045600871',
            'thumbnail': r're:^https?://.*\.jpg',
            'timestamp': 1406313244,
            'upload_date': '20140725',
            'age_limit': 0,
            'duration': 119.92,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
        },
    }, {
        'url': 'https://vid.me/Gc6M',
        'md5': 'f42d05e7149aeaec5c037b17e5d3dc82',
        'info_dict': {
            'id': 'Gc6M',
            'ext': 'mp4',
            'title': 'O Mere Dil ke chain - Arnav and Khushi VM',
            'thumbnail': r're:^https?://.*\.jpg',
            'timestamp': 1441211642,
            'upload_date': '20150902',
            'uploader': 'SunshineM',
            'uploader_id': '3552827',
            'age_limit': 0,
            'duration': 223.72,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # tests uploader field
        'url': 'https://vid.me/4Iib',
        'info_dict': {
            'id': '4Iib',
            'ext': 'mp4',
            'title': 'The Carver',
            'description': 'md5:e9c24870018ae8113be936645b93ba3c',
            'thumbnail': r're:^https?://.*\.jpg',
            'timestamp': 1433203629,
            'upload_date': '20150602',
            'uploader': 'Thomas',
            'uploader_id': '109747',
            'age_limit': 0,
            'duration': 97.859999999999999,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # nsfw test from http://naked-yogi.tumblr.com/post/118312946248/naked-smoking-stretching
        'url': 'https://vid.me/e/Wmur',
        'info_dict': {
            'id': 'Wmur',
            'ext': 'mp4',
            'title': 'naked smoking & stretching',
            'thumbnail': r're:^https?://.*\.jpg',
            'timestamp': 1430931613,
            'upload_date': '20150506',
            'uploader': 'naked-yogi',
            'uploader_id': '1638622',
            'age_limit': 18,
            'duration': 653.26999999999998,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # nsfw, user-disabled
        'url': 'https://vid.me/dzGJ',
        'only_matching': True,
    }, {
        # suspended
        'url': 'https://vid.me/Ox3G',
        'only_matching': True,
    }, {
        # deleted
        'url': 'https://vid.me/KTPm',
        'only_matching': True,
    }, {
        # no formats in the API response
        'url': 'https://vid.me/e5g',
        'info_dict': {
            'id': 'e5g',
            'ext': 'mp4',
            'title': 'Video upload (e5g)',
            'thumbnail': r're:^https?://.*\.jpg',
            'timestamp': 1401480195,
            'upload_date': '20140530',
            'uploader': None,
            'uploader_id': None,
            'age_limit': 0,
            'duration': 483,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        try:
            response = self._download_json(
                'https://api.vid.me/videoByUrl/%s' % video_id, video_id)
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 400:
                response = self._parse_json(e.cause.read(), video_id)
            else:
                raise

        error = response.get('error')
        if error:
            raise ExtractorError(
                '%s returned error: %s' % (self.IE_NAME, error), expected=True)

        video = response['video']

        if video.get('state') == 'deleted':
            raise ExtractorError(
                'Vidme said: Sorry, this video has been deleted.',
                expected=True)

        if video.get('state') in ('user-disabled', 'suspended'):
            raise ExtractorError(
                'Vidme said: This video has been suspended either due to a copyright claim, '
                'or for violating the terms of use.',
                expected=True)

        formats = []
        for f in video.get('formats', []):
            format_url = url_or_none(f.get('uri'))
            if not format_url:
                continue
            format_type = f.get('type')
            if format_type == 'dash':
                formats.extend(self._extract_mpd_formats(
                    format_url, video_id, mpd_id='dash', fatal=False))
            elif format_type == 'hls':
                formats.extend(self._extract_m3u8_formats(
                    format_url, video_id, 'mp4', entry_protocol='m3u8_native',
                    m3u8_id='hls', fatal=False))
            else:
                formats.append({
                    'format_id': f.get('type'),
                    'url': format_url,
                    'width': int_or_none(f.get('width')),
                    'height': int_or_none(f.get('height')),
                    'preference': 0 if f.get('type', '').endswith(
                        'clip') else 1,
                })

        if not formats and video.get('complete_url'):
            formats.append({
                'url': video.get('complete_url'),
                'width': int_or_none(video.get('width')),
                'height': int_or_none(video.get('height')),
            })

        self._sort_formats(formats)

        title = video['title']
        description = video.get('description')
        thumbnail = video.get('thumbnail_url')
        timestamp = parse_iso8601(video.get('date_created'), ' ')
        uploader = video.get('user', {}).get('username')
        uploader_id = video.get('user', {}).get('user_id')
        age_limit = 18 if video.get('nsfw') is True else 0
        duration = float_or_none(video.get('duration'))
        view_count = int_or_none(video.get('view_count'))
        like_count = int_or_none(video.get('likes_count'))
        comment_count = int_or_none(video.get('comment_count'))

        return {
            'id': video_id,
            'title': title or 'Video upload (%s)' % video_id,
            'description': description,
            'thumbnail': thumbnail,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'age_limit': age_limit,
            'timestamp': timestamp,
            'duration': duration,
            'view_count': view_count,
            'like_count': like_count,
            'comment_count': comment_count,
            'formats': formats,
        }


class VidmeListBaseIE(InfoExtractor):
    # Max possible limit according to https://docs.vid.me/#api-Videos-List
    _LIMIT = 100

    def _entries(self, user_id, user_name):
        for page_num in itertools.count(1):
            page = self._download_json(
                'https://api.vid.me/videos/%s?user=%s&limit=%d&offset=%d'
                % (self._API_ITEM, user_id, self._LIMIT, (page_num - 1) * self._LIMIT),
                user_name, 'Downloading user %s page %d' % (self._API_ITEM, page_num))

            videos = page.get('videos', [])
            if not videos:
                break

            for video in videos:
                video_url = video.get('full_url') or video.get('embed_url')
                if video_url:
                    yield self.url_result(video_url, VidmeIE.ie_key())

            total = int_or_none(page.get('page', {}).get('total'))
            if total and self._LIMIT * page_num >= total:
                break

    def _real_extract(self, url):
        user_name = self._match_id(url)

        user_id = self._download_json(
            'https://api.vid.me/userByUsername?username=%s' % user_name,
            user_name)['user']['user_id']

        return self.playlist_result(
            self._entries(user_id, user_name), user_id,
            '%s - %s' % (user_name, self._TITLE))


class VidmeUserIE(VidmeListBaseIE):
    IE_NAME = 'vidme:user'
    _VALID_URL = r'https?://vid\.me/(?:e/)?(?P<id>[\da-zA-Z_-]{6,})(?!/likes)(?:[^\da-zA-Z_-]|$)'
    _API_ITEM = 'list'
    _TITLE = 'Videos'
    _TESTS = [{
        'url': 'https://vid.me/MasakoX',
        'info_dict': {
            'id': '16112341',
            'title': 'MasakoX - %s' % _TITLE,
        },
        'playlist_mincount': 191,
    }, {
        'url': 'https://vid.me/unsQuare_netWork',
        'only_matching': True,
    }]


class VidmeUserLikesIE(VidmeListBaseIE):
    IE_NAME = 'vidme:user:likes'
    _VALID_URL = r'https?://vid\.me/(?:e/)?(?P<id>[\da-zA-Z_-]{6,})/likes'
    _API_ITEM = 'likes'
    _TITLE = 'Likes'
    _TESTS = [{
        'url': 'https://vid.me/ErinAlexis/likes',
        'info_dict': {
            'id': '6483530',
            'title': 'ErinAlexis - %s' % _TITLE,
        },
        'playlist_mincount': 415,
    }, {
        'url': 'https://vid.me/Kaleidoscope-Ish/likes',
        'only_matching': True,
    }]
