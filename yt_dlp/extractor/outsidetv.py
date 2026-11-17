from .common import InfoExtractor


class OutsideTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?outsidetv\.com/(?:[^/]+/)*?play/[a-zA-Z0-9]{8}/\d+/\d+/(?P<id>[a-zA-Z0-9]{8})'
    _TESTS = [{
        'url': 'http://www.outsidetv.com/category/snow/play/ZjQYboH6/1/10/Hdg0jukV/4',
        'md5': '192d968fedc10b2f70ec31865ffba0da',
        'info_dict': {
            'id': 'Hdg0jukV',
            'ext': 'mp4',
            'title': 'Home - Jackson Ep 1 | Arbor Snowboards',
            'description': 'md5:41a12e94f3db3ca253b04bb1e8d8f4cd',
            'upload_date': '20181225',
            'timestamp': 1545742800,
        },
    }, {
        'url': 'http://www.outsidetv.com/home/play/ZjQYboH6/1/10/Hdg0jukV/4',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        jw_media_id = self._match_id(url)
        return self.url_result(
            'jwplatform:' + jw_media_id, 'JWPlatform', jw_media_id)
