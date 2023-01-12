from .common import InfoExtractor
from .fox import FOXIE
from ..utils import (
    smuggle_url,
    url_basename,
)


class NationalGeographicVideoIE(InfoExtractor):
    IE_NAME = 'natgeo:video'
    _VALID_URL = r'https?://video\.nationalgeographic\.com/.*?'

    _TESTS = [
        {
            'url': 'http://video.nationalgeographic.com/video/news/150210-news-crab-mating-vin?source=featuredvideo',
            'md5': '730855d559abbad6b42c2be1fa584917',
            'info_dict': {
                'id': '0000014b-70a1-dd8c-af7f-f7b559330001',
                'ext': 'mp4',
                'title': 'Mating Crabs Busted by Sharks',
                'description': 'md5:16f25aeffdeba55aaa8ec37e093ad8b3',
                'timestamp': 1423523799,
                'upload_date': '20150209',
                'uploader': 'NAGS',
            },
            'add_ie': ['ThePlatform'],
        },
        {
            'url': 'http://video.nationalgeographic.com/wild/when-sharks-attack/the-real-jaws',
            'md5': '6a3105eb448c070503b3105fb9b320b5',
            'info_dict': {
                'id': 'ngc-I0IauNSWznb_UV008GxSbwY35BZvgi2e',
                'ext': 'mp4',
                'title': 'The Real Jaws',
                'description': 'md5:8d3e09d9d53a85cd397b4b21b2c77be6',
                'timestamp': 1433772632,
                'upload_date': '20150608',
                'uploader': 'NAGS',
            },
            'add_ie': ['ThePlatform'],
        },
    ]

    def _real_extract(self, url):
        name = url_basename(url)

        webpage = self._download_webpage(url, name)
        guid = self._search_regex(
            r'id="(?:videoPlayer|player-container)"[^>]+data-guid="([^"]+)"',
            webpage, 'guid')

        return {
            '_type': 'url_transparent',
            'ie_key': 'ThePlatform',
            'url': smuggle_url(
                'http://link.theplatform.com/s/ngs/media/guid/2423130747/%s?mbr=true' % guid,
                {'force_smil_url': True}),
            'id': guid,
        }


class NationalGeographicTVIE(FOXIE):  # XXX: Do not subclass from concrete IE
    _VALID_URL = r'https?://(?:www\.)?nationalgeographic\.com/tv/watch/(?P<id>[\da-fA-F]+)'
    _TESTS = [{
        'url': 'https://www.nationalgeographic.com/tv/watch/6a875e6e734b479beda26438c9f21138/',
        'info_dict': {
            'id': '6a875e6e734b479beda26438c9f21138',
            'ext': 'mp4',
            'title': 'Why Nat Geo? Valley of the Boom',
            'description': 'The lives of prominent figures in the tech world, including their friendships, rivalries, victories and failures.',
            'timestamp': 1542662458,
            'upload_date': '20181119',
            'age_limit': 14,
        },
        'params': {
            'skip_download': True,
        },
    }]
    _HOME_PAGE_URL = 'https://www.nationalgeographic.com/tv/'
    _API_KEY = '238bb0a0c2aba67922c48709ce0c06fd'
