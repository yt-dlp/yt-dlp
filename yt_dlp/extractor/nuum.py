from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_iso8601,
    traverse_obj,
    try_get,
)


class NuumBaseIE(InfoExtractor):

    def _fetch(self, path, video_id, description, query={}):
        response = self._download_json(
            f'https://nuum.ru/api/v2/{path}', video_id, query=query,
            note=f'Downloading {description} metadata',
            errnote=f'Unable to download {description} metadata')
        error = response.get('error')
        if error:
            raise ExtractorError(f'{self.IE_NAME} returned error: {error}', expected=True)
        return response.get('result')

    def _extract_thumbnails(self, thumbnails_dict):
        return [{
            'url': url,
            'preference': index,
        } for index, url in enumerate(
            traverse_obj(thumbnails_dict, (('small', 'medium', 'large'),))) if url]

    def _get_container(self, url):
        container_id = self._match_id(url)
        return self._fetch(
            f'media-containers/{container_id}', container_id, 'media container')

    def _get_media_url(self, media_meta):
        media_archive_url = media_meta.get('media_archive_url')
        if media_archive_url:
            return media_archive_url, False
        return media_meta['media_url'], True

    def _real_extract(self, url):
        container = self._get_container(url)
        stream = traverse_obj(container, ('media_container_streams', 0))
        media = try_get(stream, lambda x: x['stream_media'][0])
        if not media:
            raise ExtractorError('Can not extract media data.', expected=True)
        media_meta = media.get('media_meta')
        media_url, is_live = self._get_media_url(media_meta)
        video_id = media.get('media_id') or container.get('media_container_id')
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(media_url, video_id, 'mp4')
        return {
            'id': str(video_id),
            'title': container.get('media_container_name') or self._og_search_title(self._download_webpage(url, video_id)),
            'description': container.get('media_container_description'),
            'thumbnails': self._extract_thumbnails(media_meta.get('media_preview_images' if is_live else 'media_preview_archive_images')),
            'timestamp': parse_iso8601(container.get('created_at')),
            'view_count': int_or_none(stream.get('stream_current_viewers' if is_live else 'stream_total_viewers')),
            'is_live': is_live,
            'formats': formats,
            'subtitles': subtitles,
        }


class NuumLiveIE(NuumBaseIE):
    IE_NAME = 'nuum:live'
    _VALID_URL = r'https?://nuum\.ru/channel/(?P<id>[^/#?]+)'
    _TESTS = [{
        'url': 'https://nuum.ru/channel/mts_live',
        'only_matching': True,
    }]

    def _get_container(self, url):
        channel_name = self._match_id(url)
        broadcast = self._fetch(
            'broadcasts/public', video_id=channel_name, description='channel',
            query={
                'with_extra': 'true',
                'channel_name': channel_name,
                'with_deleted': 'true',
            }
        )
        channel = broadcast.get('channel')
        if not channel.get('channel_is_live'):
            raise ExtractorError('The channel is not currently live', expected=True)
        return broadcast.get('media_container')

    def _get_media_url(self, media_meta):
        return media_meta['media_url'], True


class NuumStreamIE(NuumBaseIE):
    IE_NAME = 'nuum:stream'
    _VALID_URL = r'https?://nuum\.ru/streams/(?P<id>[\d]+)'
    _TESTS = [{
        'url': 'https://nuum.ru/streams/1592713-7-days-to-die',
        'only_matching': True,
    }]


class NuumVideoIE(NuumBaseIE):
    IE_NAME = 'nuum:video'
    _VALID_URL = r'https?://nuum\.ru/videos/(?P<id>[\d]+)'
    _TESTS = [{
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
    }]


class NuumClipIE(NuumBaseIE):
    IE_NAME = 'nuum:clip'
    _VALID_URL = r'https?://nuum\.ru/clips/(?P<id>[\d]+)'
    _TESTS = [{
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
