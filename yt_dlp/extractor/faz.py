import re

from .common import InfoExtractor
from ..compat import compat_etree_fromstring
from ..utils import (
    xpath_element,
    xpath_text,
    int_or_none,
)


class FazIE(InfoExtractor):
    IE_NAME = 'faz.net'
    _VALID_URL = r'https?://(?:www\.)?faz\.net/(?:[^/]+/)*.*?-(?P<id>\d+)\.html'

    _TESTS = [{
        'url': 'http://www.faz.net/multimedia/videos/stockholm-chemie-nobelpreis-fuer-drei-amerikanische-forscher-12610585.html',
        'info_dict': {
            'id': '12610585',
            'ext': 'mp4',
            'title': 'Stockholm: Chemie-Nobelpreis für drei amerikanische Forscher',
            'description': 'md5:1453fbf9a0d041d985a47306192ea253',
        },
    }, {
        'url': 'http://www.faz.net/aktuell/politik/berlin-gabriel-besteht-zerreissprobe-ueber-datenspeicherung-13659345.html',
        'only_matching': True,
    }, {
        'url': 'http://www.faz.net/berlin-gabriel-besteht-zerreissprobe-ueber-datenspeicherung-13659345.html',
        'only_matching': True,
    }, {
        'url': 'http://www.faz.net/-13659345.html',
        'only_matching': True,
    }, {
        'url': 'http://www.faz.net/aktuell/politik/-13659345.html',
        'only_matching': True,
    }, {
        'url': 'http://www.faz.net/foobarblafasel-13659345.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        description = self._og_search_description(webpage)
        media = self._html_search_regex(
            r"data-videojs-media='([^']+)",
            webpage, 'media')
        if media == 'extern':
            perform_url = self._search_regex(
                r"<iframe[^>]+?src='((?:http:)?//player\.performgroup\.com/eplayer/eplayer\.html#/?[0-9a-f]{26}\.[0-9a-z]{26})",
                webpage, 'perform url')
            return self.url_result(perform_url)
        config = compat_etree_fromstring(media)

        encodings = xpath_element(config, 'ENCODINGS', 'encodings', True)
        formats = []
        for pref, code in enumerate(['LOW', 'HIGH', 'HQ']):
            encoding = xpath_element(encodings, code)
            if encoding is not None:
                encoding_url = xpath_text(encoding, 'FILENAME')
                if encoding_url:
                    tbr = xpath_text(encoding, 'AVERAGEBITRATE', 1000)
                    if tbr:
                        tbr = int_or_none(tbr.replace(',', '.'))
                    f = {
                        'url': encoding_url,
                        'format_id': code.lower(),
                        'quality': pref,
                        'tbr': tbr,
                        'vcodec': xpath_text(encoding, 'CODEC'),
                    }
                    mobj = re.search(r'(\d+)x(\d+)_(\d+)\.mp4', encoding_url)
                    if mobj:
                        f.update({
                            'width': int(mobj.group(1)),
                            'height': int(mobj.group(2)),
                            'tbr': tbr or int(mobj.group(3)),
                        })
                    formats.append(f)
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'formats': formats,
            'description': description.strip() if description else None,
            'thumbnail': xpath_text(config, 'STILL/STILL_BIG'),
            'duration': int_or_none(xpath_text(config, 'DURATION')),
        }
