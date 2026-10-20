from .common import InfoExtractor
from ..utils import extract_attributes, url_or_none
from ..utils.traversal import traverse_obj


class StudyflixIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?studyflix\.de/(?:.*)/(?:[^/?#]+-)?(?P<id>\d+)'
    _TESTS = [{
            'url': 'https://studyflix.de/ingenieurwissenschaften/arbeit-und-energie-ii-371',
            'info_dict': {
                'id': '371',
                'ext': 'mp4',
                'thumbnail': r're:^https?://.*\.(?:png|jpg)',
                'title': 'Arbeit und Energie Übung',
            },
        }, {
            'url': 'https://studyflix.de/ingenieurwissenschaften/winkelgeschwindigkeit-1533',
            'info_dict': {
                'id': '1533',
                'ext': 'mp4',
                'thumbnail': r're:^https?://.*\.(?:png|jpg)',
                'title': 'Winkelgeschwindigkeit',
            },
        }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        info = self._get_info(url, video_id, 'AudioObject')

        return {
            'id': video_id,
            **info,
        }