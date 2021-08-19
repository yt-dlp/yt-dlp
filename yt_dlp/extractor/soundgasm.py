# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor


class SoundgasmIE(InfoExtractor):
    IE_NAME = 'soundgasm'
    _VALID_URL = r'https?://(?:www\.)?soundgasm\.net/u/(?P<user>[0-9a-zA-Z_-]+)/(?P<display_id>[0-9a-zA-Z_-]+)'
    _TEST = {
        'url': 'http://soundgasm.net/u/ytdl/Piano-sample',
        'md5': '010082a2c802c5275bb00030743e75ad',
        'info_dict': {
            'id': '88abd86ea000cafe98f96321b23cc1206cbcbcc9',
            'ext': 'm4a',
            'title': 'Piano sample',
            'description': 'Royalty Free Sample Music',
            'uploader': 'ytdl',
        }
    }

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        display_id = mobj.group('display_id')

        webpage = self._download_webpage(url, display_id)

        audio_url = self._html_search_regex(
            r'(?s)m4a\s*:\s*(["\'])(?P<url>(?:(?!\1).)+)\1', webpage,
            'audio URL', group='url')

        title = self._search_regex(
            r'<div[^>]+\bclass=["\']jp-title[^>]+>([^<]+)',
            webpage, 'title', default=display_id)

        description = self._html_search_regex(
            (r'(?s)<div[^>]+\bclass=["\']jp-description[^>]+>(.+?)</div>',
             r'(?s)<li>Description:\s(.*?)<\/li>'),
            webpage, 'description', fatal=False)

        audio_id = self._search_regex(
            r'/([^/]+)\.m4a', audio_url, 'audio id', default=display_id)

        return {
            'id': audio_id,
            'display_id': display_id,
            'url': audio_url,
            'vcodec': 'none',
            'title': title,
            'description': description,
            'uploader': mobj.group('user'),
        }


class SoundgasmProfileIE(InfoExtractor):
    IE_NAME = 'soundgasm:profile'
    _VALID_URL = r'https?://(?:www\.)?soundgasm\.net/u/(?P<id>[^/]+)/?(?:\#.*)?$'
    _TEST = {
        'url': 'http://soundgasm.net/u/ytdl',
        'info_dict': {
            'id': 'ytdl',
        },
        'playlist_count': 1,
    }

    def _real_extract(self, url):
        profile_id = self._match_id(url)

        webpage = self._download_webpage(url, profile_id)

        entries = [
            self.url_result(audio_url, 'Soundgasm')
            for audio_url in re.findall(r'href="([^"]+/u/%s/[^"]+)' % profile_id, webpage)]

        return self.playlist_result(entries, profile_id)
