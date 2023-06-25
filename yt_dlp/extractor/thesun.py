import re

from .common import InfoExtractor
from ..utils import extract_attributes


class TheSunIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?the-?sun(\.co\.uk|\.com)/[^/]+/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.thesun.co.uk/tvandshowbiz/2261604/orlando-bloom-and-katy-perry-post-adorable-instagram-video-together-celebrating-thanksgiving-after-split-rumours/',
        'info_dict': {
            'id': '2261604',
            'title': 'md5:cba22f48bad9218b64d5bbe0e16afddf',
        },
        'playlist_count': 2,
    }, {
        'url': 'https://www.the-sun.com/entertainment/7611415/1000lb-sisters-fans-rip-amy-dangerous-health-decision/',
        'info_dict': {
            'id': '7611415',
            'title': 'md5:e0b9b976f79dc770e5c80f22f40bb844',
        },
        'playlist_count': 1,
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/default_default/index.html?videoId=%s'

    def _real_extract(self, url):
        article_id = self._match_id(url)

        webpage = self._download_webpage(url, article_id)

        entries = []
        for video in re.findall(
                r'<video[^>]+data-video-id-pending=[^>]+>',
                webpage):
            attrs = extract_attributes(video)
            video_id = attrs['data-video-id-pending']
            account_id = attrs.get('data-account', '5067014667001')
            entries.append(self.url_result(
                self.BRIGHTCOVE_URL_TEMPLATE % (account_id, video_id),
                'BrightcoveNew', video_id))

        return self.playlist_result(
            entries, article_id, self._og_search_title(webpage, fatal=False))
