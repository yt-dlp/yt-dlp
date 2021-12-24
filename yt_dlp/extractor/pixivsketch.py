# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    traverse_obj,
    ExtractorError,
    unified_timestamp,
)


class PixivSketchBaseIE(InfoExtractor):
    def _call_api(self, video_id, path, referer):
        response = self._download_json(f'https://sketch.pixiv.net/api/{path}', video_id, headers={
            'Referer': referer,
            # this is correct
            'X-Requested-With': referer,
        })
        errors = traverse_obj(response, ('errors', ..., 'message'))
        if errors:
            raise ExtractorError(' '.join(f'{e}.' for e in errors))
        return response.get('data') or {}


class PixivSketchIE(PixivSketchBaseIE):
    IE_NAME = 'pixiv:sketch'
    _VALID_URL = r'https?://sketch\.pixiv\.net/@(?P<uploader_id>[a-zA-Z0-9_-]+)/lives/(?P<id>\d+)/?'
    _TESTS = [{
        'url': 'https://sketch.pixiv.net/@nuhutya/lives/3654620468641830507',
        'info_dict': {
            'id': '3654620468641830507',
            'title': 'やっぱクリスマス絵は描きたい',
            'uploader': 'ぬふちゃ',
            'uploader_id': 'nuhutya',
            'age_limit': 0,
        },
        'skip': True,
    }, {
        # these two (age_limit > 0) requires you to login on website, but it's actually not required for download
        'url': 'https://sketch.pixiv.net/@namahyou/lives/4393103321546851377',
        'info_dict': {
            'id': '4393103321546851377',
            'title': '描きます',
            'uploader': 'なまひゆ',
            'uploader_id': 'namahyou',
            'uploader_id_numeric': '13075529',
            'uploader_pixiv_id': '13075529',
            'age_limit': 15,
        },
        'skip': True,
    }, {
        'url': 'https://sketch.pixiv.net/@8aki/lives/3553803162487249670',
        'info_dict': {
            'id': '3553803162487249670',
            'title': '原稿',
            'uploader': '8aki',
            'uploader_id': '8aki',
            'age_limit': 18,
            'timestamp': 1640074398,
        },
        'skip': True,
    }]

    def _real_extract(self, url):
        video_id, uploader_id = self._match_valid_url(url).group('id', 'uploader_id')
        data = self._call_api(video_id, f'lives/{video_id}.json', url)

        if not traverse_obj(data, 'is_broadcasting'):
            raise ExtractorError(f'This live is offline. Use https://sketch.pixiv.net/@{uploader_id} for ongoing live.', expected=True)

        m3u8_url = traverse_obj(data, ('owner', 'hls_movie', 'url'))
        if not m3u8_url:
            raise ExtractorError('Failed to extract m3u8 URL')
        formats = self._extract_m3u8_formats(
            m3u8_url, video_id, ext='mp4',
            entry_protocol='m3u8_native', m3u8_id='hls')
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': data.get('name'),
            'formats': formats,
            'uploader': traverse_obj(data, ('user', 'name'), ('owner', 'user', 'name')),
            'uploader_id': traverse_obj(data, ('user', 'unique_name'), ('owner', 'user', 'unique_name')),
            'uploader_pixiv_id': traverse_obj(data, ('user', 'pixiv_user_id'), ('owner', 'user', 'pixiv_user_id')),
            'age_limit': 18 if data.get('is_r18') else 15 if data.get('is_r15') else 0,
            'timestamp': unified_timestamp(data.get('created_at')),
            'is_live': True
        }


class PixivSketchUserIE(PixivSketchBaseIE):
    IE_NAME = 'pixiv:sketch:user'
    _VALID_URL = r'https?://sketch\.pixiv\.net/@(?P<id>[a-zA-Z0-9_-]+)/?'
    _TESTS = [{
        'url': 'https://sketch.pixiv.net/@nuhutya',
        'only_matching': True,
    }, {
        'url': 'https://sketch.pixiv.net/@namahyou',
        'only_matching': True,
    }, {
        'url': 'https://sketch.pixiv.net/@8aki',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return super(PixivSketchUserIE, cls).suitable(url) and not PixivSketchIE.suitable(url)

    def _real_extract(self, url):
        user_id = self._match_id(url)
        data = self._call_api(user_id, f'lives/users/@{user_id}.json', url)

        if not traverse_obj(data, 'is_broadcasting'):
            # cannot differentiate the two just by only one request
            raise ExtractorError('Either you are not logged in, or this user is really offline', expected=True)

        return self.url_result(f'https://sketch.pixiv.net/@{user_id}/lives/{data["id"]}')
