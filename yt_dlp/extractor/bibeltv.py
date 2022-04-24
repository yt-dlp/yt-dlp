from .common import InfoExtractor


class BibelTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?bibeltv\.de/mediathek/videos/(?:crn/)?(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.bibeltv.de/mediathek/videos/329703-sprachkurs-in-malaiisch',
        'md5': '252f908192d611de038b8504b08bf97f',
        'info_dict': {
            'id': 'ref:329703',
            'ext': 'mp4',
            'title': 'Sprachkurs in Malaiisch',
            'description': 'md5:3e9f197d29ee164714e67351cf737dfe',
            'timestamp': 1608316701,
            'uploader_id': '5840105145001',
            'upload_date': '20201218',
        }
    }, {
        'url': 'https://www.bibeltv.de/mediathek/videos/crn/326374',
        'only_matching': True,
    }]
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/5840105145001/default_default/index.html?videoId=ref:%s'

    def _real_extract(self, url):
        crn_id = self._match_id(url)
        return self.url_result(
            self.BRIGHTCOVE_URL_TEMPLATE % crn_id, 'BrightcoveNew')
