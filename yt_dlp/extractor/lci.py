from .common import InfoExtractor


class LCIIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:lci|tf1info)\.fr/[^/]+/[\w-]+-(?P<id>\d+)\.html'
    _TESTS = [{
        'url': 'https://www.tf1info.fr/politique/election-presidentielle-2022-second-tour-j-2-marine-le-pen-et-emmanuel-macron-en-interview-de-lci-vendredi-soir-2217486.html',
        'info_dict': {
            'id': '13875948',
            'ext': 'mp4',
            'title': 'md5:660df5481fd418bc3bbb0d070e6fdb5a',
            'thumbnail': 'https://photos.tf1.fr/1280/720/presidentielle-2022-marine-le-pen-et-emmanuel-macron-invites-de-lci-ce-vendredi-9c0e73-e1a036-0@1x.jpg',
            'upload_date': '20220422',
            'duration': 33,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.lci.fr/politique/election-presidentielle-2022-second-tour-j-2-marine-le-pen-et-emmanuel-macron-en-interview-de-lci-vendredi-soir-2217486.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        wat_id = self._search_regex(r'watId["\']?\s*:\s*["\']?(\d+)', webpage, 'wat id')
        return self.url_result('wat:' + wat_id, 'Wat', wat_id)
