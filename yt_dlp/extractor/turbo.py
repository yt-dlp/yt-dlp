import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    ExtractorError,
    int_or_none,
    qualities,
    xpath_text,
)


class TurboIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?turbo\.fr/videos-voiture/(?P<id>[0-9]+)-'
    _API_URL = 'http://www.turbo.fr/api/tv/xml.php?player_generique=player_generique&id={0:}'
    _TEST = {
        'url': 'http://www.turbo.fr/videos-voiture/454443-turbo-du-07-09-2014-renault-twingo-3-bentley-continental-gt-speed-ces-guide-achat-dacia.html',
        'md5': '33f4b91099b36b5d5a91f84b5bcba600',
        'info_dict': {
            'id': '454443',
            'ext': 'mp4',
            'duration': 3715,
            'title': 'Turbo du 07/09/2014 : Renault Twingo 3, Bentley Continental GT Speed, CES, Guide Achat Dacia... ',
            'description': 'Turbo du 07/09/2014 : Renault Twingo 3, Bentley Continental GT Speed, CES, Guide Achat Dacia...',
            'thumbnail': r're:^https?://.*\.jpg$',
        }
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')

        webpage = self._download_webpage(url, video_id)

        playlist = self._download_xml(self._API_URL.format(video_id), video_id)
        item = playlist.find('./channel/item')
        if item is None:
            raise ExtractorError('Playlist item was not found', expected=True)

        title = xpath_text(item, './title', 'title')
        duration = int_or_none(xpath_text(item, './durate', 'duration'))
        thumbnail = xpath_text(item, './visuel_clip', 'thumbnail')
        description = self._html_search_meta('description', webpage)

        formats = []
        get_quality = qualities(['3g', 'sd', 'hq'])
        for child in item:
            m = re.search(r'url_video_(?P<quality>.+)', child.tag)
            if m:
                quality = compat_str(m.group('quality'))
                formats.append({
                    'format_id': quality,
                    'url': child.text,
                    'quality': get_quality(quality),
                })

        return {
            'id': video_id,
            'title': title,
            'duration': duration,
            'thumbnail': thumbnail,
            'description': description,
            'formats': formats,
        }
