import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    float_or_none,
    int_or_none,
    join_nonempty,
    mimetype2ext,
    traverse_obj,
    try_get,
    urljoin,
)


class YandexDiskIE(InfoExtractor):
    _VALID_URL = r'''(?x)https?://
        (?P<domain>
            yadi\.sk|
            disk\.(?:360\.)?yandex\.
                (?:
                    az|
                    by|
                    co(?:m(?:\.(?:am|ge|tr))?|\.il)|
                    ee|
                    fr|
                    k[gz]|
                    l[tv]|
                    md|
                    t[jm]|
                    u[az]|
                    ru
                )
        )/(?:[di]/|public.*?\bhash=)(?P<id>[^/?#&]+)'''

    _TESTS = [{
        'url': 'https://yadi.sk/i/VdOeDou8eZs6Y',
        'md5': 'a4a8d52958c8fddcf9845935070402ae',
        'info_dict': {
            'id': 'VdOeDou8eZs6Y',
            'ext': 'mp4',
            'title': '4.mp4',
            'duration': 168.6,
            'uploader': 'y.botova',
            'uploader_id': '300043621',
            'view_count': int,
        },
        'expected_warnings': ['Unable to download JSON metadata'],
    }, {
        'url': 'https://yadi.sk/d/h3WAXvDS3Li3Ce',
        'only_matching': True,
    }, {
        'url': 'https://yadi.sk/public?hash=5DZ296JK9GWCLp02f6jrObjnctjRxMs8L6%2B%2FuhNqk38%3D',
        'only_matching': True,
    }, {
        'url': 'https://disk.360.yandex.ru/i/TM2xsIVsgjY4uw',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        domain, video_id = self._match_valid_url(url).groups()
        password = None
        source_url = None

        webpage = self._download_webpage(url, video_id)
        store = self._parse_json(self._search_regex(
            r'<script[^>]+id="store-prefetch"[^>]*>\s*({.+?})\s*</script>',
            webpage, 'store'), video_id)
        resource = traverse_obj(store, ('resources', store.get('rootResourceId')))

        video_streams = resource.get('videoStreams') or {}
        video_hash = resource.get('hash') or url
        environment = store.get('environment') or {}
        sk = environment.get('sk')
        yandexuid = environment.get('yandexuid')

        def call_api(action, password=None):
            payload = {
                'hash': video_hash,
                'sk': sk,
                'short_url': traverse_obj(store, ('url', 'pathname')),
            }
            if password is not None:
                payload['password'] = password

            resp = self._download_json(
                urljoin(url, '/public/api/') + action, video_id if not password else "", data=json.dumps(payload).encode(), headers={
                    'Content-Type': 'text/plain',
                }, fatal=False) or {}

            return resp.get('token') or resp.get('data') or {}

        if resource.get('id') == 'password-protected':
            password = self.get_param('videopassword')
            if not password:
                raise ExtractorError('Password protected video, use --video-password <password>', expected=True)

            token = call_api('check-password', password)
            self._set_cookie(domain, 'passToken', token)

        webpage = self._download_webpage(url, video_id)
        store = self._parse_json(self._search_regex(
            r'<script[^>]+id="store-prefetch"[^>]*>\s*({.+?})\s*</script>',
            webpage, 'store'), video_id)
        resource = traverse_obj(store, ('resources', store.get('rootResourceId')))

        title = resource.get('name')
        meta = resource.get('meta') or {}

        public_url = meta.get('short_url')
        if public_url:
            video_id = self._match_id(public_url)

        if not password:
            source_url = (self._download_json(
                'https://cloud-api.yandex.net/v1/disk/public/resources/download',
                video_id, query={'public_key': url}, fatal=False) or {}).get('href')

        if sk and yandexuid and not (source_url and video_streams):
            self._set_cookie(domain, 'yandexuid', yandexuid)

            if not source_url:
                # TODO: figure out how to detect if download limit has
                # been reached and then avoid unnecessary source format
                # extraction requests
                source_url = call_api('download-url').get('url')
            if not video_streams:
                video_streams = call_api('get-video-streams')

        formats = []
        if source_url:
            formats.append({
                'url': source_url,
                'format_id': 'source',
                'ext': determine_ext(title, meta.get('ext') or mimetype2ext(meta.get('mime_type')) or 'mp4'),
                'quality': 1,
                'filesize': int_or_none(meta.get('size')),
            })

        for video in (video_streams.get('videos') or []):
            format_url = video.get('url')
            if not format_url:
                continue
            if video.get('dimension') == 'adaptive':
                formats.extend(self._extract_m3u8_formats(
                    format_url, video_id, 'mp4', 'm3u8_native',
                    m3u8_id='hls', fatal=False))
            else:
                size = video.get('size') or {}
                height = int_or_none(size.get('height'))
                formats.append({
                    'ext': 'mp4',
                    'format_id': join_nonempty('hls', height and f'{height}p'),
                    'height': height,
                    'protocol': 'm3u8_native',
                    'url': format_url,
                    'width': int_or_none(size.get('width')),
                })

        uid = resource.get('uid')
        display_name = try_get(store, lambda x: x['users'][uid]['displayName'])

        return {
            'id': video_id,
            'title': title,
            'duration': float_or_none(video_streams.get('duration'), 1000),
            'uploader': display_name,
            'uploader_id': uid,
            'view_count': int_or_none(meta.get('views_counter')),
            'formats': formats,
        }
