from __future__ import unicode_literals

import os
import re

from .common import InfoExtractor, compat_urllib_parse_unquote
from ..utils import (
    HEADRequest,
    sanitized_Request,
    unified_timestamp,
    url_basename,
)


class BreitBartIE(InfoExtractor):
    _VALID_URL = r"https?:\/\/(?:www\.)breitbart.com/videos/v/(.*?)/"

    @classmethod
    def _get_video_id(cls, url):
        if '_VALID_URL_RE' not in cls.__dict__:
            cls._VALID_URL_RE = re.compile(cls._VALID_URL)

        if cls._VALID_URL_RE.match(url) is not None:
            return cls._VALID_URL_RE.match(url).group(1)
        else:
            return ""

    def _generic_id(self, url):
        return compat_urllib_parse_unquote(os.path.splitext(url.rstrip('/').split('/')[-1])[0])

    def _generic_title(self, url):
        return compat_urllib_parse_unquote(os.path.splitext(url_basename(url))[0])

    def _real_extract(self, url):
        video_id = self._get_video_id(url)
        if not video_id:
            return {}

        head_req = HEADRequest(url)
        head_response = self._request_webpage(
            head_req, video_id,
            note=False, errnote='Could not send HEAD request to %s' % url,
            fatal=False)

        info_dict = {
            'id': video_id,
            'title': self._generic_title(url),
            'timestamp': unified_timestamp(head_response.headers.get('Last-Modified'))
        }

        request = sanitized_Request(url)
        request.add_header('Accept-Encoding', '*')
        full_response = self._request_webpage(request, video_id)
        first_bytes = full_response.read(512)
        webpage = self._webpage_read_content(
            full_response, url, video_id, prefix=first_bytes)

        video_title = self._og_search_title(
            webpage, default=None) or self._html_search_regex(
            r'(?s)<title>(.*?)</title>', webpage, 'video title',
            default='video')

        video_description = self._og_search_description(webpage, default=None)
        video_thumbnail = self._og_search_thumbnail(webpage, default=None)

        age_limit = self._rta_search(webpage)
        info_dict.update({
            'title': video_title,
            'description': video_description,
            'thumbnail': video_thumbnail,
            'age_limit': age_limit,
        })

        video_url = "https://cdn.jwplayer.com/manifests/{}.m3u8".format(video_id)
        info_dict['formats'] = self._extract_m3u8_formats(video_url, video_id, ext='mp4')
        if info_dict.get('formats'):
            self._sort_formats(info_dict['formats'])

        return info_dict
