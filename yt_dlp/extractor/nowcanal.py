from .brightcove import BrightcoveNewIE
from .common import InfoExtractor


class NowCanalIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?nowcanal\.pt(?:/[\w-]+)+/detalhe/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.nowcanal.pt/ultimas/detalhe/pedro-sousa-hjulmand-pode-ter-uma-saida-limpa-do-sporting-daqui-a-um-ano',
        'md5': '047f17cb783e66e467d703e704bbc95d',
        'info_dict': {
            'id': '6376598467112',
            'ext': 'mp4',
            'title': 'Pedro Sousa «Hjulmand pode ter uma saída limpa do Sporting daqui a um ano»',
            'description': '',
            'uploader_id': '6108484330001',
            'duration': 65.237,
            'thumbnail': r're:^https://.+\.jpg',
            'timestamp': 1754440620,
            'upload_date': '20250806',
            'tags': ['now'],
        },
    }, {
        'url': 'https://www.nowcanal.pt/programas/frente-a-frente/detalhe/frente-a-frente-eva-cruzeiro-ps-e-rita-matias-chega',
        'only_matching': True,
    }]

    _BC_URL_TMPL = 'https://players.brightcove.net/6108484330001/chhIqzukMq_default/index.html?videoId={}'

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        video_id = self._search_json(
            r'videoHandler\.addBrightcoveVideoWithJson\(\[',
            webpage, 'video data', display_id)['brightcoveVideoId']

        return self.url_result(self._BC_URL_TMPL.format(video_id), BrightcoveNewIE)
