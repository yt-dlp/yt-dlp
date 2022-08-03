from .common import InfoExtractor
from ..utils import (
    str_or_none,
    unified_strdate
)


class HarpodeonIE(InfoExtractor):
    _VALID_URL = r'https?:\/\/(?:www\.)?harpodeon\.com\/(?:video|preview)\/[a-zA-Z_]+\/(?P<id>[0-9]+)$'
    _TESTS = [{
        'url': 'https://www.harpodeon.com/video/The_Smoking_Out_of_Bella_Butts/268068288',
        'md5': '727371564a6a9ebccef2073535b5b6bd',
        'info_dict': {
            'id': '268068288',
            'ext': 'mp4',
            'title': 'The Smoking Out of Bella Butts',
            'description': 'Anti-smoking campaigner Bella Butts enlists the help of the mayor\'s wife to enact a ban on tobacco, much to the chagrin of the town\'s cigar-addicted menfolk.',
            'creator': 'Vitagraph Company of America',
            'release_date': '19150101'
        }
    }, {
        'url': 'https://www.harpodeon.com/preview/The_Smoking_Out_of_Bella_Butts/268068288',
        'md5': '6dfea5412845f690c7331be703f884db',
        'info_dict': {
            'id': '268068288',
            'ext': 'mp4',
            'title': 'The Smoking Out of Bella Butts',
            'description': 'Anti-smoking campaigner Bella Butts enlists the help of the mayor\'s wife to enact a ban on tobacco, much to the chagrin of the town\'s cigar-addicted menfolk.',
            'creator': 'Vitagraph Company of America',
            'release_date': '19150101'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title, creator, release_year = self._search_regex(
            r'<div[^>]+videoInfo[^<]*<h2[^>]*>(?P<title>.+)<\/h2>(?:\n<p[^>]*>\((?P<creator>.+), )?(?P<release_year>[0-9]{4})?', webpage, 'title', group=['title', 'creator', 'release_year'])

        hp_base = self._html_search_regex(
            r'hpBase\((?:\'|\")(?P<hpBase>.+)(?:\'|\")', webpage, 'hp_base')

        hp_inject_video, hp_resolution = self._search_regex(
            r'hpInjectVideo\((?:\'|\")(?P<hp_inject_video>.+)(?:\'|\"),(?:\'|\")(?P<hp_resolution>.+)(?:\'|\")', webpage, 'hp_inject_video', group=['hp_inject_video', 'hp_resolution'])

        video_url = hp_base + hp_inject_video + '_' + hp_resolution + ".mp4"

        return {
            'id': video_id,
            'title': title,
            'url': video_url,
            'http_headers': {'Referer': url},
            'description': self._html_search_meta('description', webpage, fatal=False),
            'creator': str_or_none(creator),
            'release_date': unified_strdate(release_year + "0101")
        }
