from .common import InfoExtractor
from ..utils import (
    traverse_obj,
)


class GraspopIE(InfoExtractor):
    _VALID_URL = r'https?://vod\.graspop\.be/(?P<lang>fr|nl)/(?P<id>[0-9]+)/(?P<title>.*)/'
    _TESTS = [{
        'url': 'https://vod.graspop.be/fr/101556/thy-art-is-murder-concert/',
        'info_dict': {
            'id': '101556',
            'ext': 'mp4',
            'title': 'Thy Art Is Murder',
            'description': 'Thy Art Is Murder @ Graspop',
            'thumbnail': r're:https://cdn-mds\.pickx\.be/festivals/v3/global/original/.*\.jpg',
            'formats': 'count:4',
        },
        'params': {
            'nocheckcertificate': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # e.g. https://vod.graspop.be/fr/101556/thy-art-is-murder-concert/
        # e.g. https://tv.proximus.be/MWC/videocenter/festivals/101556/stream
        metadata = self._download_json(f'https://tv.proximus.be/MWC/videocenter/festivals/{video_id}/stream', video_id)
        band_name = metadata.get('name')
        asset_uri = traverse_obj(metadata, ('source', 'assetUri'))
        poster = traverse_obj(metadata, ('source', 'poster'))

        formats = self._extract_m3u8_formats(asset_uri, video_id=video_id, ext='mp4')

        return {
            'id': video_id,
            'title': band_name,
            'description': f'{band_name} @ Graspop',
            'thumbnail': poster,
            'formats': formats,
        }
