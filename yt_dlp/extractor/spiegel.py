from .common import InfoExtractor
from .jwplatform import JWPlatformIE


class SpiegelIE(InfoExtractor):
    _UUID_RE = r'[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}'
    _VALID_URL = r'https?://(?:www\.)?(?:spiegel|manager-magazin)\.de(?:/[^/]+)+/[^/]*-(?P<id>[0-9]+|%s)(?:-embed|-iframe)?(?:\.html)?(?:$|[#?])' % _UUID_RE
    _TESTS = [{
        'url': 'http://www.spiegel.de/video/vulkan-tungurahua-in-ecuador-ist-wieder-aktiv-video-1259285.html',
        'md5': '50c7948883ec85a3e431a0a44b7ad1d6',
        'info_dict': {
            'id': 'II0BUyxY',
            'display_id': '1259285',
            'ext': 'mp4',
            'title': 'Vulkan Tungurahua in Ecuador ist wieder aktiv - DER SPIEGEL - Wissenschaft',
            'description': 'md5:8029d8310232196eb235d27575a8b9f4',
            'duration': 48.0,
            'upload_date': '20130311',
            'timestamp': 1362997920,
        },
    }, {
        'url': 'http://www.spiegel.de/video/schach-wm-videoanalyse-des-fuenften-spiels-video-1309159.html',
        'only_matching': True,
    }, {
        'url': 'https://www.spiegel.de/video/eifel-zoo-aufregung-um-ausgebrochene-raubtiere-video-99018031.html',
        'only_matching': True,
    }, {
        'url': 'https://www.spiegel.de/panorama/urteile-im-goldmuenzenprozess-haftstrafen-fuer-clanmitglieder-a-aae8df48-43c1-4c61-867d-23f0a2d254b7',
        'only_matching': True,
    }, {
        'url': 'http://www.spiegel.de/video/spiegel-tv-magazin-ueber-guellekrise-in-schleswig-holstein-video-99012776.html',
        'only_matching': True,
    }, {
        'url': 'http://www.spiegel.de/sport/sonst/badminton-wm-die-randsportart-soll-populaerer-werden-a-987092.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        media_id = self._html_search_regex(
            r'(&#34;|["\'])mediaId\1\s*:\s*(&#34;|["\'])(?P<id>(?:(?!\2).)+)\2',
            webpage, 'media id', group='id')
        return {
            '_type': 'url_transparent',
            'id': video_id,
            'display_id': video_id,
            'url': 'jwplatform:%s' % media_id,
            'title': self._og_search_title(webpage, default=None),
            'ie_key': JWPlatformIE.ie_key(),
        }
