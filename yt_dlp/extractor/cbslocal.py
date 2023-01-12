from .anvato import AnvatoIE
from .sendtonews import SendtoNewsIE
from ..compat import compat_urlparse
from ..utils import (
    parse_iso8601,
    unified_timestamp,
)


class CBSLocalIE(AnvatoIE):  # XXX: Do not subclass from concrete IE
    _VALID_URL_BASE = r'https?://[a-z]+\.cbslocal\.com/'
    _VALID_URL = _VALID_URL_BASE + r'video/(?P<id>\d+)'

    _TESTS = [{
        'url': 'http://newyork.cbslocal.com/video/3580809-a-very-blue-anniversary/',
        'info_dict': {
            'id': '3580809',
            'ext': 'mp4',
            'title': 'A Very Blue Anniversary',
            'description': 'CBS2’s Cindy Hsu has more.',
            'thumbnail': 're:^https?://.*',
            'timestamp': int,
            'upload_date': r're:^\d{8}$',
            'uploader': 'CBS',
            'subtitles': {
                'en': 'mincount:5',
            },
            'categories': [
                'Stations\\Spoken Word\\WCBSTV',
                'Syndication\\AOL',
                'Syndication\\MSN',
                'Syndication\\NDN',
                'Syndication\\Yahoo',
                'Content\\News',
                'Content\\News\\Local News',
            ],
            'tags': ['CBS 2 News Weekends', 'Cindy Hsu', 'Blue Man Group'],
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        mcp_id = self._match_id(url)
        return self.url_result(
            'anvato:anvato_cbslocal_app_web_prod_547f3e49241ef0e5d30c79b2efbca5d92c698f67:' + mcp_id, 'Anvato', mcp_id)


class CBSLocalArticleIE(AnvatoIE):  # XXX: Do not subclass from concrete IE
    _VALID_URL = CBSLocalIE._VALID_URL_BASE + r'\d+/\d+/\d+/(?P<id>[0-9a-z-]+)'

    _TESTS = [{
        # Anvato backend
        'url': 'http://losangeles.cbslocal.com/2016/05/16/safety-advocates-say-fatal-car-seat-failures-are-public-health-crisis',
        'md5': 'f0ee3081e3843f575fccef901199b212',
        'info_dict': {
            'id': '3401037',
            'ext': 'mp4',
            'title': 'Safety Advocates Say Fatal Car Seat Failures Are \'Public Health Crisis\'',
            'description': 'Collapsing seats have been the focus of scrutiny for decades, though experts say remarkably little has been done to address the issue. Randy Paige reports.',
            'thumbnail': 're:^https?://.*',
            'timestamp': 1463440500,
            'upload_date': '20160516',
            'uploader': 'CBS',
            'subtitles': {
                'en': 'mincount:5',
            },
            'categories': [
                'Stations\\Spoken Word\\KCBSTV',
                'Syndication\\MSN',
                'Syndication\\NDN',
                'Syndication\\AOL',
                'Syndication\\Yahoo',
                'Syndication\\Tribune',
                'Syndication\\Curb.tv',
                'Content\\News'
            ],
            'tags': ['CBS 2 News Evening'],
        },
    }, {
        # SendtoNews embed
        'url': 'http://cleveland.cbslocal.com/2016/05/16/indians-score-season-high-15-runs-in-blowout-win-over-reds-rapid-reaction/',
        'info_dict': {
            'id': 'GxfCe0Zo7D-175909-5588',
        },
        'playlist_count': 9,
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        sendtonews_url = SendtoNewsIE._extract_url(webpage)
        if sendtonews_url:
            return self.url_result(
                compat_urlparse.urljoin(url, sendtonews_url),
                ie=SendtoNewsIE.ie_key())

        info_dict = self._extract_anvato_videos(webpage, display_id)

        timestamp = unified_timestamp(self._html_search_regex(
            r'class="(?:entry|post)-date"[^>]*>([^<]+)', webpage,
            'released date', default=None)) or parse_iso8601(
            self._html_search_meta('uploadDate', webpage))

        info_dict.update({
            'display_id': display_id,
            'timestamp': timestamp,
        })

        return info_dict
