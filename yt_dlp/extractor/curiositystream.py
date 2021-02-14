# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    urlencode_postdata,
    compat_str,
    ExtractorError,
)


class CuriosityStreamBaseIE(InfoExtractor):
    _NETRC_MACHINE = 'curiositystream'
    _auth_token = None
    _API_BASE_URL = 'https://api.curiositystream.com/v1/'

    def _handle_errors(self, result):
        error = result.get('error', {}).get('message')
        if error:
            if isinstance(error, dict):
                error = ', '.join(error.values())
            raise ExtractorError(
                '%s said: %s' % (self.IE_NAME, error), expected=True)

    def _call_api(self, path, video_id):
        headers = {}
        if self._auth_token:
            headers['X-Auth-Token'] = self._auth_token
        result = self._download_json(
            self._API_BASE_URL + path, video_id, headers=headers)
        self._handle_errors(result)
        return result['data']

    def _real_initialize(self):
        email, password = self._get_login_info()
        if email is None:
            return
        result = self._download_json(
            self._API_BASE_URL + 'login', None, data=urlencode_postdata({
                'email': email,
                'password': password,
            }))
        self._handle_errors(result)
        self._auth_token = result['message']['auth_token']


class CuriosityStreamIE(CuriosityStreamBaseIE):
    IE_NAME = 'curiositystream'
    _VALID_URL = r'https?://(?:app\.)?curiositystream\.com/video/(?P<id>\d+)'
    _TEST = {
        'url': 'https://app.curiositystream.com/video/2',
        'md5': '262bb2f257ff301115f1973540de8983',
        'info_dict': {
            'id': '2',
            'ext': 'mp4',
            'title': 'How Did You Develop The Internet?',
            'description': 'Vint Cerf, Google\'s Chief Internet Evangelist, describes how he and Bob Kahn created the internet.',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        media = self._call_api('media/' + video_id, video_id)
        title = media['title']

        formats = []
        for encoding in media.get('encodings', []):
            m3u8_url = encoding.get('master_playlist_url')
            if m3u8_url:
                formats.extend(self._extract_m3u8_formats(
                    m3u8_url, video_id, 'mp4', 'm3u8_native',
                    m3u8_id='hls', fatal=False))
            encoding_url = encoding.get('url')
            file_url = encoding.get('file_url')
            if not encoding_url and not file_url:
                continue
            f = {
                'width': int_or_none(encoding.get('width')),
                'height': int_or_none(encoding.get('height')),
                'vbr': int_or_none(encoding.get('video_bitrate')),
                'abr': int_or_none(encoding.get('audio_bitrate')),
                'filesize': int_or_none(encoding.get('size_in_bytes')),
                'vcodec': encoding.get('video_codec'),
                'acodec': encoding.get('audio_codec'),
                'container': encoding.get('container_type'),
            }
            for f_url in (encoding_url, file_url):
                if not f_url:
                    continue
                fmt = f.copy()
                rtmp = re.search(r'^(?P<url>rtmpe?://(?P<host>[^/]+)/(?P<app>.+))/(?P<playpath>mp[34]:.+)$', f_url)
                if rtmp:
                    fmt.update({
                        'url': rtmp.group('url'),
                        'play_path': rtmp.group('playpath'),
                        'app': rtmp.group('app'),
                        'ext': 'flv',
                        'format_id': 'rtmp',
                    })
                else:
                    fmt.update({
                        'url': f_url,
                        'format_id': 'http',
                    })
                formats.append(fmt)
        self._sort_formats(formats)

        subtitles = {}
        for closed_caption in media.get('closed_captions', []):
            sub_url = closed_caption.get('file')
            if not sub_url:
                continue
            lang = closed_caption.get('code') or closed_caption.get('language') or 'en'
            subtitles.setdefault(lang, []).append({
                'url': sub_url,
            })

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'description': media.get('description'),
            'thumbnail': media.get('image_large') or media.get('image_medium') or media.get('image_small'),
            'duration': int_or_none(media.get('duration')),
            'tags': media.get('tags'),
            'subtitles': subtitles,
        }


class CuriosityStreamCollectionIE(CuriosityStreamBaseIE):
    IE_NAME = 'curiositystream:collection'
    _VALID_URL = r'https?://(?:app\.)?curiositystream\.com/(?:collection|series)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://app.curiositystream.com/collection/2',
        'info_dict': {
            'id': '2',
            'title': 'Curious Minds: The Internet',
            'description': 'How is the internet shaping our lives in the 21st Century?',
        },
        'playlist_mincount': 17,
    }, {
        'url': 'https://curiositystream.com/series/2',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        collection_id = self._match_id(url)
        collection = self._call_api(
            'collections/' + collection_id, collection_id)
        entries = []
        for media in collection.get('media', []):
            media_id = compat_str(media.get('id'))
            entries.append(self.url_result(
                'https://curiositystream.com/video/' + media_id,
                CuriosityStreamIE.ie_key(), media_id))
        return self.playlist_result(
            entries, collection_id,
            collection.get('title'), collection.get('description'))
