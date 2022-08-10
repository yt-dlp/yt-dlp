from .common import InfoExtractor
from ..utils import (
    int_or_none,
    url_or_none,
    strip_or_none,
    str_to_int,
)

class InflateVidsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tube.inflatevids\.xyz/watch/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://tube.inflatevids.xyz/watch/8zdGbHUiIsi6hLg',
        'info_dict': {
            'id': '8zdGbHUiIsi6hLg',
            'ext': 'mp4',
            'title': 'Inside a double layered pvc Eevee pooltoy suit',
            'thumbnail': r're:^https?://.*\.(jpg|jpeg)',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        
        return {
            'id': video_id,
            'tags': self._html_search_meta('keywords', webpage, default=None),

            'title': self._html_search_meta(['og:title', 'twitter:title', 'title'],
                webpage, 'title', default=None),

            # TODO: Strip out newlines and other escape sequences.
            'description': self._html_search_regex(r'<div[^>]+itemprop=\"description\"[^>]*>(.*)',
                webpage, 'description', default=None),
            
            'view_count': int_or_none(
                self._html_search_regex(r'<span[^>]+video-views-count[^>]*>([^<]+)<',
                    webpage, 'view_count'),
            ),

            'like_count':int_or_none(
                self._html_search_regex(r'<div[^<]+data-likes[^>]\"([^<]*)\"',
                    webpage, 'like_count')),
            
            'url': url_or_none(
                self._html_search_meta('og:video', webpage)
                or self._html_search_regex(r'<div[^>]+contentUrl[^>]*>([^<]+)<'),
            ),

            # TODO: This is broken! Convert the date to what Python can parse.
            #'upload_date': self._html_search_regex(r'<div[^>]+uploadDate[^>]*>([^<]+)<',
            #    webpage, 'upload_date', default=None),
            
            'thumbnail': self._html_search_meta(
                ['og:image', 'twitter:image', 'thumbnail'],
                webpage, 'thumbnail', default=None),

            'uploader': strip_or_none(
                self._html_search_regex(r'(?:<div[^>]+?publisher-name[^>]*>)[^<]*(?:<a href[^>]+id=)([^>\"]+)',
                webpage, 'uploader'),
            ),
        }
