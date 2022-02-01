# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class NFBIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?nfb\.ca/(?:film)/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.nfb.ca/film/trafficopter/',
        "info_dict": {
            "id": "trafficopter",
            'ext': 'mp4',
            "title": "Trafficopter",
            "description": "md5:060228455eb85cf88785c41656776bc0",
            'thumbnail': r're:^https?://.*\.jpg$',
            "uploader": "Barrie Howells",
            "release_date": "1972",
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage('https://www.nfb.ca/film/%s/' % video_id, video_id)

        title = self._html_search_regex(
            r'<[^>]+\bid=["\']titleHeader["\'][^>]*>\s*<h1[^>]*>\s*([^<]+?)\s*</h1>',
            webpage, 'title', default=None)
        director = self._html_search_regex(
            r'<[^>]+\bitemprop=["\']name["\'][^>]*>([^<]+)',
            webpage, 'director', default=None)
        year = self._html_search_regex(
            r'<[^>]+\bitemprop=["\']datePublished["\'][^>]*>([^<]+)',
            webpage, 'year', default=None)
        description = self._html_search_regex(
            r'<[^>]+\bid=["\']tabSynopsis["\'][^>]*>\s*<p[^>]*>\s*([^<]+)',
            webpage, 'description', default=None)
        iframe = self._html_search_regex(
            r'<[^>]+\bid=["\']player-iframe["\'][^>]*src=["\']([^"\']+)',
            webpage, 'iframe', default=None, fatal=True)
        if iframe.startswith("/"):
            iframe = "https://www.nfb.ca" + iframe

        player = self._download_webpage(iframe, video_id)

        source = self._html_search_regex(
            r'source:\s*\'([^\']+)',
            player, 'source', default=None, fatal=True)
        thumbnail = self._html_search_regex(
            r'poster:\s*\'([^\']+)',
            player, 'thumbnail', default=None)

        formats = self._extract_m3u8_formats(source, video_id, ext='mp4')

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'uploader': director,
            'release_date': year,
            'formats': formats,
        }
