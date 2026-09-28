
from .kinescope import KinescopeBaseIE
from ..utils import (
    traverse_obj,
)


class SponsrIE(KinescopeBaseIE):

    _VALID_URL = r'https?://(?:www\.)?sponsr\.ru/(?:[^/]+)/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://sponsr.ru/vpered/114539/Rossiya_stroit_zavod_poluprovodnikov_vkosmose_Eksperiment_nachalsya',
        'md5': 'f94e07364c18df48b65903255123cc06',
        'info_dict': {
            'id': '114539',
            'ext': 'mp4',
            'title': 'Россия строит завод полупроводников в космосе. Эксперимент начался!',
            'description': 'Россия строит завод полупроводников в космосе. Эксперимент начался!. О позитивных достижениях России в сфере экономики, науки и о подвигах наших соотечественников',
        },
    }, {
        'url': 'https://sponsr.ru/vpered/113655/Rossiya_zanedelu_megaturbina_novyi_reaktor_sputniki_bespilotnik_idrugie_chudesa_tehniki',
        'md5': '763cad7f406cf35c5169ec95fcbd637f',
        'info_dict': {
            'id': '113655',
            'ext': 'mp4',
            'title': 'Россия за неделю: мегатурбина, новый реактор, спутники, беспилотник и другие чудеса техники',
            'description': 'Россия за неделю: мегатурбина, новый реактор, спутники, беспилотник и другие чудеса техники. О позитивных достижениях России в сфере экономики, науки и о подвигах наших соотечественников',
        },
    }, {
        'url': 'https://sponsr.ru/savvateev/114618/ZADACHKI_IZ_BROSHURY_KOLMOGOROVA__PRODOLJENIE/',
        'md5': 'b70e84d53fbbd1144230e30207b57e7d',
        'info_dict': {
            'id': '114618',
            'ext': 'mp4',
            'title': 'ЗАДАЧКИ ИЗ БРОШЮРЫ КОЛМОГОРОВА - ПРОДОЛЖЕНИЕ!',
            'description': 'ЗАДАЧКИ ИЗ БРОШЮРЫ КОЛМОГОРОВА - ПРОДОЛЖЕНИЕ!. Алексей Савватеев — популяризатор математики и пламенный борец за улучшение школьного образования. Лекции, выступления, новости',

        },
    },


    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        media_id = self._search_regex(
            r'<iframe[^>]+?src=(["\'])(?:https?:)?//(?:www\.)?kinescope\.io/[^"]+"\s*data-url=(["\'])/post/video/\?video_id=(?P<media_id>[^\?]+)[^>]+>', webpage, 'media_id', group='media_id')

        token = traverse_obj(self._search_nextjs_data(webpage, video_id), ('props', 'pageProps', 'project', 'project_kinescope_token'))

        video_info = self._get_video_info(media_id, token, fatal=True, note='Get video info')

        formats = self._get_formats(video_info, fatal=True, note='Get formats')

        return {
            'id': video_id,
            'title': self._og_search_title(webpage).split('|', 1)[0].strip(),
            'description': self._og_search_description(webpage),
            'formats': formats,
            # 'uploader': self._search_regex(r'<div[^>]+id="uploader"[^>]*>([^<]+)<', webpage, 'uploader', fatal=False),
            # TODO: more properties (see yt_dlp/extractor/common.py)
        }
