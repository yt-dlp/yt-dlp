# coding: utf-8
from __future__ import unicode_literals

from ..utils import (
    ExtractorError,
    merge_dicts,
    update_url_query,
)

from .common import InfoExtractor


class RecurbateIE(InfoExtractor):
    _VALID_URL = r'https?:\/\/(?:www\.)?recurbate\.com\/play\.php\?video=(?P<id>[0-9]+)'
    _TEST = {
        'url': 'https://recurbate.com/play.php?video=39161415',
        'info_dict': {
            'id': '39161415',
            'ext': 'mp4',
            'title': 'Performer zsnicole33 show on 2022-10-25 20_23, Chaturbate Archive – Recurbate'
        },
        'skip': 'Free videos are available for a limited amount of time and for a single session.',
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(r'<title>(.+?)</title>', webpage, 'title')
        token = self._html_search_regex(r'data-token=(.+?")', webpage, 'play_button').strip('"')
        get_url = update_url_query('https://recurbate.com/api/get.php', {'video': video_id, 'token': token})
        video_webpage = self._download_webpage(get_url, video_id)
        if 'shall_signin' in video_webpage[:20]:
            raise ExtractorError(
                "Login required: use --cookies to pass your browser's login cookie, or try again later",
                expected=True)
        entries = self._parse_html5_media_entries(get_url, video_webpage, video_id)
        if not entries:
            raise ExtractorError('No media links found')
        return merge_dicts({
            'id': video_id,
            'title': title,
            'description': self._og_search_description(webpage),
        }, entries[0])
