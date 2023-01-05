import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    clean_html,
    determine_ext,
    float_or_none,
    int_or_none,
    parse_iso8601,
)


class HitboxIE(InfoExtractor):
    IE_NAME = 'hitbox'
    _VALID_URL = r'https?://(?:www\.)?(?:hitbox|smashcast)\.tv/(?:[^/]+/)*videos?/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'http://www.hitbox.tv/video/203213',
        'info_dict': {
            'id': '203213',
            'title': 'hitbox @ gamescom, Sub Button Hype extended, Giveaway - hitbox News Update with Oxy',
            'alt_title': 'hitboxlive - Aug 9th #6',
            'description': '',
            'ext': 'mp4',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 215.1666,
            'resolution': 'HD 720p',
            'uploader': 'hitboxlive',
            'view_count': int,
            'timestamp': 1407576133,
            'upload_date': '20140809',
            'categories': ['Live Show'],
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'https://www.smashcast.tv/hitboxlive/videos/203213',
        'only_matching': True,
    }]

    def _extract_metadata(self, url, video_id):
        thumb_base = 'https://edge.sf.hitbox.tv'
        metadata = self._download_json(
            '%s/%s' % (url, video_id), video_id, 'Downloading metadata JSON')

        date = 'media_live_since'
        media_type = 'livestream'
        if metadata.get('media_type') == 'video':
            media_type = 'video'
            date = 'media_date_added'

        video_meta = metadata.get(media_type, [])[0]
        title = video_meta.get('media_status')
        alt_title = video_meta.get('media_title')
        description = clean_html(
            video_meta.get('media_description')
            or video_meta.get('media_description_md'))
        duration = float_or_none(video_meta.get('media_duration'))
        uploader = video_meta.get('media_user_name')
        views = int_or_none(video_meta.get('media_views'))
        timestamp = parse_iso8601(video_meta.get(date), ' ')
        categories = [video_meta.get('category_name')]
        thumbs = [{
            'url': thumb_base + video_meta.get('media_thumbnail'),
            'width': 320,
            'height': 180
        }, {
            'url': thumb_base + video_meta.get('media_thumbnail_large'),
            'width': 768,
            'height': 432
        }]

        return {
            'id': video_id,
            'title': title,
            'alt_title': alt_title,
            'description': description,
            'ext': 'mp4',
            'thumbnails': thumbs,
            'duration': duration,
            'uploader': uploader,
            'view_count': views,
            'timestamp': timestamp,
            'categories': categories,
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        player_config = self._download_json(
            'https://www.smashcast.tv/api/player/config/video/%s' % video_id,
            video_id, 'Downloading video JSON')

        formats = []
        for video in player_config['clip']['bitrates']:
            label = video.get('label')
            if label == 'Auto':
                continue
            video_url = video.get('url')
            if not video_url:
                continue
            bitrate = int_or_none(video.get('bitrate'))
            if determine_ext(video_url) == 'm3u8':
                if not video_url.startswith('http'):
                    continue
                formats.append({
                    'url': video_url,
                    'ext': 'mp4',
                    'tbr': bitrate,
                    'format_note': label,
                    'protocol': 'm3u8_native',
                })
            else:
                formats.append({
                    'url': video_url,
                    'tbr': bitrate,
                    'format_note': label,
                })

        metadata = self._extract_metadata(
            'https://www.smashcast.tv/api/media/video', video_id)
        metadata['formats'] = formats

        return metadata


class HitboxLiveIE(HitboxIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'hitbox:live'
    _VALID_URL = r'https?://(?:www\.)?(?:hitbox|smashcast)\.tv/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'http://www.hitbox.tv/dimak',
        'info_dict': {
            'id': 'dimak',
            'ext': 'mp4',
            'description': 'md5:c9f80fa4410bc588d7faa40003fc7d0e',
            'timestamp': int,
            'upload_date': compat_str,
            'title': compat_str,
            'uploader': 'Dimak',
        },
        'params': {
            # live
            'skip_download': True,
        },
    }, {
        'url': 'https://www.smashcast.tv/dimak',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if HitboxIE.suitable(url) else super(HitboxLiveIE, cls).suitable(url)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        player_config = self._download_json(
            'https://www.smashcast.tv/api/player/config/live/%s' % video_id,
            video_id)

        formats = []
        cdns = player_config.get('cdns')
        servers = []
        for cdn in cdns:
            # Subscribe URLs are not playable
            if cdn.get('rtmpSubscribe') is True:
                continue
            base_url = cdn.get('netConnectionUrl')
            host = re.search(r'.+\.([^\.]+\.[^\./]+)/.+', base_url).group(1)
            if base_url not in servers:
                servers.append(base_url)
                for stream in cdn.get('bitrates'):
                    label = stream.get('label')
                    if label == 'Auto':
                        continue
                    stream_url = stream.get('url')
                    if not stream_url:
                        continue
                    bitrate = int_or_none(stream.get('bitrate'))
                    if stream.get('provider') == 'hls' or determine_ext(stream_url) == 'm3u8':
                        if not stream_url.startswith('http'):
                            continue
                        formats.append({
                            'url': stream_url,
                            'ext': 'mp4',
                            'tbr': bitrate,
                            'format_note': label,
                            'rtmp_live': True,
                        })
                    else:
                        formats.append({
                            'url': '%s/%s' % (base_url, stream_url),
                            'ext': 'mp4',
                            'tbr': bitrate,
                            'rtmp_live': True,
                            'format_note': host,
                            'page_url': url,
                            'player_url': 'http://www.hitbox.tv/static/player/flowplayer/flowplayer.commercial-3.2.16.swf',
                        })

        metadata = self._extract_metadata(
            'https://www.smashcast.tv/api/media/live', video_id)
        metadata['formats'] = formats
        metadata['is_live'] = True
        metadata['title'] = metadata.get('title')

        return metadata
