import itertools

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    parse_duration,
    parse_iso8601,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class KikaIE(InfoExtractor):
    IE_DESC = 'KiKA.de'
    _VALID_URL = r'https?://(?:www\.)?kika\.de/[\w/-]+/videos/(?P<id>[a-z-]+\d+)'
    _GEO_COUNTRIES = ['DE']

    _TESTS = [{
        # Video without season/episode info
        'url': 'https://www.kika.de/logo/videos/logo-vom-dienstag-achtundzwanzig-oktober-zweitausendfuenfundzwanzig-100',
        'md5': '4a9f6e0f9c6bfcc82394c294f186d6db',
        'info_dict': {
            'id': 'logo-vom-dienstag-achtundzwanzig-oktober-zweitausendfuenfundzwanzig-100',
            'ext': 'mp4',
            'title': 'logo! vom Dienstag, 28. Oktober 2025',
            'description': 'md5:4d28b92cef423bec99740ffaa3e7ec04',
            'duration': 651,
            'timestamp': 1761678000,
            'upload_date': '20251028',
            'modified_timestamp': 1761682624,
            'modified_date': '20251028',
        },
    }, {
        # Video with season/episode info
        # Also: Video with subtitles
        'url': 'https://www.kika.de/kaltstart/videos/video92498',
        'md5': 'e58073070acb195906c55c4ad31dceb3',
        'info_dict': {
            'id': 'video92498',
            'ext': 'mp4',
            'title': '7. Wo ist Leo?',
            'description': 'md5:fb48396a5b75068bcac1df74f1524920',
            'duration': 436,
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 7',
            'episode_number': 7,
            'timestamp': 1702926876,
            'upload_date': '20231218',
            'modified_timestamp': 1710880610,
            'modified_date': '20240319',
            'subtitles': 'count:1',
        },
    }, {
        # Video without subtitles
        'url': 'https://www.kika.de/die-pfefferkoerner/videos/abgezogen-102',
        'md5': '62e97961ce5343c19f0f330a1b6dd736',
        'info_dict': {
            'id': 'abgezogen-102',
            'ext': 'mp4',
            'title': '1. Abgezogen',
            'description': 'md5:42d87963364391f9f8eba8affcb30bd2',
            'duration': 1574,
            'season': 'Season 1',
            'season_number': 1,
            'episode': 'Episode 1',
            'episode_number': 1,
            'timestamp': 1735382700,
            'upload_date': '20241228',
            'modified_timestamp': 1757344051,
            'modified_date': '20250908',
            'subtitles': 'count:0',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        doc = self._download_json(f'https://www.kika.de/_next-api/proxy/v1/videos/{video_id}', video_id)
        video_assets = self._download_json(doc['assets']['url'], video_id)

        subtitles = {}
        # Subtitle API endpoints may be present in the JSON even if there are no subtitles.
        # They then return HTTP 200 with invalid data. So we must check explicitly.
        if doc.get('hasSubtitle'):
            if ttml_resource := url_or_none(video_assets.get('videoSubtitle')):
                subtitles['de'] = [{
                    'url': ttml_resource,
                    'ext': 'ttml',
                }]
            if webvtt_resource := url_or_none(video_assets.get('webvttUrl')):
                subtitles.setdefault('de', []).append({
                    'url': webvtt_resource,
                    'ext': 'vtt',
                })

        return {
            'id': video_id,
            'formats': list(self._extract_formats(video_assets, video_id)),
            'subtitles': subtitles,
            **traverse_obj(doc, {
                'title': ('title', {str}),
                'description': ('description', {str}),
                'timestamp': ('date', {parse_iso8601}),
                'modified_timestamp': ('modificationDate', {parse_iso8601}),
                'duration': ((
                    ('durationInSeconds', {int_or_none}),
                    ('duration', {parse_duration})), any),
                'episode_number': ('episodeNumber', {int_or_none}),
                'season_number': ('season', {int_or_none}),
            }),
        }

    def _extract_formats(self, media_info, video_id):
        for media in traverse_obj(media_info, ('assets', lambda _, v: url_or_none(v['url']))):
            stream_url = media['url']
            ext = determine_ext(stream_url)
            if ext == 'm3u8':
                yield from self._extract_m3u8_formats(
                    stream_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
            else:
                yield {
                    'url': stream_url,
                    'format_id': ext,
                    **traverse_obj(media, {
                        'width': ('frameWidth', {int_or_none}),
                        'height': ('frameHeight', {int_or_none}),
                        # NB: filesize is 0 if unknown, bitrate is -1 if unknown
                        'filesize': ('fileSize', {int_or_none}, filter),
                        'abr': ('bitrateAudio', {int_or_none}, {lambda x: None if x == -1 else x}),
                        'vbr': ('bitrateVideo', {int_or_none}, {lambda x: None if x == -1 else x}),
                    }),
                }


class KikaPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?kika\.de/[\w-]+/(?P<id>[a-z-]+\d+)'

    _TESTS = [{
        'url': 'https://www.kika.de/logo/logo-die-welt-und-ich-562',
        'info_dict': {
            'id': 'logo-die-welt-und-ich-562',
            'title': 'logo!',
            'description': 'md5:7b9d7f65561b82fa512f2cfb553c397d',
        },
        'playlist_count': 100,
    }]

    def _entries(self, playlist_url, playlist_id):
        for page in itertools.count(1):
            data = self._download_json(playlist_url, playlist_id, note=f'Downloading page {page}')
            for item in traverse_obj(data, ('content', lambda _, v: url_or_none(v['api']['url']))):
                yield self.url_result(
                    item['api']['url'], ie=KikaIE,
                    **traverse_obj(item, {
                        'id': ('id', {str}),
                        'title': ('title', {str}),
                        'duration': ('duration', {int_or_none}),
                        'timestamp': ('date', {parse_iso8601}),
                    }))

            playlist_url = traverse_obj(data, ('links', 'next', {url_or_none}))
            if not playlist_url:
                break

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        brand_data = self._download_json(
            f'https://www.kika.de/_next-api/proxy/v1/brands/{playlist_id}', playlist_id)

        return self.playlist_result(
            self._entries(brand_data['videoSubchannel']['videosPageUrl'], playlist_id),
            playlist_id, title=brand_data.get('title'), description=brand_data.get('description'))
