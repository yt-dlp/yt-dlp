from .art19 import Art19IE
from .common import InfoExtractor
from ..utils import extract_attributes, get_elements_html_by_class
from ..utils.traversal import traverse_obj


class RideHomeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ridehome\.info/show/[\w-]+/(?P<id>[\w-]+)/?(?:$|[?#])'
    _TESTS = [{
        'url': 'https://www.ridehome.info/show/techmeme-ride-home/thu-1228-will-2024-be-the-year-apple-gets-serious-about-gaming-on-macs/',
        'info_dict': {
            'id': 'thu-1228-will-2024-be-the-year-apple-gets-serious-about-gaming-on-macs',
        },
        'playlist_count': 1,
        'playlist': [{
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
                'thumbnail': r're:^https?://content\.production\.cdn\.art19\.com/images/.*\.jpeg$',
            },
        }],
    }, {
        'url': 'https://www.ridehome.info/show/techmeme-ride-home/portfolio-profile-sensel-with-ilyarosenberg/',
        'info_dict': {
            'id': 'portfolio-profile-sensel-with-ilyarosenberg',
        },
        'playlist_count': 1,
        'playlist': [{
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
            },
        }],
    }, {
        'url': 'https://www.ridehome.info/show/spacecasts/big-tech-news-apples-macbook-pro-event/',
        'info_dict': {
            'id': 'big-tech-news-apples-macbook-pro-event',
        },
        'playlist_count': 1,
        'playlist': [{
            'md5': 'b1428530c6e03904a8271e978007fc05',
            'info_dict': {
                'id': 'f4780044-6c4b-4ce0-8215-8a86cc66bff7',
                'ext': 'mp3',
                'title': 'md5:e6c05d44d59b6577a4145ac339de5040',
                'description': 'md5:14152f7228c8a301a77e3d6bc891b145',
                'series': 'SpaceCasts',
                'series_id': '8e3e837d-7fe0-4a23-8e11-894917e07e17',
                'upload_date': '20211026',
                'timestamp': 1635271450,
                'modified_date': '20230502',
                'episode_id': 'f4780044-6c4b-4ce0-8215-8a86cc66bff7',
                'modified_timestamp': 1683057500,
                'release_date': '20211026',
                'release_timestamp': 1635272124,
                'duration': 2266.30531,
                'thumbnail': r're:^https?://content\.production\.cdn\.art19\.com/images/.*\.jpeg$'
            },
        }],
    }]

    def _real_extract(self, url):
        article_id = self._match_id(url)
        webpage = self._download_webpage(url, article_id)

        urls = traverse_obj(
            get_elements_html_by_class('iframeContainer', webpage),
            (..., {extract_attributes}, lambda k, v: k == 'data-src' and Art19IE.suitable(v)))
        return self.playlist_from_matches(urls, article_id, ie=Art19IE)
