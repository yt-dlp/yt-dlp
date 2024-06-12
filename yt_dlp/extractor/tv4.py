import re

from .common import InfoExtractor
from ..utils import (
    bool_or_none,
    int_or_none,
    parse_iso8601,
    traverse_obj,
    url_or_none,
)


class TV4IE(InfoExtractor):
    IE_DESC = 'tv4.se and tv4play.se'
    _VALID_URL = r'''(?x)https?://(?:www\.)?
        (?:
            tv4\.se/(?:[^/]+)/klipp/(?:.*)-|
            tv4play\.se/
            (?:
                (?:program|barn)/(?:(?:[^/]+/){1,2}|(?:[^\?]+)\?video_id=)|
                iframe/video/|
                film/|
                sport/|
            )
        )(?P<id>[0-9]+)'''
    _GEO_BYPASS = False
    _TESTS = [
        {
            # not geo-restricted
            'url': 'http://www.tv4.se/kalla-fakta/klipp/kalla-fakta-5-english-subtitles-2491650',
            'md5': 'cb837212f342d77cec06e6dad190e96d',
            'info_dict': {
                'id': '2491650',
                'ext': 'mp4',
                'title': 'Kalla Fakta 5 (english subtitles)',
                'description': '2491650',
                'series': 'Kalla fakta',
                'duration': 1335,
                'thumbnail': r're:^https?://[^/?#]+/api/v2/img/',
                'timestamp': 1385373240,
                'upload_date': '20131125',
            },
            'params': {'skip_download': 'm3u8'},
            'expected_warnings': ['Unable to download f4m manifest'],
        },
        {
            'url': 'http://www.tv4play.se/iframe/video/3054113',
            'md5': 'cb837212f342d77cec06e6dad190e96d',
            'info_dict': {
                'id': '3054113',
                'ext': 'mp4',
                'title': 'Så här jobbar ficktjuvarna - se avslöjande bilder',
                'thumbnail': r're:^https?://.*\.jpg$',
                'description': 'Unika bilder avslöjar hur turisternas fickor vittjas mitt på Stockholms central. Två experter på ficktjuvarna avslöjar knepen du ska se upp för.',
                'timestamp': int,
                'upload_date': '20150130',
            },
            'skip': '404 Not Found',
        },
        {
            'url': 'http://www.tv4play.se/sport/3060959',
            'only_matching': True,
        },
        {
            'url': 'http://www.tv4play.se/film/2378136',
            'only_matching': True,
        },
        {
            'url': 'http://www.tv4play.se/barn/looney-tunes?video_id=3062412',
            'only_matching': True,
        },
        {
            'url': 'http://www.tv4play.se/program/farang/3922081',
            'only_matching': True,
        },
        {
            'url': 'https://www.tv4play.se/program/nyheterna/avsnitt/13315940',
            'only_matching': True,
        },
    ]

    def _call_api(self, endpoint, video_id, headers=None, query={}):
        return self._download_json(
            f'https://playback2.a2d.tv/{endpoint}/{video_id}', video_id,
            f'Downloading {endpoint} API JSON', headers=headers, query={
                'service': 'tv4',
                'device': 'browser',
                'protocol': 'hls',
                **query,
            })

    def _real_extract(self, url):
        video_id = self._match_id(url)

        info = traverse_obj(self._call_api('asset', video_id, query={
            'protocol': 'hls,dash',
            'drm': 'widevine',
        }), ('metadata', {dict})) or {}

        manifest_url = self._call_api(
            'play', video_id, headers=self.geo_verification_headers())['playbackItem']['manifestUrl']

        formats, subtitles = [], {}

        fmts, subs = self._extract_m3u8_formats_and_subtitles(
            manifest_url, video_id, 'mp4',
            'm3u8_native', m3u8_id='hls', fatal=False)
        formats.extend(fmts)
        subtitles = self._merge_subtitles(subtitles, subs)

        fmts, subs = self._extract_mpd_formats_and_subtitles(
            manifest_url.replace('.m3u8', '.mpd'),
            video_id, mpd_id='dash', fatal=False)
        formats.extend(fmts)
        subtitles = self._merge_subtitles(subtitles, subs)

        fmts = self._extract_f4m_formats(
            manifest_url.replace('.m3u8', '.f4m'),
            video_id, f4m_id='hds', fatal=False)
        formats.extend(fmts)

        fmts, subs = self._extract_ism_formats_and_subtitles(
            re.sub(r'\.ism/.*?\.m3u8', r'.ism/Manifest', manifest_url),
            video_id, ism_id='mss', fatal=False)
        formats.extend(fmts)
        subtitles = self._merge_subtitles(subtitles, subs)

        if not formats and info.get('is_geo_restricted'):
            self.raise_geo_restricted(
                'This video is not available from your location due to geo-restriction, or not being authenticated',
                countries=['SE'])

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(info, {
                'title': ('title', {str}),
                'description': ('description', {str}),
                'timestamp': (('broadcast_date_time', 'broadcastDateTime'), {parse_iso8601}),
                'duration': ('duration', {int_or_none}),
                'thumbnail': ('image', {url_or_none}),
                'is_live': ('isLive', {bool_or_none}),
                'series': ('seriesTitle', {str}),
                'season_number': ('seasonNumber', {int_or_none}),
                'episode': ('episodeTitle', {str}),
                'episode_number': ('episodeNumber', {int_or_none}),
            }, get_all=False),
        }
