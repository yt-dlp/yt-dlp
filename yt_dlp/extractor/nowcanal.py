import json
import re

from .brightcove import BrightcoveNewIE
from .common import InfoExtractor


class NowCanalIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?nowcanal\.pt/[\w\-/]+/detalhe/(?P<id>[\w\-]+)'
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
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        m = re.search(r'\.addBrightcoveVideoWithJson\(\[\{([^\}]+)\}\]', webpage, re.MULTILINE)
        data = json.loads(f'{{{m.groups(1)[0]}}}')

        bc_id = data['brightcoveVideoId']
        bc_player = 'chhIqzukMq'
        bc_account = '6108484330001'

        return self.url_result(
            f'https://players.brightcove.net/{bc_account}/{bc_player}_default/index.html?videoId={bc_id}',
            BrightcoveNewIE,
        )
