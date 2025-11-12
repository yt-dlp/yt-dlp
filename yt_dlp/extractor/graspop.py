from .common import InfoExtractor
from ..utils import update_url, url_or_none
from ..utils.traversal import traverse_obj


class GraspopIE(InfoExtractor):
    _VALID_URL = r'https?://vod\.graspop\.be/[a-z]{2}/(?P<id>\d+)/'
    _TESTS = [{
        'url': 'https://vod.graspop.be/fr/101556/thy-art-is-murder-concert/',
        'info_dict': {
            'id': '101556',
            'ext': 'mp4',
            'title': 'Thy Art Is Murder',
            'thumbnail': r're:https://cdn-mds\.pickx\.be/festivals/v3/global/original/.+\.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        metadata = self._download_json(
            f'https://tv.proximus.be/MWC/videocenter/festivals/{video_id}/stream', video_id)

        return {
            'id': video_id,
            'formats': self._extract_m3u8_formats(
                # Downgrade manifest request to avoid incomplete certificate chain error
                update_url(metadata['source']['assetUri'], scheme='http'), video_id, 'mp4'),
            **traverse_obj(metadata, {
                'title': ('name', {str}),
                'thumbnail': ('source', 'poster', {url_or_none}),
            }),
        }
