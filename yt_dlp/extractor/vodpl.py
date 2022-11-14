from .onet import OnetBaseIE


class VODPlIE(OnetBaseIE):
    _VALID_URL = r'https?://vod\.pl/(?:[^/]+/)+(?P<id>[0-9a-zA-Z]+)'

    _TESTS = [{
        'url': 'https://vod.pl/filmy/chlopaki-nie-placza/3ep3jns',
        'md5': 'a7dc3b2f7faa2421aefb0ecaabf7ec74',
        'info_dict': {
            'id': '3ep3jns',
            'ext': 'mp4',
            'title': 'Chłopaki nie płaczą',
            'description': 'md5:f5f03b84712e55f5ac9f0a3f94445224',
            'timestamp': 1463415154,
            'duration': 5765,
            'upload_date': '20160516',
        },
    }, {
        'url': 'https://vod.pl/seriale/belfer-na-planie-praca-kamery-online/2c10heh',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        info_dict = self._extract_from_id(self._search_mvp_id(webpage), webpage)
        info_dict['id'] = video_id
        return info_dict
