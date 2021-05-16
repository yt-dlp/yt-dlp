# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    urlencode_postdata,
    ExtractorError,
)


class BigoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?bigo\.tv/(?:[a-z]{2,}/)?(?P<id>[^/]+)'
    # Note: I would like to provide some real test, but Bigo is a live streaming
    # site, and a test would require that the broadcaster is live at the moment.
    # So, I don't have a good way to provide a real test here.
    _TESTS = [{
        'url': 'https://www.bigo.tv/th/Tarlerm1304',
        'only_matching': True,
    }, {
        'url': 'https://bigo.tv/115976881',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        user_id = self._match_id(url)

        INFO_URL = 'https://bigo.tv/studio/getInternalStudioInfo'
        info_raw = self._download_json(
            INFO_URL, user_id, data=urlencode_postdata({'siteId': user_id}))

        if info_raw['code'] != 0:
            if self._downloader.params.get('verbose', False):
                self.to_screen(
                    '[debug] getInternalStudioInfo returns code %i, msg "%s"'
                    % (info_raw['code'], info_raw['msg']))

            raise ExtractorError(
                "Failed to get user's data. Most likely the user doesn't exist",
                expected=True)
        info = info_raw['data']

        alive = info.get('alive')
        if alive is not None and alive == 0:
            raise ExtractorError(
                'User "%s" is not live at the moment' % user_id,
                expected=True)

        return {
            'id': info.get('roomId') or user_id,
            'title': info.get('roomTopic'),
            'url': info.get('hls_src'),
            'ext': 'mp4',
            'thumbnail': info.get('snapshot'),
            'uploader': info.get('nick_name'),
            'is_live': True,
        }
