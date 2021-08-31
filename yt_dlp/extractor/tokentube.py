# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    parse_count,
    unified_strdate,
    js_to_json,
)


class TokentubeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tokentube\.net/(l|v)/(?P<id>\d+)/.*'
    _TESTS = [{
        'url': 'https://tokentube.net/l/3236632011/Praise-A-Thon-Pastori-Chrisin-ja-Pastori-Bennyn-kanssa-27-8-2021',
        'info_dict': {
            'id': '3236632011',
            'ext': 'mp4',
            'title': 'Praise-A-Thon Pastori Chrisin ja Pastori Bennyn kanssa 27.8.2021',
            'description': '',
            'uploader': 'Pastori Chris - Rapsodia.fi',
            'upload_date': '20210827',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://tokentube.net/v/3950239124/Linux-Ubuntu-Studio-perus-k%C3%A4ytt%C3%B6',
        'md5': '0e1f00421f501f5eada9890d38fcfb56',
        'info_dict': {
            'id': '3950239124',
            'ext': 'mp4',
            'title': 'Linux Ubuntu Studio perus käyttö',
            'description': 'md5:854ff1dc732ff708976de2880ea32050',
            'uploader': 'jyrilehtonen',
            'upload_date': '20210825',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        formats = []

        title = self._html_search_regex(r'<h1\s*class=["\']title-text["\']>(.+?)</h1>', webpage, 'title')

        data_json = self._html_search_regex(r'({["\']html5["\'].+?}}}+)', webpage, 'data json')
        data_json = self._parse_json(js_to_json(data_json), video_id, fatal=False)

        sources = data_json.get('sources')
        if not sources:
            sources = self._html_search_regex(r'updateSrc\(([^\)]+)\)', webpage, 'sources')
            sources = self._parse_json(js_to_json(sources), video_id)

        for format in sources:
            formats.append({
                'url': format.get('src'),
                'format_id': format.get('label'),
                'height': format.get('res'),
            })

        view_count = parse_count(self._html_search_regex(
            r'<p\s*class=["\']views_counter["\']>\s*([\d\.,]+)\s*<span>views</span></p>',
            webpage, 'view_count', fatal=False))

        like_count = parse_count(self._html_search_regex(
            r'<div\s*class="sh_button\s*likes_count">\s*(\d+)\s*</div>',
            webpage, 'like count', fatal=False))

        dislike_count = parse_count(self._html_search_regex(
            r'<div\s*class="sh_button\s*dislikes_count">\s*(\d+)\s*</div>',
            webpage, 'dislike count', fatal=False))

        upload_date = unified_strdate(self._html_search_regex(
            r'<span\s*class="p-date">Published\s*on\s+([^<]+)',
            webpage, 'upload date', fatal=False))

        uploader = self._html_search_regex(
            r'<a\s*class="place-left"[^>]+>(.+?)</a>',
            webpage, 'uploader', fatal=False)

        description = self._html_search_meta('description', webpage)

        self._sort_formats(formats)

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'view_count': view_count,
            'like_count': like_count,
            'dislike_count': dislike_count,
            'upload_date': upload_date,
            'description': description,
            'uploader': uploader,
        }


class TokentubeChannelIE(InfoExtractor):
    IE_NAME = 'Tokentube:channel'
    _VALID_URL = r'https?://(?:www\.)?tokentube\.net/channel/(?P<id>\d+)/(?P<name>[^/]+)(?:/videos)?'
    _TESTS = [{
        'url': 'https://tokentube.net/channel/3697658904/TokenTube',
        'info_dict': {
            'id': '3697658904',
            'title': 'Ylläpito',
        },
        'playlist_mincount': 7,
    }, {
        'url': 'https://tokentube.net/channel/3353234420/Linux/videos',
        'info_dict': {
            'id': '3353234420',
            'title': 'Linux',
        },
        'playlist_mincount': 20,
    }]

    def _real_extract(self, url):
        channel_id, channel_name = self._match_valid_url(url).groups()

        webpage = self._download_webpage(
            f'https://tokentube.net/channel/{channel_id}/{channel_name}/videos', channel_id)

        title = self._html_search_regex(
            r'<h1>([^>]+)</h1>', webpage, 'title', default=None)

        if '<button class="more-button"' in webpage:
            videos = self._download_webpage(
                f'https://tokentube.net/videos?p=0&m=1&sort=recent&u={channel_id}&page=2',
                channel_id, headers={'X-Requested-With': 'XMLHttpRequest'}, note='Fetching more videos', fatal=False)
            webpage += videos if videos else ''

        entries = []
        for path, media_id in re.findall(
                r'<a[^>]+\bhref=["\']([^"\']+/[lv]/(\d+)/\S+)["\'][^>]+>',
                webpage):
            entries.append(
                self.url_result(path, ie=TokentubeIE.ie_key(), video_id=media_id))

        return self.playlist_result(entries, channel_id, title)
