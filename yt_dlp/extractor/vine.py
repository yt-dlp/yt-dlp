# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    determine_ext,
    int_or_none,
    unified_timestamp,
)


class VineIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?vine\.co/(?:v|oembed)/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://vine.co/v/b9KOOWX7HUx',
        'md5': '2f36fed6235b16da96ce9b4dc890940d',
        'info_dict': {
            'id': 'b9KOOWX7HUx',
            'ext': 'mp4',
            'title': 'Chicken.',
            'alt_title': 'Vine by Jack',
            'timestamp': 1368997951,
            'upload_date': '20130519',
            'uploader': 'Jack',
            'uploader_id': '76',
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'repost_count': int,
        },
    }, {
        'url': 'https://vine.co/v/e192BnZnZ9V',
        'info_dict': {
            'id': 'e192BnZnZ9V',
            'ext': 'mp4',
            'title': 'ยิ้ม~ เขิน~ อาย~ น่าร้ากอ้ะ >//< @n_whitewo @orlameena #lovesicktheseries  #lovesickseason2',
            'alt_title': 'Vine by Pimry_zaa',
            'timestamp': 1436057405,
            'upload_date': '20150705',
            'uploader': 'Pimry_zaa',
            'uploader_id': '1135760698325307392',
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'repost_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://vine.co/v/MYxVapFvz2z',
        'only_matching': True,
    }, {
        'url': 'https://vine.co/v/bxVjBbZlPUH',
        'only_matching': True,
    }, {
        'url': 'https://vine.co/oembed/MYxVapFvz2z.json',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        data = self._download_json(
            'https://archive.vine.co/posts/%s.json' % video_id, video_id)

        def video_url(kind):
            for url_suffix in ('Url', 'URL'):
                format_url = data.get('video%s%s' % (kind, url_suffix))
                if format_url:
                    return format_url

        formats = []
        for quality, format_id in enumerate(('low', '', 'dash')):
            format_url = video_url(format_id.capitalize())
            if not format_url:
                continue
            # DASH link returns plain mp4
            if format_id == 'dash' and determine_ext(format_url) == 'mpd':
                formats.extend(self._extract_mpd_formats(
                    format_url, video_id, mpd_id='dash', fatal=False))
            else:
                formats.append({
                    'url': format_url,
                    'format_id': format_id or 'standard',
                    'quality': quality,
                })
        self._check_formats(formats, video_id)
        self._sort_formats(formats)

        username = data.get('username')

        alt_title = 'Vine by %s' % username if username else None

        return {
            'id': video_id,
            'title': data.get('description') or alt_title or 'Vine video',
            'alt_title': alt_title,
            'thumbnail': data.get('thumbnailUrl'),
            'timestamp': unified_timestamp(data.get('created')),
            'uploader': username,
            'uploader_id': data.get('userIdStr'),
            'view_count': int_or_none(data.get('loops')),
            'like_count': int_or_none(data.get('likes')),
            'comment_count': int_or_none(data.get('comments')),
            'repost_count': int_or_none(data.get('reposts')),
            'formats': formats,
        }


class VineUserIE(InfoExtractor):
    IE_NAME = 'vine:user'
    _VALID_URL = r'https?://vine\.co/(?P<u>u/)?(?P<user>[^/]+)'
    _VINE_BASE_URL = 'https://vine.co/'
    _TESTS = [{
        'url': 'https://vine.co/itsruthb',
        'info_dict': {
            'id': 'itsruthb',
            'title': 'Ruth B',
            'description': '| Instagram/Twitter: itsruthb | still a lost boy from neverland',
        },
        'playlist_mincount': 611,
    }, {
        'url': 'https://vine.co/u/942914934646415360',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if VineIE.suitable(url) else super(VineUserIE, cls).suitable(url)

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        user = mobj.group('user')
        u = mobj.group('u')

        profile_url = '%sapi/users/profiles/%s%s' % (
            self._VINE_BASE_URL, 'vanity/' if not u else '', user)
        profile_data = self._download_json(
            profile_url, user, note='Downloading user profile data')

        data = profile_data['data']
        user_id = data.get('userId') or data['userIdStr']
        profile = self._download_json(
            'https://archive.vine.co/profiles/%s.json' % user_id, user_id)
        entries = [
            self.url_result(
                'https://vine.co/v/%s' % post_id, ie='Vine', video_id=post_id)
            for post_id in profile['posts']
            if post_id and isinstance(post_id, compat_str)]
        return self.playlist_result(
            entries, user, profile.get('username'), profile.get('description'))
