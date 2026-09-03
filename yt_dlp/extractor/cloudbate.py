import re

from .common import InfoExtractor


class CloudBateIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?cloudbate\.com/video/(?P<id>[0-9]+)/[^/]+/'
    _TESTS = [{
        'url': 'https://www.cloudbate.com/video/1110318/ariannaxo-blowjob-on-cam/',
        'md5': '3af75c71160a6335285afdc40637f0ad',
        'info_dict': {
            # For videos, only the 'id' and 'ext' fields are required to RUN the test:
            'id': '1110318',
            'ext': 'mp4',
            'title': 'Ariannaxo_ blowjob on cam',
            'description': 'Ariannaxo_ blowjob on cam',
            'uploader': 'ariannaxo_',
            'height': 720,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        var = self._html_search_regex(r"window\['player_obj'\] = kt_player\(.*, (?P<var>t[0-9a-z]{10})", webpage, 'var')
        info_txt = self._html_search_regex(r'var '+var+r' = (?P<info>\{[^}]+\});', webpage, 'info')

        # prepare text for json parser
        info_txt = info_txt.replace("'", '"')
        info_txt = re.sub(r'(,|{) ?([a-z0-9_]+)\s*:', r'\1"\2":', info_txt)

        info = self._parse_json(info_txt, video_id)
        height, ext = re.search(r'_(?P<height>\d+)p\.(?P<ext>\w+)$', info['postfix']).groups()

        return {
            'id': video_id,
            'title': info['video_title'],
            'description': self._og_search_description(webpage),
            'uploader': info['video_models'],
            'url': info['video_url'],
            'height': int(height),
            'ext': ext,
        }
