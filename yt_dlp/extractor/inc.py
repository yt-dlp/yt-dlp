from .common import InfoExtractor
from .kaltura import KalturaIE


class IncIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?inc\.com/(?:[^/]+/)+(?P<id>[^.]+).html'
    _TESTS = [{
        'url': 'http://www.inc.com/tip-sheet/bill-gates-says-these-5-books-will-make-you-smarter.html',
        'md5': '7416739c9c16438c09fa35619d6ba5cb',
        'info_dict': {
            'id': '1_wqig47aq',
            'ext': 'mov',
            'title': 'Bill Gates Says These 5 Books Will Make You Smarter',
            'description': 'md5:bea7ff6cce100886fc1995acb743237e',
            'timestamp': 1474414430,
            'upload_date': '20160920',
            'uploader_id': 'video@inc.com',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # div with id=kaltura_player_1_kqs38cgm
        'url': 'https://www.inc.com/oscar-raymundo/richard-branson-young-entrepeneurs.html',
        'info_dict': {
            'id': '1_kqs38cgm',
            'ext': 'mp4',
            'title': 'Branson: "In the end, you have to say, Screw it. Just do it."',
            'description': 'md5:21b832d034f9af5191ca5959da5e9cb6',
            'timestamp': 1364403232,
            'upload_date': '20130327',
            'uploader_id': 'incdigital@inc.com',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.inc.com/video/david-whitford/founders-forum-tripadvisor-steve-kaufer-most-enjoyable-moment-for-entrepreneur.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        partner_id = self._search_regex(
            r'var\s+_?bizo_data_partner_id\s*=\s*["\'](\d+)', webpage,
            'partner id', default='1034971')

        kaltura_id = self._search_regex(
            r'id=(["\'])kaltura_player_(?P<id>.+?)\1', webpage, 'kaltura id',
            default=None, group='id') or self._parse_json(self._search_regex(
                r'pageInfo\.videos\s*=\s*\[(.+)\];', webpage, 'kaltura id'),
            display_id)['vid_kaltura_id']

        return self.url_result(
            'kaltura:%s:%s' % (partner_id, kaltura_id), KalturaIE.ie_key())
