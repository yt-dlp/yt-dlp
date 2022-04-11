from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_iso8601,
    traverse_obj,
    try_get,
)


class WASDTVBaseIE(InfoExtractor):

    def _fetch(self, path, video_id, description, query={}):
        response = self._download_json(
            f'https://wasd.tv/api/{path}', video_id, query=query,
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
        self._sort_formats(formats)
        return {
            'id': str(video_id),
            'title': container.get('media_container_name') or self._og_search_title(self._download_webpage(url, video_id)),
            'description': container.get('media_container_description'),
            'thumbnails': self._extract_thumbnails(media_meta.get('media_preview_images')),
            'timestamp': parse_iso8601(container.get('created_at')),
            'view_count': int_or_none(stream.get('stream_current_viewers' if is_live else 'stream_total_viewers')),
            'is_live': is_live,
            'formats': formats,
            'subtitles': subtitles,
        }

    def _get_container(self, url):
        raise NotImplementedError('Subclass for get media container')

    def _get_media_url(self, media_meta):
        raise NotImplementedError('Subclass for get media url')


class WASDTVStreamIE(WASDTVBaseIE):
    IE_NAME = 'wasdtv:stream'
    _VALID_URL = r'https?://wasd\.tv/(?P<id>[^/#?]+)$'
    _TESTS = [{
        'url': 'https://wasd.tv/24_7',
        'info_dict': {
            'id': '559738',
            'ext': 'mp4',
            'title': 'Live 24/7 Music',
            'description': '24&#x2F;7 Music',
            'timestamp': int,
            'upload_date': r're:^\d{8}$',
            'is_live': True,
            'view_count': int,
        },
    }]

    def _get_container(self, url):
        nickname = self._match_id(url)
        channel = self._fetch(f'channels/nicknames/{nickname}', video_id=nickname, description='channel')
        channel_id = channel.get('channel_id')
        containers = self._fetch(
            'v2/media-containers', channel_id, 'running media containers',
            query={
                'channel_id': channel_id,
                'media_container_type': 'SINGLE',
                'media_container_status': 'RUNNING',
            })
        if not containers:
            raise ExtractorError(f'{nickname} is offline', expected=True)
        return containers[0]

    def _get_media_url(self, media_meta):
        return media_meta['media_url'], True


class WASDTVRecordIE(WASDTVBaseIE):
    IE_NAME = 'wasdtv:record'
    _VALID_URL = r'https?://wasd\.tv/[^/#?]+/videos\?record=(?P<id>\d+)$'
    _TESTS = [{
        'url': 'https://wasd.tv/spacemita/videos?record=907755',
        'md5': 'c9899dd85be4cc997816ff9f9ca516ce',
        'info_dict': {
            'id': '906825',
            'ext': 'mp4',
            'title': 'Музыкальный',
            'description': 'md5:f510388d929ff60ae61d4c3cab3137cc',
            'timestamp': 1645812079,
            'upload_date': '20220225',
            'thumbnail': r're:^https?://.+\.jpg',
            'is_live': False,
            'view_count': int,
        },
    }]

    def _get_container(self, url):
        container_id = self._match_id(url)
        return self._fetch(
            f'v2/media-containers/{container_id}', container_id, 'media container')

    def _get_media_url(self, media_meta):
        media_archive_url = media_meta.get('media_archive_url')
        if media_archive_url:
            return media_archive_url, False
        return media_meta['media_url'], True


class WASDTVClipIE(WASDTVBaseIE):
    IE_NAME = 'wasdtv:clip'
    _VALID_URL = r'https?://wasd\.tv/[^/#?]+/clips\?clip=(?P<id>\d+)$'
    _TESTS = [{
        'url': 'https://wasd.tv/spacemita/clips?clip=26804',
        'md5': '818885e720143d7a4e776ff66fcff148',
        'info_dict': {
            'id': '26804',
            'ext': 'mp4',
            'title': 'Пуш флексит на голове стримера',
            'timestamp': 1646682908,
            'upload_date': '20220307',
            'thumbnail': r're:^https?://.+\.jpg',
            'view_count': int,
        },
    }]

    def _real_extract(self, url):
        clip_id = self._match_id(url)
        clip = self._fetch(f'v2/clips/{clip_id}', video_id=clip_id, description='clip')
        clip_data = clip.get('clip_data')
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(clip_data.get('url'), video_id=clip_id, ext='mp4')
        self._sort_formats(formats)
        return {
            'id': clip_id,
            'title': clip.get('clip_title') or self._og_search_title(self._download_webpage(url, clip_id, fatal=False)),
            'thumbnails': self._extract_thumbnails(clip_data.get('preview')),
            'timestamp': parse_iso8601(clip.get('created_at')),
            'view_count': int_or_none(clip.get('clip_views_count')),
            'formats': formats,
            'subtitles': subtitles,
        }
