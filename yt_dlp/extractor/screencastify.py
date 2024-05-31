import urllib.parse

from .common import InfoExtractor
from ..utils import traverse_obj, update_url_query


class ScreencastifyIE(InfoExtractor):
    _VALID_URL = [
        r'https?://watch\.screencastify\.com/v/(?P<id>[^/?#]+)',
        r'https?://app\.screencastify\.com/v[23]/watch/(?P<id>[^/?#]+)',
    ]
    _TESTS = [{
        'url': 'https://watch.screencastify.com/v/sYVkZip3quLKhHw4Ybk8',
        'info_dict': {
            'id': 'sYVkZip3quLKhHw4Ybk8',
            'ext': 'mp4',
            'title': 'Inserting and Aligning the Case Top and Bottom',
            'description': '',
            'uploader': 'Paul Gunn',
            'extra_param_to_segment_url': str,
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        'url': 'https://app.screencastify.com/v3/watch/J5N7H11wofDN1jZUCr3t',
        'info_dict': {
            'id': 'J5N7H11wofDN1jZUCr3t',
            'ext': 'mp4',
            'uploader': 'Scott Piesen',
            'description': '',
            'title': 'Lesson Recording 1-17 Burrr...',
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        'url': 'https://app.screencastify.com/v2/watch/BQ26VbUdfbQLhKzkktOk',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        info = self._download_json(
            f'https://umbrella.svc.screencastify.com/api/umbrellaService/watch/{video_id}', video_id)

        query_string = traverse_obj(info, ('manifest', 'auth', 'query'))
        query = urllib.parse.parse_qs(query_string)
        formats = []
        dash_manifest_url = traverse_obj(info, ('manifest', 'url'))
        if dash_manifest_url:
            formats.extend(
                self._extract_mpd_formats(
                    dash_manifest_url, video_id, mpd_id='dash', query=query, fatal=False))
        hls_manifest_url = traverse_obj(info, ('manifest', 'hlsUrl'))
        if hls_manifest_url:
            formats.extend(
                self._extract_m3u8_formats(
                    hls_manifest_url, video_id, ext='mp4', m3u8_id='hls', query=query, fatal=False))
        for f in formats:
            f['url'] = update_url_query(f['url'], query)

        return {
            'id': video_id,
            'title': info.get('title'),
            'description': info.get('description'),
            'uploader': info.get('userName'),
            'formats': formats,
            'extra_param_to_segment_url': query_string,
        }
