import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    traverse_obj,
)


class KinescopeIE(InfoExtractor):
    _DOMAINS = (
        'sponsr.ru',
    )

    _VALID_URL = rf'''(?x)
        https?://(?:www\.)?(?P<host>{"|".join(map(re.escape, _DOMAINS))})/
        (?:[^/]+)/(?P<id>\d+)(?:/([^/?#]+))?
    '''

#    _VALID_URL = r'https?://(?:www\.)?sponsr\.ru/(?:[^/]+)/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://sponsr.ru/vpered/114539/Rossiya_stroit_zavod_poluprovodnikov_vkosmose_Eksperiment_nachalsya',
        'md5': 'f94e07364c18df48b65903255123cc06',
        'info_dict': {
            'id': '114539',
            'ext': 'mp4',
            'title': 'Россия строит завод полупроводников в космосе. Эксперимент начался! | Время - вперёд! | Sponsr',
            'description': 'Россия строит завод полупроводников в космосе. Эксперимент начался!. О позитивных достижениях России в сфере экономики, науки и о подвигах наших соотечественников',
        },
    }, {
        'url': 'https://sponsr.ru/vpered/113655/Rossiya_zanedelu_megaturbina_novyi_reaktor_sputniki_bespilotnik_idrugie_chudesa_tehniki',
        'md5': '763cad7f406cf35c5169ec95fcbd637f',
        'info_dict': {
            'id': '113655',
            'ext': 'mp4',
            'title': 'Россия за неделю: мегатурбина, новый реактор, спутники, беспилотник и другие чудеса техники | Время - вперёд! | Sponsr',
            'description': 'Россия за неделю: мегатурбина, новый реактор, спутники, беспилотник и другие чудеса техники. О позитивных достижениях России в сфере экономики, науки и о подвигах наших соотечественников',
        },
    }, {
        'url': 'https://sponsr.ru/savvateev/114618/ZADACHKI_IZ_BROSHURY_KOLMOGOROVA__PRODOLJENIE/',
        'md5': 'b70e84d53fbbd1144230e30207b57e7d',
        'info_dict': {
            'id': '114618',
            'ext': 'mp4',
            'title': 'ЗАДАЧКИ ИЗ БРОШЮРЫ КОЛМОГОРОВА - ПРОДОЛЖЕНИЕ! | Маткульт-привет! | Sponsr',
            'description': 'ЗАДАЧКИ ИЗ БРОШЮРЫ КОЛМОГОРОВА - ПРОДОЛЖЕНИЕ!. Алексей Савватеев — популяризатор математики и пламенный борец за улучшение школьного образования. Лекции, выступления, новости',

        },
    },



    ]

    def _call_api(self, url, video_id, fatal=False, **kwargs):
        content = self._download_json(url, video_id, fatal=fatal, **kwargs)
        if traverse_obj(content, 'error'):
            raise self._error_or_warning(ExtractorError(
                f'Kinescope said: {content["error"]}', expected=True), fatal=fatal)
        return content or {}

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        media_id = self._html_search_regex(r'video_id=(.+?)\?', webpage, 'media_id')

        token = traverse_obj(self._search_nextjs_data(webpage, video_id), ('props', 'pageProps', 'project', 'project_kinescope_token'))

        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

        video_info = self._call_api(
            f'https://api.kinescope.io/v1/videos/{media_id}', media_id, fatal=True,
            note='Downloading video file info', headers=headers)

        formats = []
        for item in traverse_obj(video_info, ('data', 'assets')):
            formats.append({
                'url': item.get('download_link'),
                'format_id': item.get('quality'),
                'ext': item.get('filetype'),
                'resolution': item.get('resolution'),
            })

        return {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'formats': formats,
            # 'uploader': self._search_regex(r'<div[^>]+id="uploader"[^>]*>([^<]+)<', webpage, 'uploader', fatal=False),
            # TODO: more properties (see yt_dlp/extractor/common.py)
        }
