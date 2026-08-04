import re
import urllib.parse
import uuid

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    parse_age_limit,
    str_or_none,
    traverse_obj,
)


class CeskaTelevizeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ceskatelevize\.cz/(?:ivysilani|porady|zive)/(?:[^/?#&]+/)*(?P<id>[^/#?]+)'
    _VOD_API = 'https://api.ceskatelevize.cz/video/v1/playlist-vod/v1'
    _LIVE_API = 'https://api.ceskatelevize.cz/video/v1/playlist-live/v1'
    _PLAYER_CLIENT = 'iVysilaniWeb'
    _PLAYER_CLIENT_VERSION = '0.25.1'
    _TESTS = [{
        'url': 'https://www.ceskatelevize.cz/porady/10441294653-hyde-park-civilizace/bonus/45890/',
        'info_dict': {
            'id': 'BO-45890',
            'ext': 'mp4',
            'title': 'Interview with Walter Villadei - Hyde Park Civilizace',
            'description': 'Interview with astronaut Walter Villadei',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 2295.0,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        # live stream
        'url': 'https://www.ceskatelevize.cz/zive/ct1/',
        'info_dict': {
            'id': '102',
            'ext': 'mp4',
            'title': r're:^ČT1 - živé vysílání online',
            'description': 'Sledujte živé vysílání kanálu ČT1 online. Vybírat si můžete i z dalších kanálů České televize na kterémkoli z vašich zařízení.',
            'thumbnail': r're:^https?://.*',
            'live_status': 'is_live',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        # another
        'url': 'https://www.ceskatelevize.cz/ivysilani/zive/ct4/',
        'only_matching': True,
        'info_dict': {
            'id': '402',
            'ext': 'mp4',
            'title': r're:^ČT Sport \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
            'is_live': True,
        },
        # 'skip': 'Georestricted to Czech Republic',
    }, {
        'url': 'https://www.ceskatelevize.cz/ivysilani/embed/iFramePlayer.php?hash=d6a3e1370d2e4fa76296b90bad4dfc19673b641e&IDEC=217 562 22150/0004&channelID=1&width=100%25',
        'only_matching': True,
    }, {
        # video with 18+ age restriction
        'url': 'https://www.ceskatelevize.cz/porady/10520528904-queer/215562210900007-bogotart/',
        'info_dict': {
            'id': '215562210900007',
            'ext': 'mp4',
            'title': 'Bogotart - Queer',
            'description': 'Hlavní město Kolumbie v doprovodu queer umělců. Vroucí svět plný vášně, sebevědomí, ale i násilí a bolesti',
            'thumbnail': r're:^https?://.*',
            'duration': 1556.0,
            'age_limit': 18,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        # iframe embed
        'url': 'https://www.ceskatelevize.cz/porady/10614999031-neviditelni/21251212048/',
        'only_matching': True,
    }]

    def _api_request(self, api_url, video_id, note):
        return self._download_json(
            api_url, video_id, note=note,
            query={
                'canPlayDrm': 'false',
                'quality': 'web',
                'streamType': 'hls',
                'sessionId': str(uuid.uuid4()),
                'origin': 'ivysilani',
                'client': self._PLAYER_CLIENT,
                'clientVersion': self._PLAYER_CLIENT_VERSION,
            },
            headers={
                'X-GEOIP-COUNTRY': 'cz',
                'X-DEVICE': 'web',
                'Origin': 'https://player.ceskatelevize.cz',
                'Referer': 'https://player.ceskatelevize.cz/',
            })

    def _parse_vod_response(self, data, video_id, playlist_id, playlist_title, playlist_description):
        error = data.get('error')
        if error == 'UNSUPPORTED_GEOLOCATION':
            self.raise_geo_restricted(data.get('message') or 'Content not available in your region')
        if error:
            raise ExtractorError(str_or_none(data.get('message')) or f'API error: {error}', expected=True)

        streams = data.get('streams', [])
        if not streams:
            raise ExtractorError('No streams found in API response')

        entries = []
        for i, stream in enumerate(streams):
            stream_url = stream.get('url')
            if not stream_url:
                continue
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(stream_url, playlist_id, 'mp4', fatal=False)

            for sub in stream.get('subtitles', []):
                lang = sub.get('language') or 'cs'
                for sub_file in sub.get('files', []):
                    fmt = sub_file.get('format', '')
                    if fmt in ('vtt', 'ttml') and sub_file.get('url'):
                        subtitles.setdefault(lang, []).append({
                            'url': sub_file['url'],
                            'ext': fmt,
                        })

            entry_id = video_id if len(streams) == 1 else f'{video_id}-{i + 1}'
            entries.append({
                'id': entry_id,
                'title': playlist_title or str_or_none(data.get('title')),
                'description': playlist_description,
                'thumbnail': data.get('previewImageUrl'),
                'duration': float_or_none(stream.get('duration') or data.get('duration')),
                'age_limit': parse_age_limit(traverse_obj(data, ('labeling', 0, 'text'))),
                'formats': formats,
                'subtitles': subtitles,
            })

        if not entries:
            raise ExtractorError('No playable streams found')
        if len(entries) == 1:
            return entries[0]
        return self.playlist_result(entries, playlist_id, playlist_title, playlist_description)

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        parsed_input = urllib.parse.urlparse(url)

        # iFramePlayer.php embeds: player is gone, but IDEC is still in the URL params
        if 'iFramePlayer.php' in parsed_input.path:
            qs = urllib.parse.parse_qs(parsed_input.query)
            idec = qs.get('IDEC', [None])[0]
            if not idec:
                raise ExtractorError('No IDEC found in iFramePlayer URL')
            idec = idec.strip()
            data = self._api_request(
                f'{self._VOD_API}/stream-data/media/external/{urllib.parse.quote(idec, safe="")}',
                playlist_id, 'Downloading stream data')
            return self._parse_vod_response(data, idec, playlist_id, None, None)

        webpage, urlh = self._download_webpage_handle(url, playlist_id)
        parsed_url = urllib.parse.urlparse(urlh.url)

        site_name = self._og_search_property('site_name', webpage, fatal=False, default='Česká televize')
        playlist_title = self._og_search_title(webpage, default=None)
        if site_name and playlist_title:
            playlist_title = re.split(rf'\s*[—|]\s*{site_name}', playlist_title, maxsplit=1)[0]
        playlist_description = self._og_search_description(webpage, default=None)
        if playlist_description:
            playlist_description = playlist_description.replace('\xa0', ' ')

        if '/zive/' in parsed_url.path:
            next_data = self._search_nextjs_data(webpage, playlist_id)
            encoder = traverse_obj(next_data, ('props', 'pageProps', 'data', 'liveBroadcast', 'current', 'encoder'), get_all=False)
            if not encoder:
                raise ExtractorError('Failed to find live channel encoder ID')
            data = self._api_request(
                f'{self._LIVE_API}/stream-data/channel/{encoder}',
                playlist_id, 'Downloading live stream data')

            error = data.get('error')
            if error == 'UNSUPPORTED_GEOLOCATION':
                self.raise_geo_restricted(data.get('message') or 'Content not available in your region')
            if error:
                raise ExtractorError(str_or_none(data.get('message')) or f'API error: {error}', expected=True)

            main_url = traverse_obj(data, ('streamUrls', 'main'))
            if not main_url:
                raise ExtractorError('No live stream URL found')
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(main_url, playlist_id, 'mp4', fatal=False)
            return {
                'id': str_or_none(data.get('id')) or playlist_id,
                'title': playlist_title or str_or_none(data.get('title')),
                'description': playlist_description,
                'thumbnail': data.get('previewImageUrl'),
                'age_limit': parse_age_limit(traverse_obj(data, ('labeling', 0, 'text'))),
                'formats': formats,
                'subtitles': subtitles,
                'is_live': True,
            }

        # VOD: /porady/ or /ivysilani/ (which 308-redirects to /porady/)
        next_data = self._search_nextjs_data(webpage, playlist_id)
        idec = traverse_obj(next_data, ('props', 'pageProps', 'data', ('show', 'mediaMeta'), 'idec'), get_all=False)
        if idec:
            api_url = f'{self._VOD_API}/stream-data/media/external/{idec}'
        else:
            bonus_id = traverse_obj(next_data, ('props', 'pageProps', 'data', 'videobonusDetail', 'bonusId'), get_all=False)
            if not bonus_id:
                raise ExtractorError('Failed to find video ID (IDEC or bonusId)')
            bonus_id = str(bonus_id)
            if not bonus_id.startswith('BO-'):
                bonus_id = f'BO-{bonus_id}'
            idec = bonus_id
            api_url = f'{self._VOD_API}/stream-data/bonus/{bonus_id}'

        data = self._api_request(api_url, playlist_id, 'Downloading stream data')
        return self._parse_vod_response(data, idec, playlist_id, playlist_title, playlist_description)
