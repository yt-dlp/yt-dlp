import re

from .common import InfoExtractor


class AtScaleConfEventIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?atscaleconference\.com/events/(?P<id>[^/&$?]+)'

    _TESTS = [{
        'url': 'https://atscaleconference.com/events/data-scale-spring-2022/',
        'playlist_mincount': 13,
        'info_dict': {
            'id': 'data-scale-spring-2022',
            'title': 'Data @Scale Spring 2022',
            'description': 'md5:7d7ca1c42ac9c6d8a785092a1aea4b55'
        },
    }, {
        'url': 'https://atscaleconference.com/events/video-scale-2021/',
        'playlist_mincount': 14,
        'info_dict': {
            'id': 'video-scale-2021',
            'title': 'Video @Scale 2021',
            'description': 'md5:7d7ca1c42ac9c6d8a785092a1aea4b55'
        },
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        webpage = self._download_webpage(url, id)

        return self.playlist_from_matches(
            re.findall(r'data-url\s*=\s*"(https?://(?:www\.)?atscaleconference\.com/videos/[^"]+)"', webpage),
            ie='Generic', playlist_id=id,
            title=self._og_search_title(webpage), description=self._og_search_description(webpage))
