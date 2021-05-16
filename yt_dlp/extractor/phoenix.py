# coding: utf-8
from __future__ import unicode_literals

import re

from .youtube import YoutubeIE
from .zdf import ZDFBaseIE
from ..compat import compat_str
from ..utils import (
    int_or_none,
    merge_dicts,
    try_get,
    unified_timestamp,
    urljoin,
)


class PhoenixIE(ZDFBaseIE):
    IE_NAME = 'phoenix.de'
    _VALID_URL = r'https?://(?:www\.)?phoenix\.de/(?:[^/]+/)*[^/?#&]*-a-(?P<id>\d+)\.html'
    _TESTS = [{
        # Same as https://www.zdf.de/politik/phoenix-sendungen/wohin-fuehrt-der-protest-in-der-pandemie-100.html
        'url': 'https://www.phoenix.de/sendungen/ereignisse/corona-nachgehakt/wohin-fuehrt-der-protest-in-der-pandemie-a-2050630.html',
        'md5': '34ec321e7eb34231fd88616c65c92db0',
        'info_dict': {
            'id': '210222_phx_nachgehakt_corona_protest',
            'ext': 'mp4',
            'title': 'Wohin führt der Protest in der Pandemie?',
            'description': 'md5:7d643fe7f565e53a24aac036b2122fbd',
            'duration': 1691,
            'timestamp': 1613902500,
            'upload_date': '20210221',
            'uploader': 'Phoenix',
            'series': 'corona nachgehakt',
            'episode': 'Wohin führt der Protest in der Pandemie?',
        },
    }, {
        # Youtube embed
        'url': 'https://www.phoenix.de/sendungen/gespraeche/phoenix-streitgut-brennglas-corona-a-1965505.html',
        'info_dict': {
            'id': 'hMQtqFYjomk',
            'ext': 'mp4',
            'title': 'phoenix streitgut: Brennglas Corona - Wie gerecht ist unsere Gesellschaft?',
            'description': 'md5:ac7a02e2eb3cb17600bc372e4ab28fdd',
            'duration': 3509,
            'upload_date': '20201219',
            'uploader': 'phoenix',
            'uploader_id': 'phoenix',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.phoenix.de/entwicklungen-in-russland-a-2044720.html',
        'only_matching': True,
    }, {
        # no media
        'url': 'https://www.phoenix.de/sendungen/dokumentationen/mit-dem-jumbo-durch-die-nacht-a-89625.html',
        'only_matching': True,
    }, {
        # Same as https://www.zdf.de/politik/phoenix-sendungen/die-gesten-der-maechtigen-100.html
        'url': 'https://www.phoenix.de/sendungen/dokumentationen/gesten-der-maechtigen-i-a-89468.html?ref=suche',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        article_id = self._match_id(url)

        article = self._download_json(
            'https://www.phoenix.de/response/id/%s' % article_id, article_id,
            'Downloading article JSON')

        video = article['absaetze'][0]
        title = video.get('titel') or article.get('subtitel')

        if video.get('typ') == 'video-youtube':
            video_id = video['id']
            return self.url_result(
                video_id, ie=YoutubeIE.ie_key(), video_id=video_id,
                video_title=title)

        video_id = compat_str(video.get('basename') or video.get('content'))

        details = self._download_json(
            'https://www.phoenix.de/php/mediaplayer/data/beitrags_details.php',
            video_id, 'Downloading details JSON', query={
                'ak': 'web',
                'ptmd': 'true',
                'id': video_id,
                'profile': 'player2',
            })

        title = title or details['title']
        content_id = details['tracking']['nielsen']['content']['assetid']

        info = self._extract_ptmd(
            'https://tmd.phoenix.de/tmd/2/ngplayer_2_3/vod/ptmd/phoenix/%s' % content_id,
            content_id, None, url)

        duration = int_or_none(try_get(
            details, lambda x: x['tracking']['nielsen']['content']['length']))
        timestamp = unified_timestamp(details.get('editorialDate'))
        series = try_get(
            details, lambda x: x['tracking']['nielsen']['content']['program'],
            compat_str)
        episode = title if details.get('contentType') == 'episode' else None

        thumbnails = []
        teaser_images = try_get(details, lambda x: x['teaserImageRef']['layouts'], dict) or {}
        for thumbnail_key, thumbnail_url in teaser_images.items():
            thumbnail_url = urljoin(url, thumbnail_url)
            if not thumbnail_url:
                continue
            thumbnail = {
                'url': thumbnail_url,
            }
            m = re.match('^([0-9]+)x([0-9]+)$', thumbnail_key)
            if m:
                thumbnail['width'] = int(m.group(1))
                thumbnail['height'] = int(m.group(2))
            thumbnails.append(thumbnail)

        return merge_dicts(info, {
            'id': content_id,
            'title': title,
            'description': details.get('leadParagraph'),
            'duration': duration,
            'thumbnails': thumbnails,
            'timestamp': timestamp,
            'uploader': details.get('tvService'),
            'series': series,
            'episode': episode,
        })
