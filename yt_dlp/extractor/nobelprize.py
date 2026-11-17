from .common import InfoExtractor
from ..utils import (
    UnsupportedError,
    clean_html,
    int_or_none,
    parse_duration,
    parse_qs,
    str_or_none,
    update_url,
)
from ..utils.traversal import find_element, traverse_obj


class NobelPrizeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:mediaplayer|www)\.)?nobelprize\.org/mediaplayer/'
    _TESTS = [{
        'url': 'https://www.nobelprize.org/mediaplayer/?id=2636',
        'info_dict': {
            'id': '2636',
            'ext': 'mp4',
            'title': 'Announcement of the 2016 Nobel Prize in Physics',
            'description': 'md5:1a2d8a6ca80c88fb3b9a326e0b0e8e43',
            'duration': 1560.0,
            'thumbnail': r're:https?://www\.nobelprize\.org/images/.+\.jpg',
            'timestamp': 1504883793,
            'upload_date': '20170908',
        },
    }, {
        'url': 'https://mediaplayer.nobelprize.org/mediaplayer/?qid=12693',
        'info_dict': {
            'id': '12693',
            'ext': 'mp4',
            'title': 'Nobel Lecture by Peter Higgs',
            'description': 'md5:9b12e275dbe3a8138484e70e00673a05',
            'duration': 1800.0,
            'thumbnail': r're:https?://www\.nobelprize\.org/images/.+\.jpg',
            'timestamp': 1504883793,
            'upload_date': '20170908',
        },
    }]

    def _real_extract(self, url):
        video_id = traverse_obj(parse_qs(url), (
            ('id', 'qid'), -1, {int_or_none}, {str_or_none}, any))
        if not video_id:
            raise UnsupportedError(url)
        webpage = self._download_webpage(
            update_url(url, netloc='mediaplayer.nobelprize.org'), video_id)

        return {
            **self._search_json_ld(webpage, video_id),
            'id': video_id,
            'title': self._html_search_meta('caption', webpage),
            'description': traverse_obj(webpage, (
                {find_element(tag='span', attr='itemprop', value='description')}, {clean_html})),
            'duration': parse_duration(self._html_search_meta('duration', webpage)),
        }
