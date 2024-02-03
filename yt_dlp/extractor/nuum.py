import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_iso8601,
    traverse_obj,
    try_get,
)


class NuumBaseIE(InfoExtractor):

    def _call_api(self, path, video_id, description, query={}):
        response = self._download_json(
            f'https://nuum.ru/api/v2/{path}', video_id, query=query,
            note=f'Downloading {description} metadata',
            errnote=f'Unable to download {description} metadata')
        error = response.get('error')
        if error:
            raise ExtractorError(f'API returned error: {error!r}')
        return response.get('result')

    def _get_container(self, url):
        container_id = self._match_id(url)
        return self._call_api(
            f'media-containers/{container_id}', container_id, 'media container')

    def _get_broadcast(self, channel_name):
        return self._call_api(
            'broadcasts/public', video_id=channel_name, description='channel',
            query={
                'with_extra': 'true',
                'channel_name': channel_name,
                'with_deleted': 'true',
            })

    def _extract_thumbnails(self, thumbnails_dict):
        return [{
            'url': url,
            'preference': index,
        } for index, url in enumerate(
            traverse_obj(thumbnails_dict, (('small', 'medium', 'large'),))) if url]

    def _get_media_url(self, media_meta):
        media_archive_url = media_meta.get('media_archive_url')
        if media_archive_url:
            return media_archive_url, False
        return media_meta['media_url'], True

    def _extract_container(self, container):
        stream = traverse_obj(container, ('media_container_streams', 0))
        media = try_get(stream, lambda x: x['stream_media'][0])
        if not media:
            raise ExtractorError('Cannot extract media data')
        media_meta = media.get('media_meta')
        media_url, is_live = self._get_media_url(media_meta)
        video_id = media.get('media_id') or container.get('media_container_id')
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(media_url, video_id, 'mp4')
        return {
            'id': str(video_id),
            'title': container.get('media_container_name'),
            'description': container.get('media_container_description'),
            'thumbnails': self._extract_thumbnails(media_meta.get('media_preview_images' if is_live else 'media_preview_archive_images')),
            'timestamp': parse_iso8601(container.get('created_at')),
            'view_count': int_or_none(stream.get('stream_current_viewers' if is_live else 'stream_total_viewers')),
            'is_live': is_live,
            'formats': formats,
            'subtitles': subtitles,
        }

    def _real_extract(self, url):
        return self._extract_container(self._get_container(url))


class NuumLiveIE(NuumBaseIE):
    IE_NAME = 'nuum:live'
    _VALID_URL = r'https?://nuum\.ru/channel/(?P<id>[^/#?]+)$'
    _TESTS = [{
        'url': 'https://nuum.ru/channel/mts_live',
        'only_matching': True,
    }]

    def _get_container(self, url):
        channel_name = self._match_id(url)
        broadcast = self._get_broadcast(channel_name)
        if not traverse_obj(broadcast, ('channel', 'channel_is_live')):
            raise ExtractorError('The channel is not currently live', expected=True)
        return broadcast.get('media_container')


class NuumTabsIE(NuumBaseIE):
    IE_NAME = 'nuum:tabs'
    _VALID_URL = r'https?://nuum\.ru/channel/(?P<id>[^/#?]+)/(?P<type>streams|videos|clips)'
    _TESTS = [{
        'url': 'https://nuum.ru/channel/mts_live/clips',
        'only_matching': True,
    }, {
        'url': 'https://nuum.ru/channel/mts_live/videos',
        'only_matching': True,
    }, {
        'url': 'https://nuum.ru/channel/mts_live/streams',
        'only_matching': True,
    }]

    def _get_containers(self, channel_id, channel_name, tab_type):
        MAX_LIMIT = 50
        CONTAINER_TYPES = {
            'clips': ['SHORT_VIDEO', 'REVIEW_VIDEO'],
            'videos': ['LONG_VIDEO'],
            'streams': ['SINGLE'],
        }
        qs_types = ''.join([f'&media_container_type={type}' for type in CONTAINER_TYPES[tab_type]])
        query = {
            'limit': MAX_LIMIT,
            'offset': 0,
            'channel_id': channel_id,
            'media_container_status': 'STOPPED'
        }
        media_containers = []
        while True:
            qs_main = urllib.parse.urlencode(query)
            res = self._call_api(
                f'media-containers?{qs_main}{qs_types}', video_id=channel_name, description=tab_type)
            query['offset'] += MAX_LIMIT
            media_containers.extend(res)
            if len(res) == 0 or len(res) < MAX_LIMIT:
                break
        return media_containers

    def _real_extract(self, url):
        channel_name, tab_type = self._match_valid_url(url).group('id', 'type')
        channel_id = traverse_obj(self._get_broadcast(channel_name), ('channel', 'channel_id'))
        containers = self._get_containers(channel_id, channel_name, tab_type)
        entries = [self._extract_container(container) for container in containers]
        return self.playlist_result(entries, channel_name, tab_type)


class NuumMediaIE(NuumBaseIE):
    IE_NAME = 'nuum:media'
    _VALID_URL = r'https?://nuum\.ru/(streams|videos|clips)/(?P<id>[\d]+)'
    _TESTS = [{
        'url': 'https://nuum.ru/streams/1592713-7-days-to-die',
        'only_matching': True,
    }, {
        'url': 'https://nuum.ru/videos/1567547-toxi-hurtz',
        'md5': 'f1d9118a30403e32b702a204eb03aca3',
        'info_dict': {
            'id': '1546357',
            'ext': 'mp4',
            'title': 'Toxi$ - Hurtz',
            'description': '',
            'timestamp': 1702631651,
            'upload_date': '20231215',
            'thumbnail': r're:^https?://.+\.jpg',
            'view_count': int,
        },
    }, {
        'url': 'https://nuum.ru/clips/1552564-pro-misu',
        'md5': 'b248ae1565b1e55433188f11beeb0ca1',
        'info_dict': {
            'id': '1531374',
            'ext': 'mp4',
            'title': 'Про Мису 🙃',
            'timestamp': 1701971828,
            'upload_date': '20231207',
            'thumbnail': r're:^https?://.+\.jpg',
            'view_count': int,
        },
    }]
