from .common import InfoExtractor
from ..utils import (
    int_or_none,
    try_get,
    urlencode_postdata,
)


class BongaCamsIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<host>(?:[^/]+\.)?bongacams\d*\.(?:com|net))/(?P<id>[^/?&#]+)'
    _TESTS = [{
        'url': 'https://de.bongacams.com/azumi-8',
        'only_matching': True,
    }, {
        'url': 'https://cn.bongacams.com/azumi-8',
        'only_matching': True,
    }, {
        'url': 'https://de.bongacams.net/claireashton',
        'info_dict': {
            'id': 'claireashton',
            'ext': 'mp4',
            'title': r're:ClaireAshton \d{4}-\d{2}-\d{2} \d{2}:\d{2}',
            'age_limit': 18,
            'uploader_id': 'ClaireAshton',
            'uploader': 'ClaireAshton',
            'like_count': int,
            'is_live': True,
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        host = mobj.group('host')
        channel_id = mobj.group('id')

        amf = self._download_json(
            f'https://{host}/tools/amf.php', channel_id,
            data=urlencode_postdata((
                ('method', 'getRoomData'),
                ('args[]', channel_id),
                ('args[]', 'false'),
            )), headers={'X-Requested-With': 'XMLHttpRequest'})

        server_url = amf['localData']['videoServerUrl']

        uploader_id = try_get(
            amf, lambda x: x['performerData']['username'], str) or channel_id
        uploader = try_get(
            amf, lambda x: x['performerData']['displayName'], str)
        like_count = int_or_none(try_get(
            amf, lambda x: x['performerData']['loversCount']))

        formats = self._extract_m3u8_formats(
            f'{server_url}/hls/stream_{uploader_id}/playlist.m3u8',
            channel_id, 'mp4', m3u8_id='hls', live=True)

        return {
            'id': channel_id,
            'title': uploader or uploader_id,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'like_count': like_count,
            'age_limit': 18,
            'is_live': True,
            'formats': formats,
        }
