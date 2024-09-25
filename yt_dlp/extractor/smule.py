import base64

from .common import InfoExtractor
from .videa import VideaIE
from ..utils import (
    int_or_none,
    js_to_json,
    orderedSet,
    parse_iso8601,
    parse_resolution,
    str_or_none,
    traverse_obj,
    url_or_none,
    urljoin,
)


class SmuleIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?smule\.com/(?:recording/(?P<display_id>[^/]+)|sing-recording|p|c)/(?P<id>[0-9]+_[0-9]+)(?:/frame(?:/box)?)?'
    _EMBED_REGEX = [fr'<iframe[^>]+src=["\'](?P<url>{_VALID_URL})']
    _TESTS = [
        {
            'url': 'https://www.smule.com/recording/billie-happier-than-ever-acoustic/33197115_4356089929',
            'md5': 'e89bdc24625b881f045162ddd71807a0',
            'info_dict': {
                'id': '33197115_4356089929',
                'title': 'Happier Than Ever - Acoustic',
                'display_id': 'billie-happier-than-ever-acoustic',
                'ext': 'mp4',
                'thumbnail': r're:^https?://.*\.jpg$',
                'description': 'md5:aed4e5342a7d9b29c1012003d12a8b41',
                'creators': ['Kait_is_here', 'EllinaRyz'],
                'timestamp': 1651701380,
                'upload_date': '20220504',
                'channel': 'Kait_is_here',
                'channel_id': '33196155',
                'channel_url': 'https://www.smule.com/Kait_is_here',
                'channel_is_verified': False,
                'duration': 295,
                'view_count': int,
                'like_count': int,
                'comment_count': int,
                'artists': ['Billie'],
            },
        },
        {
            'url': 'https://www.smule.com/sing-recording/33197115_4356089929',
            'only_matching': True,
        },
        {
            'url': 'https://www.smule.com/p/33197115_4356089929',
            'only_matching': True,
        },
        {
            'url': 'https://www.smule.com/c/33197115_4356089929',
            'only_matching': True,
        },
        # Responsive embed
        {
            'url': 'https://www.smule.com/recording/billie-happier-than-ever-acoustic/33197115_4356089929/frame',
            'only_matching': True,
        },
        # Box-sized embed
        {
            'url': 'https://www.smule.com/recording/billie-happier-than-ever-acoustic/33197115_4356089929/frame/box',
            'only_matching': True,
        },
        # Same performer listed multiple times (ensure 'creators' is deduplicated)
        {
            'url': 'https://www.smule.com/recording/will-smith-aladdin-disney-arabian-nights/2168232711_4834574691',
            'info_dict': {
                'id': '2168232711_4834574691',
                'title': 'Arabian Nights',
                'display_id': 'will-smith-aladdin-disney-arabian-nights',
                'ext': 'mp4',
                'thumbnail': r're:^https?://.*\.jpg$',
                'description': 'md5:4282995a7d42f4319f7f227e46a64866',
                'creators': ['AngelJ3000'],
                'timestamp': 1711471777,
                'upload_date': '20240326',
                'channel': 'AngelJ3000',
                'channel_id': '2168260843',
                'channel_url': 'https://www.smule.com/AngelJ3000',
                'channel_is_verified': False,
                'duration': 191,
                'view_count': int,
                'like_count': int,
                'comment_count': int,
                'artists': ['Will Smith Aladdin (disney)'],
            },
            'params': {
                'skip_download': True,
            },
        },
    ]

    _STATIC_SECRET = 'M=|ZUyMu^-qWb}VL^jJd}Mv)8y%bQWXf>IFBDcJ>%4zg2Ci|telj`dVZ@'

    def _process_recording(self, b64str):
        if not b64str or len(b64str) < 2 or not b64str.startswith('e:'):
            return b64str

        return VideaIE.rc4(base64.b64decode(b64str[2:]), self._STATIC_SECRET)

    def _extract_creators(self, performance):
        creators = traverse_obj(performance, ('owner', 'handle', {lambda c: [c]}), default=[])
        creators.extend(traverse_obj(performance, ('other_performers', ..., 'handle'), default=[]))
        return orderedSet(creators)

    def _extract_formats(self, video_id, performance):
        formats = []
        for key, format_id in (
            ('media_url', 'm4a'),
            ('visualizer_media_url', 'visualizer'),
            ('video_media_mp4_url', 'mp4'),
            ('video_media_url', 'hls'),
        ):
            enc_url = performance.get(key)
            if not enc_url:
                continue

            url = url_or_none(self._process_recording(enc_url))
            if not url:
                continue

            if format_id == 'hls':
                # Not all performances have an HLS stream. In such case the URL can be the same as the MP4 URL, so we skip it.
                if enc_url == performance.get('video_media_mp4_url'):
                    continue

                formats.extend(self._extract_m3u8_formats(url, video_id, fatal=False))
            else:
                fmt = {
                    'url': url,
                    'format_id': format_id,
                }

                if key == 'media_url':
                    fmt.update(vcodec='none')
                else:
                    fmt.update(parse_resolution(performance.get('video_resolution')))

                formats.append(fmt)

        return formats

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).group('id', 'display_id')
        webpage = self._download_webpage(url, video_id)

        data_store = self._search_json(
            r'<script>\s*window\.DataStore\s*=', webpage, 'data store', video_id,
            end_pattern=r';\s*</script>', transform_source=js_to_json)

        performance = traverse_obj(data_store, ('Pages', 'Recording', 'performance'))
        return {
            'id': video_id,
            'display_id': display_id,
            **traverse_obj(
                performance,
                {
                    'title': ('title', {str_or_none}),
                    'description': ('message', {str_or_none}),
                    'timestamp': ('created_at', {parse_iso8601}),
                    'duration': ('song_length', {int_or_none}),
                    'thumbnail': ('cover_url', {url_or_none}),
                    'view_count': ('stats', 'total_listens', {int_or_none}),
                    'like_count': ('stats', 'total_loves', {int_or_none}),
                    'comment_count': ('stats', 'total_comments', {int_or_none}),
                    'artists': ('artist', {lambda a: [a]}),
                    'channel': ('owner', 'handle', {str_or_none}),
                    'channel_id': ('owner', 'account_id', {str_or_none}),
                    'channel_url': ('owner', 'url', {lambda p: urljoin('https://www.smule.com', p)}),
                    'channel_is_verified': ('owner', 'is_verified', {bool}),
                },
            ),
            'creators': self._extract_creators(performance),
            'formats': self._extract_formats(video_id, performance),
        }
