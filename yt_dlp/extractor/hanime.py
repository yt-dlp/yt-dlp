import hashlib
import time

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    traverse_obj,
    url_or_none,
)


class HanimeIE(InfoExtractor):
    IE_NAME = 'hanime'
    _VALID_URL = r'https?://(?:www\.)?hanime\.tv/videos/hentai/(?P<id>[^/?#&]+)'
    _API_BASE = 'https://freeanimehentai.net/api'
    _CACHED_API_BASE = 'https://cached.freeanimehentai.net/api'
    _ORIGIN = 'https://hanime.tv'

    _TESTS = [{
        'url': 'https://hanime.tv/videos/hentai/sister-breeder-4',
        'info_dict': {
            'id': '3418',
            'display_id': 'sister-breeder-4',
            'ext': 'mp4',
            'title': 'Sister Breeder 4',
            'description': str,
            'thumbnail': r're:^https?://.+',
            'age_limit': 18,
            'tags': list,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'timestamp': int,
            'upload_date': str,
            'duration': 981.0,
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://hanime.tv/videos/hentai/sister-breeder-4?playlist_id=rslxsqs7vopbejnztxxs',
        'only_matching': True,
    }, {
        'url': 'https://hanime.tv/videos/hentai/baka-dakedo-chinchin-shaburu-no-dake-wa-jouzu-na-chii-chan-2',
        'only_matching': True,
    }]

    def _generate_signature(self, ts):
        msg = f'{ts},Xkdi29,{self._ORIGIN},mn2,{ts}'
        return hashlib.sha256(msg.encode()).hexdigest()

    def _build_api_headers(self):
        ts = int(time.time())
        return {
            'accept': 'application/json',
            'accept-language': 'en-US,en;q=0.9',
            'origin': self._ORIGIN,
            'referer': f'{self._ORIGIN}/',
            'x-csrf-token': '',
            'x-license': '',
            'x-session-token': '',
            'x-signature': self._generate_signature(ts),
            'x-signature-version': 'web2',
            'x-time': str(ts),
            'x-user-license': '',
        }

    def _search_for_video(self, slug, display_id):
        data = self._download_json(
            f'{self._API_BASE}/v10/search_hvs',
            display_id,
            'Downloading video info',
            headers=self._build_api_headers(),
            query={'search_text': slug.replace('-', ' ')},
            fatal=False,
        ) or {}

        hentai_videos = traverse_obj(data, ('hentai_videos', ...))
        if not hentai_videos:
            hentai_videos = data if isinstance(data, list) else []

        for item in hentai_videos:
            if item.get('slug') == slug:
                return item
        return {}

    def _extract_formats(self, video_id, manifest):
        servers = traverse_obj(manifest, ('videos_manifest', 'servers', ...)) or []
        if not servers:
            raise ExtractorError('No video servers found in manifest', expected=True)

        formats = []
        duration = None
        for server in servers:
            server_name = server.get('name') or server.get('slug') or 'unknown'
            for stream in traverse_obj(server, ('streams', ...)):
                stream_url = url_or_none(stream.get('url'))
                if not stream_url:
                    continue
                height = int_or_none(stream.get('height'))
                width = int_or_none(stream.get('width'))
                filesize = (int_or_none(stream.get('filesize_mbs')) or 0) * 1024 * 1024 or None

                if duration is None:
                    duration_ms = int_or_none(stream.get('duration_in_ms'))
                    if duration_ms:
                        duration = duration_ms / 1000

                if stream.get('kind', '').lower() == 'hls':
                    fmts, _ = self._extract_m3u8_formats_and_subtitles(
                        stream_url, video_id, 'mp4',
                        entry_protocol='m3u8_native',
                        m3u8_id=f'hls-{server_name}',
                        fatal=False,
                    )
                    for f in fmts:
                        f.setdefault('width', width)
                        f.setdefault('height', height)
                        if filesize:
                            f['filesize_approx'] = filesize
                    formats.extend(fmts)
                else:
                    formats.append({
                        'url': stream_url,
                        'format_id': f'{server_name}-{height}p' if height else server_name,
                        'width': width,
                        'height': height,
                        'ext': stream.get('extension') or 'mp4',
                        'filesize_approx': filesize,
                    })

        if not formats:
            raise ExtractorError('No downloadable formats found', expected=True)
        return formats, duration

    def _real_extract(self, url):
        display_id = self._match_id(url)

        info_item = self._search_for_video(display_id, display_id)
        video_id = str(info_item.get('id') or '')

        if not video_id:
            raise ExtractorError(
                f'Could not find video ID for {display_id}', expected=True)

        manifest = self._download_json(
            f'{self._CACHED_API_BASE}/v8/guest/videos/{video_id}/manifest',
            video_id,
            'Downloading video manifest',
            headers=self._build_api_headers(),
        ) or {}

        formats, duration = self._extract_formats(video_id, manifest)

        thumbnails = []
        for thumb_key, preference in (('poster_url', 1), ('cover_url', 0)):
            thumb_url = url_or_none(info_item.get(thumb_key))
            if thumb_url:
                thumbnails.append({'id': thumb_key, 'url': thumb_url, 'preference': preference})

        return {
            'id': video_id,
            'display_id': display_id,
            'title': info_item.get('name') or display_id,
            'description': clean_html(info_item.get('description')) or None,
            'thumbnails': thumbnails,
            'thumbnail': url_or_none(info_item.get('poster_url') or info_item.get('cover_url')),
            'age_limit': 18,
            'tags': traverse_obj(info_item, ('hentai_tags', ..., 'text')) or traverse_obj(info_item, ('tags', ...)) or [],
            'view_count': int_or_none(info_item.get('views')),
            'like_count': int_or_none(info_item.get('likes')),
            'dislike_count': int_or_none(info_item.get('dislikes')),
            'timestamp': int_or_none(
                info_item.get('released_at_unix') or info_item.get('created_at_unix')),
            'duration': duration,
            'formats': formats,
        }
