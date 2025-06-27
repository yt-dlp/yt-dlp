import os
import urllib.parse

from .common import InfoExtractor
from ..utils import float_or_none


class CamtasiaEmbedIE(InfoExtractor):
    _VALID_URL = False
    _WEBPAGE_TESTS = [
        {
            'url': 'http://www.ll.mit.edu/workshops/education/videocourses/antennas/lecture1/video/',
            'playlist': [{
                'md5': '0c5e352edabf715d762b0ad4e6d9ee67',
                'info_dict': {
                    'id': 'Fenn-AA_PA_Radar_Course_Lecture_1c_Final',
                    'title': 'Fenn-AA_PA_Radar_Course_Lecture_1c_Final - video1',
                    'ext': 'flv',
                    'duration': 2235.90,
                },
            }, {
                'md5': '10e4bb3aaca9fd630e273ff92d9f3c63',
                'info_dict': {
                    'id': 'Fenn-AA_PA_Radar_Course_Lecture_1c_Final_PIP',
                    'title': 'Fenn-AA_PA_Radar_Course_Lecture_1c_Final - pip',
                    'ext': 'flv',
                    'duration': 2235.93,
                },
            }],
            'info_dict': {
                'title': 'Fenn-AA_PA_Radar_Course_Lecture_1c_Final',
            },
            'skip': 'webpage dead',
        },

    ]

    def _extract_from_webpage(self, url, webpage):
        camtasia_cfg = self._search_regex(
            r'fo\.addVariable\(\s*"csConfigFile",\s*"([^"]+)"\s*\);',
            webpage, 'camtasia configuration file', default=None)
        if camtasia_cfg is None:
            return None

        title = self._html_search_meta('DC.title', webpage, fatal=True)

        camtasia_url = urllib.parse.urljoin(url, camtasia_cfg)
        camtasia_cfg = self._download_xml(
            camtasia_url, self._generic_id(url),
            note='Downloading camtasia configuration',
            errnote='Failed to download camtasia configuration')
        fileset_node = camtasia_cfg.find('./playlist/array/fileset')

        entries = []
        for n in fileset_node.getchildren():
            url_n = n.find('./uri')
            if url_n is None:
                continue

            entries.append({
                'id': os.path.splitext(url_n.text.rpartition('/')[2])[0],
                'title': f'{title} - {n.tag}',
                'url': urllib.parse.urljoin(url, url_n.text),
                'duration': float_or_none(n.find('./duration').text),
            })

        return {
            '_type': 'playlist',
            'entries': entries,
            'title': title,
        }
