from .common import InfoExtractor
from .arkena import ArkenaIE


class LcpPlayIE(ArkenaIE):  # XXX: Do not subclass from concrete IE
    _VALID_URL = r'https?://play\.lcp\.fr/embed/(?P<id>[^/]+)/(?P<account_id>[^/]+)/[^/]+/[^/]+'
    _TESTS = [{
        'url': 'http://play.lcp.fr/embed/327336/131064/darkmatter/0',
        'md5': 'b8bd9298542929c06c1c15788b1f277a',
        'info_dict': {
            'id': '327336',
            'ext': 'mp4',
            'title': '327336',
            'timestamp': 1456391602,
            'upload_date': '20160225',
        },
        'params': {
            'skip_download': True,
        },
    }]


class LcpIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?lcp\.fr/(?:[^/]+/)*(?P<id>[^/]+)'

    _TESTS = [{
        # arkena embed
        'url': 'http://www.lcp.fr/la-politique-en-video/schwartzenberg-prg-preconise-francois-hollande-de-participer-une-primaire',
        'md5': 'b8bd9298542929c06c1c15788b1f277a',
        'info_dict': {
            'id': 'd56d03e9',
            'ext': 'mp4',
            'title': 'Schwartzenberg (PRG) préconise à François Hollande de participer à une primaire à gauche',
            'description': 'md5:96ad55009548da9dea19f4120c6c16a8',
            'timestamp': 1456488895,
            'upload_date': '20160226',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # dailymotion live stream
        'url': 'http://www.lcp.fr/le-direct',
        'info_dict': {
            'id': 'xji3qy',
            'ext': 'mp4',
            'title': 'La Chaine Parlementaire (LCP), Live TNT',
            'description': 'md5:5c69593f2de0f38bd9a949f2c95e870b',
            'uploader': 'LCP',
            'uploader_id': 'xbz33d',
            'timestamp': 1308923058,
            'upload_date': '20110624',
        },
        'params': {
            # m3u8 live stream
            'skip_download': True,
        },
    }, {
        'url': 'http://www.lcp.fr/emissions/277792-les-volontaires',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        play_url = self._search_regex(
            r'<iframe[^>]+src=(["\'])(?P<url>%s?(?:(?!\1).)*)\1' % LcpPlayIE._VALID_URL,
            webpage, 'play iframe', default=None, group='url')

        if not play_url:
            return self.url_result(url, 'Generic')

        title = self._og_search_title(webpage, default=None) or self._html_search_meta(
            'twitter:title', webpage, fatal=True)
        description = self._html_search_meta(
            ('description', 'twitter:description'), webpage)

        return {
            '_type': 'url_transparent',
            'ie_key': LcpPlayIE.ie_key(),
            'url': play_url,
            'display_id': display_id,
            'title': title,
            'description': description,
        }
