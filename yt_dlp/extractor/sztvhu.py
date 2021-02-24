# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor


class SztvHuIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www\.)?sztv\.hu|www\.tvszombathely\.hu)/(?:[^/]+)/.+-(?P<id>[0-9]+)'
    _TEST = {
        'url': 'http://sztv.hu/hirek/cserkeszek-nepszerusitettek-a-kornyezettudatos-eletmodot-a-savaria-teren-20130909',
        'md5': 'a6df607b11fb07d0e9f2ad94613375cb',
        'info_dict': {
            'id': '20130909',
            'ext': 'mp4',
            'title': 'Cserkészek népszerűsítették a környezettudatos életmódot a Savaria téren',
            'description': 'A zöld nap játékos ismeretterjesztő programjait a Magyar Cserkész Szövetség szervezte, akik az ország nyolc városában adják át tudásukat az érdeklődőknek. A PET...',
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        video_file = self._search_regex(
            r'file: "...:(.*?)",', webpage, 'video file')
        title = self._html_search_regex(
            r'<meta name="title" content="([^"]*?) - [^-]*? - [^-]*?"',
            webpage, 'video title')
        description = self._html_search_regex(
            r'<meta name="description" content="([^"]*)"/>',
            webpage, 'video description', fatal=False)
        thumbnail = self._og_search_thumbnail(webpage)

        video_url = 'http://media.sztv.hu/vod/' + video_file

        return {
            'id': video_id,
            'url': video_url,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
        }
