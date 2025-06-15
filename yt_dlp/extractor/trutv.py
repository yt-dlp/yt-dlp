from .turner import TurnerBaseIE
from ..utils import (
    int_or_none,
    parse_iso8601,
)


class TruTVIE(TurnerBaseIE):
    _VALID_URL = r'https?://(?:www\.)?trutv\.com/(?:shows|full-episodes)/(?P<series_slug>[0-9A-Za-z-]+)/(?:videos/(?P<clip_slug>[0-9A-Za-z-]+)|(?P<id>\d+))'
    _TEST = {
        'url': 'https://www.trutv.com/shows/the-carbonaro-effect/videos/sunlight-activated-flower.html',
        'info_dict': {
            'id': 'f16c03beec1e84cd7d1a51f11d8fcc29124cc7f1',
            'ext': 'mp4',
            'title': 'Sunlight-Activated Flower',
            'description': "A customer is stunned when he sees Michael's sunlight-activated flower.",
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }
    _SOFTWARE_STATEMENT = 'eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJhYzQyOTkwMi0xMDYzLTQyNTQtYWJlYS1iZTY2ODM4MTVmZGIiLCJuYmYiOjE1MzcxOTA4NjgsImlzcyI6ImF1dGguYWRvYmUuY29tIiwiaWF0IjoxNTM3MTkwODY4fQ.ewXl5LDMDvvx3nDXV4jCdSwUq_sOluKoOVsIjznAo6Zo4zrGe9rjlZ9DOmQKW66g6VRMexJsJ5vM1EkY8TC5-YcQw_BclK1FPGO1rH3Wf7tX_l0b1BVbSJQKIj9UgqDp_QbGcBXz24kN4So3U22mhs6di9PYyyfG68ccKL2iRprcVKWCslIHwUF-T7FaEqb0K57auilxeW1PONG2m-lIAcZ62DUwqXDWvw0CRoWI08aVVqkkhnXaSsQfLs5Ph1Pfh9Oq3g_epUm9Ss45mq6XM7gbOb5omTcKLADRKK-PJVB_JXnZnlsXbG0ttKE1cTKJ738qu7j4aipYTf-W0nKF5Q'

    def _real_extract(self, url):
        series_slug, clip_slug, video_id = self._match_valid_url(url).groups()

        if video_id:
            path = 'episode'
            display_id = video_id
        else:
            path = 'series/clip'
            display_id = clip_slug

        data = self._download_json(
            f'https://api.trutv.com/v2/web/{path}/{series_slug}/{display_id}',
            display_id)
        video_data = data['episode'] if video_id else data['info']
        media_id = video_data['mediaId']
        title = video_data['title'].strip()

        info = self._extract_ngtv_info(
            media_id, {}, self._SOFTWARE_STATEMENT, {
                'url': url,
                'site_name': 'truTV',
                'auth_required': video_data.get('isAuthRequired'),
            })

        thumbnails = []
        for image in video_data.get('images', []):
            image_url = image.get('srcUrl')
            if not image_url:
                continue
            thumbnails.append({
                'url': image_url,
                'width': int_or_none(image.get('width')),
                'height': int_or_none(image.get('height')),
            })

        info.update({
            'id': media_id,
            'display_id': display_id,
            'title': title,
            'description': video_data.get('description'),
            'thumbnails': thumbnails,
            'timestamp': parse_iso8601(video_data.get('publicationDate')),
            'series': video_data.get('showTitle'),
            'season_number': int_or_none(video_data.get('seasonNum')),
            'episode_number': int_or_none(video_data.get('episodeNum')),
        })
        return info
