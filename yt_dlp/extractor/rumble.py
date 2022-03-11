# coding: utf-8
from __future__ import unicode_literals

import itertools
import re

from .common import InfoExtractor
from ..compat import compat_str, compat_HTTPError
from ..utils import (
    determine_ext,
    int_or_none,
    parse_iso8601,
    try_get,
    ExtractorError,
)


class RumbleEmbedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rumble\.com/embed/(?:[0-9a-z]+\.)?(?P<id>[0-9a-z]+)'
    _TESTS = [{
        'url': 'https://rumble.com/embed/v5pv5f',
        'md5': '36a18a049856720189f30977ccbb2c34',
        'info_dict': {
            'id': 'v5pv5f',
            'ext': 'mp4',
            'title': 'WMAR 2 News Latest Headlines | October 20, 6pm',
            'timestamp': 1571611968,
            'upload_date': '20191020',
            'channel': 'WMAR',
            'channel_url': 'https://rumble.com/c/WMAR',
            'duration': 234,
            'thumbnail': 'https://sp.rmbl.ws/s8/1/5/M/z/1/5Mz1a.OvCc-small-WMAR-2-News-Latest-Headline.jpg',
            'description': 'md5:6c791446ac12dea994674d3976a3cdd5',
            'view_count': int,
        }
    }, {
        'url': 'https://rumble.com/embed/ufe9n.v5pv5f',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_urls(webpage):
        return [
            mobj.group('url')
            for mobj in re.finditer(
                r'(?:<(?:script|iframe)[^>]+\bsrc=|["\']embedUrl["\']\s*:\s*)["\'](?P<url>%s)' % RumbleEmbedIE._VALID_URL,
                webpage)]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video = self._download_json(
            'https://rumble.com/embedJS/', video_id,
            query={'request': 'video', 'v': video_id})
        title = video['title']

        embed_page = self._download_webpage(url, video_id, note='Downloading embed page')
        canonical_url = self._search_regex(
            r'<link\s+rel="canonical"\s*href="(.+?)"', embed_page, 'canonical URL',
            default=url)
        webpage = self._download_webpage(canonical_url, video_id)
        description = self._html_search_regex(
            r'media-description">([^<]+)<', webpage, 'description', default=None, fatal=False)
        view_count = self._html_search_regex(
            r'media-heading-info">([0-9,]+) Views<', webpage, 'view_count', default=None, fatal=False)
        if view_count:
            view_count = int_or_none(view_count.replace(',', ''))

        formats = []
        for height, ua in (video.get('ua') or {}).items():
            for i in range(2):
                f_url = try_get(ua, lambda x: x[i], compat_str)
                if f_url:
                    ext = determine_ext(f_url)
                    f = {
                        'ext': ext,
                        'format_id': '%s-%sp' % (ext, height),
                        'height': int_or_none(height),
                        'url': f_url,
                    }
                    bitrate = try_get(ua, lambda x: x[i + 2]['bitrate'])
                    if bitrate:
                        f['tbr'] = int_or_none(bitrate)
                    formats.append(f)
        self._sort_formats(formats)

        author = video.get('author') or {}

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': video.get('i'),
            'timestamp': parse_iso8601(video.get('pubDate')),
            'channel': author.get('name'),
            'channel_url': author.get('url'),
            'duration': int_or_none(video.get('duration')),
            'description': description,
            'view_count': view_count,
        }


class RumbleChannelIE(InfoExtractor):
    _VALID_URL = r'(?P<url>https?://(?:www\.)?rumble\.com/(?:c|user)/(?P<id>[^&?#$/]+))'

    _TESTS = [{
        'url': 'https://rumble.com/c/Styxhexenhammer666',
        'playlist_mincount': 1160,
        'info_dict': {
            'id': 'Styxhexenhammer666',
        },
    }, {
        'url': 'https://rumble.com/user/goldenpoodleharleyeuna',
        'playlist_count': 4,
        'info_dict': {
            'id': 'goldenpoodleharleyeuna',
        },
    }]

    def entries(self, url, playlist_id):
        for page in itertools.count(1):
            try:
                webpage = self._download_webpage(f'{url}?page={page}', playlist_id, note='Downloading page %d' % page)
            except ExtractorError as e:
                if isinstance(e.cause, compat_HTTPError) and e.cause.code == 404:
                    break
                raise
            for video_url in re.findall(r'class=video-item--a\s?href=([^>]+\.html)', webpage):
                yield self.url_result('https://rumble.com' + video_url)

    def _real_extract(self, url):
        url, playlist_id = self._match_valid_url(url).groups()
        return self.playlist_result(self.entries(url, playlist_id), playlist_id=playlist_id)
