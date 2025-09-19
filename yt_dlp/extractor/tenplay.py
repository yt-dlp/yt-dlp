import base64
import datetime as dt
import itertools
import json
import re

from .common import InfoExtractor
from ..networking import HEADRequest
from ..utils import (
    ExtractorError,
    int_or_none,
    url_or_none,
    urlencode_postdata,
    urljoin,
)
from ..utils.traversal import traverse_obj


class TenPlayIE(InfoExtractor):
    IE_NAME = '10play'
    _VALID_URL = r'https?://(?:www\.)?10(?:play)?\.com\.au/(?:[^/?#]+/)+(?P<id>tpv\d{6}[a-z]{5})'
    _NETRC_MACHINE = '10play'

    _BASE_HEADERS = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-AU,en;q=0.9',
        'Origin': 'https://10play.com.au',
        'Referer': 'https://10play.com.au/',
    }

    _TESTS = [{
        # Geo-restricted to Australia
        'url': 'https://10.com.au/australian-survivor/web-extras/season-10-brains-v-brawn-ii/myless-journey/tpv250414jdmtf',
        'info_dict': {
            'id': '7440980000013868',
            'ext': 'mp4',
            'title': 'Myles\'s Journey',
            'alt_title': 'Myles\'s Journey',
            'description': 'Relive Myles\'s epic Brains V Brawn II journey to reach the game\'s final two',
            'uploader': 'Channel 10',
            'uploader_id': '2199827728001',
            'age_limit': 15,
            'duration': 249,
            'thumbnail': r're:https://.+/.+\.jpg',
            'series': 'Australian Survivor',
            'season': 'Season 10',
            'season_number': 10,
            'timestamp': 1744629420,
            'upload_date': '20250414',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # Geo-restricted to Australia
        'url': 'https://10.com.au/neighbours/episodes/season-42/episode-9107/tpv240902nzqyp',
        'info_dict': {
            'id': '9000000000091177',
            'ext': 'mp4',
            'title': 'Neighbours - S42 Ep. 9107',
            'alt_title': 'Thu 05 Sep',
            'description': 'md5:37a1f4271be34b9ee2b533426a5fbaef',
            'duration': 1388,
            'episode': 'Episode 9107',
            'episode_number': 9107,
            'season': 'Season 42',
            'season_number': 42,
            'series': 'Neighbours',
            'thumbnail': r're:https://.+/.+\.jpg',
            'age_limit': 15,
            'timestamp': 1725517860,
            'upload_date': '20240905',
            'uploader': 'Channel 10',
            'uploader_id': '2199827728001',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        # Geo-restricted to Australia; upgrading the m3u8 quality fails and we need the fallback
        'url': 'https://10.com.au/tiny-chef-show/episodes/season-1/episode-2/tpv240228pofvt',
        'info_dict': {
            'id': '9000000000084116',
            'ext': 'mp4',
            'uploader': 'Channel 10',
            'uploader_id': '2199827728001',
            'duration': 1297,
            'title': 'The Tiny Chef Show - S1 Ep. 2',
            'alt_title': 'S1 Ep. 2 - Popcorn/banana',
            'description': 'md5:d4758b52b5375dfaa67a78261dcb5763',
            'age_limit': 0,
            'series': 'The Tiny Chef Show',
            'season_number': 1,
            'episode_number': 2,
            'timestamp': 1747957740,
            'thumbnail': r're:https://.+/.+\.jpg',
            'upload_date': '20250522',
            'season': 'Season 1',
            'episode': 'Episode 2',
        },
        'params': {'skip_download': 'm3u8'},
        'expected_warnings': ['Failed to download m3u8 information: HTTP Error 502'],
        'skip': 'video unavailable',
    }, {
        'url': 'https://10play.com.au/how-to-stay-married/web-extras/season-1/terrys-talks-ep-1-embracing-change/tpv190915ylupc',
        'only_matching': True,
    }]
    _GEO_BYPASS = False

    _AUS_AGES = {
        'G': 0,
        'PG': 15,
        'M': 15,
        'MA': 15,
        'MA15+': 15,
        'R': 18,
        'X': 18,
    }

    def _perform_login(self, username, password):
        if hasattr(self, '_cached_token') and self._cached_token:
            return self._cached_token

        timestamp = dt.datetime.utcnow().strftime('%Y%m%d000000')
        auth_header = base64.b64encode(timestamp.encode('ascii')).decode('ascii')

        login_data = self._download_json(
            'https://10play.com.au/api/user/auth',
            None,
            'Logging in',
            'Unable to log in',
            data=json.dumps({'email': username, 'password': password}).encode(),
            headers={
                'X-Network-Ten-Auth': auth_header,
                'Content-Type': 'application/json',
                **self._BASE_HEADERS,
            },
        )

        token = traverse_obj(login_data, ('jwt', 'accessToken'))
        if not token:
            if hasattr(self, '_cached_token'):
                delattr(self, '_cached_token')
            raise ExtractorError('Unable to extract access token from login response')

        self._cached_token = 'Bearer ' + token
        return self._cached_token

    def _get_dai_stream_manifest(self, content_source_id, video_id, dai_auth_token, episode_url):
        form_data = {
            'cmsid': content_source_id,
            'vid': video_id,
            'auth-token': dai_auth_token,
            'url': episode_url,
        }

        dai_url = f'https://dai.google.com/ondemand/hls/content/{content_source_id}/vid/{video_id}/streams'

        response = self._download_json(
            dai_url,
            video_id,
            'Getting DAI stream manifest',
            data=urlencode_postdata(form_data),
            headers={
                'Accept': '*/*',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': episode_url,
            },
        )

        if not response or not isinstance(response, dict):
            raise ExtractorError('Invalid DAI response format')

        manifest_url = traverse_obj(
            response,
            (('stream_manifest', 'manifest', 'url'), {url_or_none}),
            get_all=False,
        )
        if manifest_url:
            return manifest_url

        streams = traverse_obj(response, ('streams', ..., {dict})) or []
        for stream in streams:
            if stream.get('format', '').upper() == 'HLS' and stream.get('url'):
                return stream['url']

        raise ExtractorError('Unable to extract stream manifest from DAI response')

    def _extract_m3u8_url(self, playback_data, dai_auth_token, url):
        direct_source = traverse_obj(playback_data, ('source', {url_or_none}))
        if direct_source and direct_source != 'https://':
            return direct_source

        dai_info = traverse_obj(playback_data, ('dai', {dict})) or {}
        content_source_id = dai_info.get('contentSourceId')
        video_id = dai_info.get('videoId')

        if content_source_id and video_id:
            return self._get_dai_stream_manifest(
                content_source_id, video_id, dai_auth_token, url)

        return None

    def _filter_ads_from_playlist(self, lines, m3u8_url):
        filtered_lines = []
        prev_extinf_idx = None

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#EXTINF:'):
                filtered_lines.append(line)
                prev_extinf_idx = len(filtered_lines) - 1
            elif not stripped.startswith('#'):
                if re.match(r'^https?://redirector\.googlevideo\.com', urljoin(m3u8_url, stripped), re.I):
                    if prev_extinf_idx == len(filtered_lines) - 1:
                        filtered_lines.pop()
                    prev_extinf_idx = None
                else:
                    filtered_lines.append(line)
                    prev_extinf_idx = None
            else:
                filtered_lines.append(line)

        return filtered_lines

    def _create_1080_playlist(self, filtered_lines):
        fhd_lines = [re.sub(r'(-TEN-)(15|30)(\d*)', r'\g<1>50\3', line) for line in filtered_lines]
        fhd_urls = [
            new.strip() for old, new in zip(filtered_lines, fhd_lines)
            if old != new and not new.strip().startswith('#')]

        return fhd_lines, fhd_urls

    def _probe_segments_for_bitrate(self, fhd_urls, m3u8_url, fhd_lines):
        bitrate = 0
        durations = [float(line.split(':')[1].split(',')[0]) for line in fhd_lines if line.startswith('#EXTINF:')]

        for i in [0, len(fhd_urls) // 2, max(0, len(fhd_urls) - 2)]:
            try:
                _, urlh = self._download_webpage_handle(
                    HEADRequest(urljoin(m3u8_url, fhd_urls[i])),
                    None, note=f'Probing 1080p segment {i + 1}', fatal=False)
                if urlh and 'Content-Length' in urlh.headers:
                    size = int_or_none(urlh.headers['Content-Length'], default=0)
                    duration = durations[i] if i < len(durations) else 6.0
                    raw_bitrate = size * 8 // int(duration * 1000)
                    bitrate = max(bitrate, int(raw_bitrate * 0.83))  # Handle overhead from probing AES-128 streams w/o decrypting.
                else:
                    return 0
            except ExtractorError:
                return 0

        return bitrate

    def _access_1080p_streams(self, m3u8_url, content_id, formats):
        # Check if 1080p already exists
        if any(fmt.get('height') == 1080 for fmt in formats):
            return

        try:
            playlist_content = self._download_webpage(
                m3u8_url, content_id, 'Downloading master playlist', fatal=False)
            if not playlist_content:
                return

            if '#EXT-X-STREAM-INF' in playlist_content:
                for line in playlist_content.splitlines():
                    if line.strip() and not line.strip().startswith('#'):
                        m3u8_url = urljoin(m3u8_url, line.strip())
                        break
                playlist_content = self._download_webpage(
                    m3u8_url, content_id, 'Downloading media playlist', fatal=False)

            if not (playlist_content and '#EXTINF:' in playlist_content):
                return

            lines = playlist_content.splitlines()
            filtered_lines = self._filter_ads_from_playlist(lines, m3u8_url)
            fhd_lines, fhd_urls = self._create_1080_playlist(filtered_lines)

            if not fhd_urls:
                self.report_warning('No FHD URLs found - 1080p stream not available')
                return

            try:
                bitrate = self._probe_segments_for_bitrate(fhd_urls, m3u8_url, fhd_lines)
                if bitrate == 0:
                    self.report_warning('1080p stream segments not accessible - skipping 1080p stream')
                    return
            except ExtractorError as e:
                self.report_warning(f'Failed to probe 1080p segments: {e}')
                return

            for fmt in formats:
                if fmt.get('url') == m3u8_url:
                    fmt['hls_media_playlist_data'] = '\n'.join(filtered_lines)
                    break

            formats.append({
                **formats[0],
                'format_id': str(bitrate),
                'height': 1080,
                'width': 1920,
                'tbr': bitrate,
                'hls_media_playlist_data': '\n'.join(fhd_lines),
            })

        except ExtractorError as e:
            self.report_warning(f'Could not process M3U8 for 1080p access: {e}')

    def _real_extract(self, url):
        content_id = self._match_id(url)

        username, password = self._get_login_info()
        if not username or not password:
            raise ExtractorError(
                '10Play requires authentication. Please use --username and --password with valid 10Play credentials.',
            )

        jwt_token = self._perform_login(username, password)
        auth_headers = {
            'Authorization': jwt_token,
            'tp-acceptfeature': 'v1/fw;v1/drm',
            **self._BASE_HEADERS,
        }

        try:
            video_data = self._download_json(
                'https://10.com.au/api/v1/videos/' + content_id,
                content_id,
                'Downloading video metadata',
                headers=auth_headers,
            )

            playback_api_url = video_data.get('playbackApiEndpoint')
            if not playback_api_url:
                raise ExtractorError('Missing playback API endpoint in video metadata')

            playback_data, playback_response = self._download_json_handle(
                playback_api_url + '?platform=samsung',
                content_id,
                'Downloading playback data',
                headers=auth_headers,
            )
        except ExtractorError as e:
            if '401' in str(e) or '403' in str(e) or 'unauthorized' in str(e).lower():
                if hasattr(self, '_cached_token'):
                    delattr(self, '_cached_token')
            raise

        dai_auth_token = playback_response.headers.get('x-dai-auth')
        if not dai_auth_token:
            raise ExtractorError(
                'Missing DAI auth token. This may indicate the content requires different authentication or is not available.',
            )

        m3u8_url = self._extract_m3u8_url(playback_data, dai_auth_token, url)

        if not m3u8_url:
            raise ExtractorError(
                'Unable to extract stream URL. The content may be geo-restricted or require different authentication.',
            )

        if '10play-not-in-oz' in m3u8_url:
            self.raise_geo_restricted(countries=['AU'])
        if '10play_unsupported' in m3u8_url:
            raise ExtractorError('Unable to extract stream')

        formats = self._extract_m3u8_formats(m3u8_url, content_id, 'mp4')
        if not formats:
            raise ExtractorError('No formats found')

        self._access_1080p_streams(m3u8_url, content_id, formats)

        return {
            'id': content_id,
            'formats': formats,
            'subtitles': {'en': [{'url': video_data['captionUrl']}]} if url_or_none(video_data.get('captionUrl')) else None,
            'uploader': 'Channel 10',
            'uploader_id': '2199827728001',
            **traverse_obj(video_data, {
                'id': ('altId', {str}),
                'duration': ('duration', {int_or_none}),
                'title': ('subtitle', {str}),
                'alt_title': ('title', {str}),
                'description': ('description', {str}),
                'age_limit': ('classification', {self._AUS_AGES.get}),
                'series': ('tvShow', {str}),
                'season_number': ('season', {int_or_none}),
                'episode_number': ('episode', {int_or_none}),
                'timestamp': ('published', {int_or_none}),
                'thumbnail': ('imageUrl', {url_or_none}),
            }),
        }


class TenPlaySeasonIE(InfoExtractor):
    IE_NAME = '10play:season'
    _VALID_URL = r'https?://(?:www\.)?10(?:play)?\.com\.au/(?P<show>[^/?#]+)/episodes/(?P<season>[^/?#]+)/?(?:$|[?#])'
    _TESTS = [{
        'url': 'https://10.com.au/masterchef/episodes/season-15',
        'info_dict': {
            'title': 'Season 15',
            'id': 'MTQ2NjMxOQ==',
        },
        'playlist_mincount': 50,
    }, {
        'url': 'https://10.com.au/the-bold-and-the-beautiful-fast-tracked/episodes/season-2024',
        'info_dict': {
            'title': 'Season 2024',
            'id': 'Mjc0OTIw',
        },
        'playlist_mincount': 159,
    }, {
        'url': 'https://10play.com.au/the-bold-and-the-beautiful-fast-tracked/episodes/season-2024',
        'only_matching': True,
    }]

    def _entries(self, load_more_url, display_id=None):
        skip_ids = []
        for page in itertools.count(1):
            episodes_carousel = self._download_json(
                load_more_url, display_id, query={'skipIds[]': skip_ids},
                note=f'Fetching episodes page {page}')

            episodes_chunk = episodes_carousel['items']
            skip_ids.extend(ep['id'] for ep in episodes_chunk)

            for ep in episodes_chunk:
                yield ep['cardLink']
            if not episodes_carousel['hasMore']:
                break

    def _real_extract(self, url):
        show, season = self._match_valid_url(url).group('show', 'season')
        season_info = self._download_json(
            f'https://10.com.au/api/shows/{show}/episodes/{season}', f'{show}/{season}')

        episodes_carousel = traverse_obj(season_info, (
            'content', 0, 'components', (
                lambda _, v: v['title'].lower() == 'episodes',
                (..., {dict}),
            )), get_all=False) or {}

        playlist_id = episodes_carousel['tpId']

        return self.playlist_from_matches(
            self._entries(urljoin(url, episodes_carousel['loadMoreUrl']), playlist_id),
            playlist_id, traverse_obj(season_info, ('content', 0, 'title', {str})),
            getter=urljoin(url))
