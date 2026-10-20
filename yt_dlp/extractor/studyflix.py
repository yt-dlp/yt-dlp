from .common import InfoExtractor
from ..utils import extract_attributes, url_or_none
from ..utils.traversal import traverse_obj


class StudyflixIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pixabay\.com/(?:music|sound-effects)/(?:[^/?#]+-)?(?P<id>\d+)'
    _TESTS = [{
            'url': 'https://studyflix.de/ingenieurwissenschaften/arbeit-und-energie-ii-371',
            'info_dict': {
                'id': '537751',
                'ext': 'mp3',
                'thumbnail': r're:^https?://.*\.(?:png|jpg)',
                'title': 'No Copyright Music by SigmaMusicArt | Royalty-free Music',
            },
        }, {
            'url': 'https://studyflix.de/ingenieurwissenschaften/winkelgeschwindigkeit-1533',
            'info_dict': {
                'id': '245859',
                'ext': 'mp3',
                'title': 'Relaxing Guitar Loop V5 by IdoBerg | Royalty-free Sound Effects',
            },
        }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        info = self._get_info(url, video_id, 'AudioObject')

        return {
            'id': video_id,
            **info,
        }