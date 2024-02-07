from .common import InfoExtractor
from .art19 import Art19IE

from ..utils import (
    ExtractorError,
    extract_attributes,
    get_elements_html_by_class,
    traverse_obj,
)


class RideHomeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ridehome\.info/show/techmeme-ride-home/(?P<id>[\w-]+)(?:/|$)'
    _TESTS = [{
        'url': 'https://www.ridehome.info/show/techmeme-ride-home/thu-1228-will-2024-be-the-year-apple-gets-serious-about-gaming-on-macs/',
        'md5': 'c84ea3cc96950a9ab86fe540f3edc588',
        'info_dict': {
            'id': '540e5493-9fe6-4c14-a488-dc508d8794b2',
            'ext': 'mp3',
            'title': 'Thu. 12/28 – Will 2024 Be The Year Apple Gets Serious About Gaming On Macs?',
            'description': 'md5:9dba86ae9b5047a8150eceddeeb629c2',
            'series': 'Techmeme Ride Home',
            'series_id': '3c30e8f4-ab48-415b-9421-1ae06cd4058b',
            'upload_date': '20231228',
            'timestamp': 1703780995,
            'modified_date': '20231230',
            'episode_id': '540e5493-9fe6-4c14-a488-dc508d8794b2',
            'modified_timestamp': 1703912404,
            'release_date': '20231228',
            'release_timestamp': 1703782800,
            'duration': 1000.1502,
            'thumbnail': r're:^https?://content\.production\.cdn\.art19\.com/images/.*\.jpeg$'
        }
    }, {
        'url': 'https://www.ridehome.info/show/techmeme-ride-home/portfolio-profile-sensel-with-ilyarosenberg/',
        'md5': 'bf9d6efad221008ce71aea09d5533cf6',
        'info_dict': {
            'id': '6beed803-b1ef-4536-9fef-c23cf6b4dcac',
            'ext': 'mp3',
            'title': '(Portfolio Profile) Sensel - With @IlyaRosenberg',
            'description': 'md5:e1e4a970bce04290e0ba6f030b0125db',
            'series': 'Techmeme Ride Home',
            'series_id': '3c30e8f4-ab48-415b-9421-1ae06cd4058b',
            'upload_date': '20220108',
            'timestamp': 1641656064,
            'modified_date': '20230418',
            'episode_id': '6beed803-b1ef-4536-9fef-c23cf6b4dcac',
            'modified_timestamp': 1681843318,
            'release_date': '20220108',
            'release_timestamp': 1641672000,
            'duration': 2789.38122,
            'thumbnail': r're:^https?://content\.production\.cdn\.art19\.com/images/.*\.jpeg$'
        }
    }]

    def _entries(self, containers):
        for container in containers:
            yield self.url_result(container, Art19IE)

    def _real_extract(self, url):
        article_id = self._match_id(url)
        webpage = self._download_webpage(url, article_id)

        containers = traverse_obj(
            get_elements_html_by_class(
                'iframeContainer', webpage), (..., {extract_attributes}, 'data-src'))
        if not containers:
            raise ExtractorError('Unable to extract any media containers from webpage')

        # couldn't find an example with multiple containers. This is just a safeguard.
        if len(containers) > 1:
            return self.playlist_result(self._entries(containers), article_id)

        return self.url_result(containers[0], Art19IE)
