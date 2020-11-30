# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    strip_or_none,
    xpath_attr,
    xpath_text,
)


class InaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www|m)\.)?ina\.fr/(?:video|audio)/(?P<id>[A-Z0-9_]+)'
    _TESTS = [{
        'url': 'http://www.ina.fr/video/I12055569/francois-hollande-je-crois-que-c-est-clair-video.html',
        'md5': 'a667021bf2b41f8dc6049479d9bb38a3',
        'info_dict': {
            'id': 'I12055569',
            'ext': 'mp4',
            'title': 'François Hollande "Je crois que c\'est clair"',
            'description': 'md5:3f09eb072a06cb286b8f7e4f77109663',
        }
    }, {
        'url': 'https://www.ina.fr/video/S806544_001/don-d-organes-des-avancees-mais-d-importants-besoins-video.html',
        'only_matching': True,
    }, {
        'url': 'https://www.ina.fr/audio/P16173408',
        'only_matching': True,
    }, {
        'url': 'https://www.ina.fr/video/P16173408-video.html',
        'only_matching': True,
    }, {
        'url': 'http://m.ina.fr/video/I12055569',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        info_doc = self._download_xml(
            'http://player.ina.fr/notices/%s.mrss' % video_id, video_id)
        item = info_doc.find('channel/item')
        title = xpath_text(item, 'title', fatal=True)
        media_ns_xpath = lambda x: self._xpath_ns(x, 'http://search.yahoo.com/mrss/')
        content = item.find(media_ns_xpath('content'))

        get_furl = lambda x: xpath_attr(content, media_ns_xpath(x), 'url')
        formats = []
        for q, w, h in (('bq', 400, 300), ('mq', 512, 384), ('hq', 768, 576)):
            q_url = get_furl(q)
            if not q_url:
                continue
            formats.append({
                'format_id': q,
                'url': q_url,
                'width': w,
                'height': h,
            })
        if not formats:
            furl = get_furl('player') or content.attrib['url']
            ext = determine_ext(furl)
            formats = [{
                'url': furl,
                'vcodec': 'none' if ext == 'mp3' else None,
                'ext': ext,
            }]

        thumbnails = []
        for thumbnail in content.findall(media_ns_xpath('thumbnail')):
            thumbnail_url = thumbnail.get('url')
            if not thumbnail_url:
                continue
            thumbnails.append({
                'url': thumbnail_url,
                'height': int_or_none(thumbnail.get('height')),
                'width': int_or_none(thumbnail.get('width')),
            })

        return {
            'id': video_id,
            'formats': formats,
            'title': title,
            'description': strip_or_none(xpath_text(item, 'description')),
            'thumbnails': thumbnails,
        }
