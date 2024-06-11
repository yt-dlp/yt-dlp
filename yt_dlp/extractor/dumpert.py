from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    qualities,
)


class DumpertIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        (?P<protocol>https?)://(?:(?:www|legacy)\.)?dumpert\.nl/(?:
            (?:mediabase|embed|item)/|
            [^#]*[?&]selectedId=
        )(?P<id>[0-9]+[/_][0-9a-zA-Z]+)'''
    _TESTS = [{
        'url': 'https://www.dumpert.nl/item/6646981_951bc60f',
        'md5': '1b9318d7d5054e7dcb9dc7654f21d643',
        'info_dict': {
            'id': '6646981/951bc60f',
            'ext': 'mp4',
            'title': 'Ik heb nieuws voor je',
            'description': 'Niet schrikken hoor',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 9,
            'view_count': int,
            'like_count': int,
        },
    }, {
        'url': 'https://www.dumpert.nl/embed/6675421_dc440fe7',
        'only_matching': True,
    }, {
        'url': 'http://legacy.dumpert.nl/mediabase/6646981/951bc60f',
        'only_matching': True,
    }, {
        'url': 'http://legacy.dumpert.nl/embed/6675421/dc440fe7',
        'only_matching': True,
    }, {
        'url': 'https://www.dumpert.nl/item/100031688_b317a185',
        'info_dict': {
            'id': '100031688/b317a185',
            'ext': 'mp4',
            'title': 'Epic schijnbeweging',
            'description': '<p>Die zag je niet eh</p>',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)$',
            'duration': 12,
            'view_count': int,
            'like_count': int,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.dumpert.nl/toppers?selectedId=100031688_b317a185',
        'only_matching': True,
    }, {
        'url': 'https://www.dumpert.nl/latest?selectedId=100031688_b317a185',
        'only_matching': True,
    }, {
        'url': 'https://www.dumpert.nl/?selectedId=100031688_b317a185',
        'only_matching': True,
    }, {
        'url': 'https://www.dumpert.nl/toppers/dag?selectedId=100086074_f5cef3ac',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url).replace('_', '/')
        item = self._download_json(
            'http://api-live.dumpert.nl/mobile_api/json/info/' + video_id.replace('/', '_'),
            video_id)['items'][0]
        title = item['title']
        media = next(m for m in item['media'] if m.get('mediatype') == 'VIDEO')

        quality = qualities(['flv', 'mobile', 'tablet', '720p', '1080p'])
        formats = []
        for variant in media.get('variants', []):
            uri = variant.get('uri')
            if not uri:
                continue
            version = variant.get('version')
            preference = quality(version)
            if determine_ext(uri) == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    uri, video_id, 'mp4', m3u8_id=version, quality=preference))
            else:
                formats.append({
                    'url': uri,
                    'format_id': version,
                    'quality': preference,
                })

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
