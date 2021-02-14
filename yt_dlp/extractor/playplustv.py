# coding: utf-8
from __future__ import unicode_literals

import json
import re

from .common import InfoExtractor
from ..compat import compat_HTTPError
from ..utils import (
    clean_html,
    ExtractorError,
    int_or_none,
    PUTRequest,
)


class PlayPlusTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?playplus\.(?:com|tv)/VOD/(?P<project_id>[0-9]+)/(?P<id>[0-9a-f]{32})'
    _TEST = {
        'url': 'https://www.playplus.tv/VOD/7572/db8d274a5163424e967f35a30ddafb8e',
        'md5': 'd078cb89d7ab6b9df37ce23c647aef72',
        'info_dict': {
            'id': 'db8d274a5163424e967f35a30ddafb8e',
            'ext': 'mp4',
            'title': 'Capítulo 179 - Final',
            'description': 'md5:01085d62d8033a1e34121d3c3cabc838',
            'timestamp': 1529992740,
            'upload_date': '20180626',
        },
        'skip': 'Requires account credential',
    }
    _NETRC_MACHINE = 'playplustv'
    _GEO_COUNTRIES = ['BR']
    _token = None
    _profile_id = None

    def _call_api(self, resource, video_id=None, query=None):
        return self._download_json('https://api.playplus.tv/api/media/v2/get' + resource, video_id, headers={
            'Authorization': 'Bearer ' + self._token,
        }, query=query)

    def _real_initialize(self):
        email, password = self._get_login_info()
        if email is None:
            self.raise_login_required()

        req = PUTRequest(
            'https://api.playplus.tv/api/web/login', json.dumps({
                'email': email,
                'password': password,
            }).encode(), {
                'Content-Type': 'application/json; charset=utf-8',
            })

        try:
            self._token = self._download_json(req, None)['token']
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 401:
                raise ExtractorError(self._parse_json(
                    e.cause.read(), None)['errorMessage'], expected=True)
            raise

        self._profile = self._call_api('Profiles')['list'][0]['_id']

    def _real_extract(self, url):
        project_id, media_id = re.match(self._VALID_URL, url).groups()
        media = self._call_api(
            'Media', media_id, {
                'profileId': self._profile,
                'projectId': project_id,
                'mediaId': media_id,
            })['obj']
        title = media['title']

        formats = []
        for f in media.get('files', []):
            f_url = f.get('url')
            if not f_url:
                continue
            file_info = f.get('fileInfo') or {}
            formats.append({
                'url': f_url,
                'width': int_or_none(file_info.get('width')),
                'height': int_or_none(file_info.get('height')),
            })
        self._sort_formats(formats)

        thumbnails = []
        for thumb in media.get('thumbs', []):
            thumb_url = thumb.get('url')
            if not thumb_url:
                continue
            thumbnails.append({
                'url': thumb_url,
                'width': int_or_none(thumb.get('width')),
                'height': int_or_none(thumb.get('height')),
            })

        return {
            'id': media_id,
            'title': title,
            'formats': formats,
            'thumbnails': thumbnails,
            'description': clean_html(media.get('description')) or media.get('shortDescription'),
            'timestamp': int_or_none(media.get('publishDate'), 1000),
            'view_count': int_or_none(media.get('numberOfViews')),
            'comment_count': int_or_none(media.get('numberOfComments')),
            'tags': media.get('tags'),
        }
