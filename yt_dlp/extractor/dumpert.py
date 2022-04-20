from .common import InfoExtractor
from ..utils import (
    int_or_none,
    qualities,
)


class DumpertIE(InfoExtractor):
    _VALID_URL = r'(?P<protocol>https?)://(?:(?:www|legacy)\.)?dumpert\.nl/(?:mediabase|embed|item)/(?P<id>[0-9]+[/_][0-9a-zA-Z]+)'
    _TESTS = [{
        'url': 'https://www.dumpert.nl/item/6646981_951bc60f',
        'md5': '1b9318d7d5054e7dcb9dc7654f21d643',
        'info_dict': {
            'id': '6646981/951bc60f',
            'ext': 'mp4',
            'title': 'Ik heb nieuws voor je',
            'description': 'Niet schrikken hoor',
            'thumbnail': r're:^https?://.*\.jpg$',
        }
    }, {
        'url': 'https://www.dumpert.nl/embed/6675421_dc440fe7',
        'only_matching': True,
    }, {
        'url': 'http://legacy.dumpert.nl/mediabase/6646981/951bc60f',
        'only_matching': True,
    }, {
        'url': 'http://legacy.dumpert.nl/embed/6675421/dc440fe7',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url).replace('_', '/')
        item = self._download_json(
            'http://api-live.dumpert.nl/mobile_api/json/info/' + video_id.replace('/', '_'),
            video_id)['items'][0]
        title = item['title']
        media = next(m for m in item['media'] if m.get('mediatype') == 'VIDEO')

        quality = qualities(['flv', 'mobile', 'tablet', '720p'])
        formats = []
        for variant in media.get('variants', []):
            uri = variant.get('uri')
            if not uri:
                continue
            version = variant.get('version')
            formats.append({
                'url': uri,
                'format_id': version,
                'quality': quality(version),
            })
        self._sort_formats(formats)

        thumbnails = []
        stills = item.get('stills') or {}
        for t in ('thumb', 'still'):
            for s in ('', '-medium', '-large'):
                still_id = t + s
                still_url = stills.get(still_id)
                if not still_url:
                    continue
                thumbnails.append({
                    'id': still_id,
                    'url': still_url,
                })

        stats = item.get('stats') or {}

        return {
            'id': video_id,
            'title': title,
            'description': item.get('description'),
            'thumbnails': thumbnails,
            'formats': formats,
            'duration': int_or_none(media.get('duration')),
            'like_count': int_or_none(stats.get('kudos_total')),
            'view_count': int_or_none(stats.get('views_total')),
        }
