import json

from .common import InfoExtractor
from ..compat import (
    compat_urlparse,
)
from ..utils import (
    ExtractorError,
    get_element_by_id,
)


class SlideshareIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?slideshare\.net/[^/]+?/(?P<title>.+?)($|\?)'

    _TEST = {
        'url': 'http://www.slideshare.net/Dataversity/keynote-presentation-managing-scale-and-complexity',
        'info_dict': {
            'id': '25665706',
            'ext': 'mp4',
            'title': 'Managing Scale and Complexity',
            'description': 'This was a keynote presentation at the NoSQL Now! 2013 Conference & Expo (http://www.nosqlnow.com). This presentation was given by Adrian Cockcroft from Netflix.',
        },
    }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        page_title = mobj.group('title')
        webpage = self._download_webpage(url, page_title)
        slideshare_obj = self._search_regex(
            r'\$\.extend\(.*?slideshare_object,\s*(\{.*?\})\);',
            webpage, 'slideshare object')
        info = json.loads(slideshare_obj)
        if info['slideshow']['type'] != 'video':
            raise ExtractorError('Webpage type is "%s": only video extraction is supported for Slideshare' % info['slideshow']['type'], expected=True)

        doc = info['doc']
        bucket = info['jsplayer']['video_bucket']
        ext = info['jsplayer']['video_extension']
        video_url = compat_urlparse.urljoin(bucket, doc + '-SD.' + ext)
        description = get_element_by_id('slideshow-description-paragraph', webpage) or self._html_search_regex(
            r'(?s)<p[^>]+itemprop="description"[^>]*>(.+?)</p>', webpage,
            'description', fatal=False)

        return {
            '_type': 'video',
            'id': info['slideshow']['id'],
            'title': info['slideshow']['title'],
            'ext': ext,
            'url': video_url,
            'thumbnail': info['slideshow']['pin_image_url'],
            'description': description.strip() if description else None,
        }
