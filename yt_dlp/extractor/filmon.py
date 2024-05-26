from .common import InfoExtractor
from ..compat import compat_str
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    int_or_none,
    qualities,
    strip_or_none,
)


class FilmOnIE(InfoExtractor):
    IE_NAME = 'filmon'
    _VALID_URL = r'(?:https?://(?:www\.)?filmon\.com/vod/view/|filmon:)(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.filmon.com/vod/view/24869-0-plan-9-from-outer-space',
        'info_dict': {
            'id': '24869',
            'ext': 'mp4',
            'title': 'Plan 9 From Outer Space',
            'description': 'Dead human, zombies and vampires',
        },
    }, {
        'url': 'https://www.filmon.com/vod/view/2825-1-popeye-series-1',
        'info_dict': {
            'id': '2825',
            'title': 'Popeye Series 1',
            'description': 'The original series of Popeye.',
        },
        'playlist_mincount': 8,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        try:
            response = self._download_json(
                'https://www.filmon.com/api/vod/movie?id=%s' % video_id,
                video_id)['response']
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError):
                errmsg = self._parse_json(e.cause.response.read().decode(), video_id)['reason']
                raise ExtractorError('%s said: %s' % (self.IE_NAME, errmsg), expected=True)
            raise

        title = response['title']
        description = strip_or_none(response.get('description'))

        if response.get('type_id') == 1:
            entries = [self.url_result('filmon:' + episode_id) for episode_id in response.get('episodes', [])]
            return self.playlist_result(entries, video_id, title, description)

        QUALITY = qualities(('low', 'high'))
        formats = []
        for format_id, stream in response.get('streams', {}).items():
            stream_url = stream.get('url')
            if not stream_url:
                continue
            formats.append({
                'format_id': format_id,
                'url': stream_url,
                'ext': 'mp4',
                'quality': QUALITY(stream.get('quality')),
                'protocol': 'm3u8_native',
            })

        thumbnails = []
        poster = response.get('poster', {})
        thumbs = poster.get('thumbs', {})
        thumbs['poster'] = poster
        for thumb_id, thumb in thumbs.items():
            thumb_url = thumb.get('url')
            if not thumb_url:
                continue
            thumbnails.append({
                'id': thumb_id,
                'url': thumb_url,
                'width': int_or_none(thumb.get('width')),
                'height': int_or_none(thumb.get('height')),
            })

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'description': description,
            'thumbnails': thumbnails,
        }


class FilmOnChannelIE(InfoExtractor):
    IE_NAME = 'filmon:channel'
    _VALID_URL = r'https?://(?:www\.)?filmon\.com/(?:tv|channel)/(?P<id>[a-z0-9-]+)'
    _TESTS = [{
        # VOD
        'url': 'http://www.filmon.com/tv/sports-haters',
        'info_dict': {
            'id': '4190',
            'ext': 'mp4',
            'title': 'Sports Haters',
            'description': 'md5:dabcb4c1d9cfc77085612f1a85f8275d',
        },
    }, {
        # LIVE
        'url': 'https://www.filmon.com/channel/filmon-sports',
        'only_matching': True,
    }, {
        'url': 'https://www.filmon.com/tv/2894',
        'only_matching': True,
    }]

    _THUMBNAIL_RES = [
        ('logo', 56, 28),
        ('big_logo', 106, 106),
        ('extra_big_logo', 300, 300),
    ]

    def _real_extract(self, url):
        channel_id = self._match_id(url)

        try:
            channel_data = self._download_json(
                'http://www.filmon.com/api-v2/channel/' + channel_id, channel_id)['data']
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError):
                errmsg = self._parse_json(e.cause.response.read().decode(), channel_id)['message']
                raise ExtractorError('%s said: %s' % (self.IE_NAME, errmsg), expected=True)
            raise

        channel_id = compat_str(channel_data['id'])
        is_live = not channel_data.get('is_vod') and not channel_data.get('is_vox')
        title = channel_data['title']

        QUALITY = qualities(('low', 'high'))
        formats = []
        for stream in channel_data.get('streams', []):
            stream_url = stream.get('url')
            if not stream_url:
                continue
            if not is_live:
                formats.extend(self._extract_wowza_formats(
                    stream_url, channel_id, skip_protocols=['dash', 'rtmp', 'rtsp']))
                continue
            quality = stream.get('quality')
            formats.append({
                'format_id': quality,
                # this is an m3u8 stream, but we are deliberately not using _extract_m3u8_formats
                # because it doesn't have bitrate variants anyway
                'url': stream_url,
                'ext': 'mp4',
                'quality': QUALITY(quality),
            })

        thumbnails = []
        for name, width, height in self._THUMBNAIL_RES:
            thumbnails.append({
                'id': name,
                'url': 'http://static.filmon.com/assets/channels/%s/%s.png' % (channel_id, name),
                'width': width,
                'height': height,
            })

        return {
            'id': channel_id,
            'display_id': channel_data.get('alias'),
            'title': title,
            'description': channel_data.get('description'),
            'thumbnails': thumbnails,
            'formats': formats,
            'is_live': is_live,
        }
