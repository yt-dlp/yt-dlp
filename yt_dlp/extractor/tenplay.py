import base64
import datetime as dt
import itertools
import json
import random
import re

from .common import InfoExtractor
from ..networking import Request
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
    _VALID_URL = (
        r'https?://(?:www\.)?10(?:play)?\.com\.au/(?:[^/?#]+/)+(?P<id>tpv\d{6}[a-z]{5})'
    )
    _NETRC_MACHINE = '10play'

    def _perform_login(self, username, password):
        """Perform login to get JWT token"""
        timestamp = dt.datetime.now().strftime('%Y%m%d000000')
        auth_header = base64.b64encode(
            timestamp.encode('ascii')).decode('ascii')

        login_data = self._download_json(
            'https://10play.com.au/api/user/auth',
            None,
            'Logging in',
            'Unable to log in',
            data=json.dumps(
                {'email': username, 'password': password}).encode(),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Origin': 'https://10play.com.au',
                'Referer': 'https://10play.com.au/',
                'X-Network-Ten-Auth': auth_header,
                'Content-Type': 'application/json',
            },
        )

        token = traverse_obj(login_data, ('jwt', 'accessToken'))
        if not token:
            raise ExtractorError(
                'Unable to extract access token from login response')

        self._jwt_token = f'Bearer {token}'

    def _get_auth_headers(self):
        """Get authentication headers for API requests"""
        return {
            'Authorization': self._jwt_token,
            'tp-acceptfeature': 'v1/fw;v1/drm',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-AU,en;q=0.9',
            'Origin': 'https://10play.com.au',
            'Referer': 'https://10play.com.au/',
        }

    def _get_dai_stream_manifest(
        self, content_source_id, video_id, dai_auth_token, episode_url,
    ):
        """Get DAI stream manifest URL using Google DAI"""
        form_data = {
            'cmsid': content_source_id,
            'vid': video_id,
            'auth-token': dai_auth_token,
            'url': episode_url,
            'ua': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'correlator': str(random.randint(10**12, 10**16)),
        }

        dai_url = f'https://pubads.g.doubleclick.net/ondemand/hls/content/{content_source_id}/vid/{video_id}/streams'

        response = self._download_json(
            dai_url,
            video_id,
            'Getting DAI stream manifest',
            data=urlencode_postdata(form_data),
            headers={
                'User-Agent': form_data['ua'],
                'Accept': '*/*',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': episode_url,
            },
        )

        if not response or not isinstance(response, dict):
            raise ExtractorError('Invalid DAI response format')

        # Try different possible keys for the manifest URL
        manifest_url = traverse_obj(
            response,
            (('stream_manifest', 'manifest', 'url'), {url_or_none}),
            get_all=False,
        )
        if manifest_url:
            return manifest_url

        # Check for streams array
        streams = traverse_obj(response, ('streams', ..., {dict})) or []
        for stream in streams:
            if stream.get('format', '').upper() == 'HLS' and stream.get('url'):
                return stream['url']

        raise ExtractorError(
            'Unable to extract stream manifest from DAI response')

    _TESTS = [
        {
            # Geo-restricted to Australia
            'url': 'https://10.com.au/australian-survivor/web-extras/season-10-brains-v-brawn-ii/myless-journey/tpv250414jdmtf',
            'info_dict': {
                'id': '7440980000013868',
                'ext': 'mp4',
                'title': "Myles's Journey",
                'alt_title': "Myles's Journey",
                'description': "Relive Myles's epic Brains V Brawn II journey to reach the game's final two",
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
        },
        {
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
        },
        {
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
            'expected_warnings': [
                'Failed to download m3u8 information: HTTP Error 502',
            ],
            'skip': 'video unavailable',
        },
        {
            'url': 'https://10play.com.au/how-to-stay-married/web-extras/season-1/terrys-talks-ep-1-embracing-change/tpv190915ylupc',
            'only_matching': True,
        },
    ]
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

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # Require credentials for extraction
        username, password = self._get_login_info()
        if not username or not password:
            raise ExtractorError(
                '10Play requires authentication. Please use --username and --password with valid 10Play credentials.',
            )

        # Perform login
        self._perform_login(username, password)
        auth_headers = self._get_auth_headers()

        # Get video metadata
        video_data = self._download_json(
            f'https://10play.com.au/api/v1/videos/{video_id}',
            video_id,
            'Downloading video metadata',
            headers=auth_headers,
        )

        # Get playback data - use samsung platform for unencrypted 720p content
        playback_data, playback_response = self._download_json_handle(
            f'https://10play.com.au/api/v1/videos/playback/{video_id}?platform=samsung',
            video_id,
            'Downloading playback data',
            headers=auth_headers,
        )

        # Extract DAI auth token from response headers
        dai_auth_token = playback_response.headers.get('x-dai-auth')
        if not dai_auth_token:
            raise ExtractorError(
                'Missing DAI auth token. This may indicate the content requires different authentication or is not available.',
            )

        # Get stream manifest URL
        m3u8_url = None

        # Check for direct source URL
        direct_source = traverse_obj(playback_data, ('source', {url_or_none}))
        if direct_source and direct_source != 'https://':
            m3u8_url = direct_source
        else:
            # Use DAI to get stream manifest
            dai_info = traverse_obj(playback_data, ('dai', {dict})) or {}
            content_source_id = dai_info.get('contentSourceId')
            brightcove_video_id = dai_info.get('videoId')

            if content_source_id and brightcove_video_id:
                m3u8_url = self._get_dai_stream_manifest(
                    content_source_id, brightcove_video_id, dai_auth_token, url,
                )

        if not m3u8_url:
            raise ExtractorError(
                'Unable to extract stream URL. The content may be geo-restricted or require different authentication.',
            )

        # Check for geo-restriction
        if '10play-not-in-oz' in m3u8_url:
            self.raise_geo_restricted(countries=['AU'])
        if '10play_unsupported' in m3u8_url:
            raise ExtractorError(
                'Unable to extract stream (10Play says "unsupported")')

        # Extract M3U8 formats
        formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4')

        # Prepare filtered HLS media playlist (strip googlevideo ad segments) and inject into format
        try:
            master_or_media = self._download_webpage(
                m3u8_url, video_id, 'Downloading M3U8 manifest', fatal=False,
            )
            media_url = m3u8_url
            if master_or_media and '#EXT-X-STREAM-INF' in master_or_media:
                best_bw = -1
                pending_bw = None
                candidate_url = None
                for line in master_or_media.splitlines():
                    line = line.strip()
                    if line.startswith('#EXT-X-STREAM-INF'):
                        attrs = line.split(':', 1)[1] if ':' in line else ''
                        for kv in attrs.split(','):
                            kv = kv.strip()
                            if kv.startswith('BANDWIDTH='):
                                try:
                                    pending_bw = int(kv.split('=', 1)[1])
                                except Exception:
                                    pending_bw = None
                                break
                        continue
                    if line and not line.startswith('#'):
                        if pending_bw is None:
                            pending_bw = 0
                        if pending_bw >= best_bw:
                            best_bw = pending_bw
                            candidate_url = urljoin(m3u8_url, line)
                        pending_bw = None
                media_url = candidate_url or media_url
            media_pl = self._download_webpage(
                media_url, video_id, 'Downloading M3U8 media playlist', fatal=False,
            )
            if media_pl:
                # Build filtered playlist without googlevideo ad segments
                filtered_lines = []
                prev_extinf_index = None
                for raw_line in media_pl.splitlines():
                    line = raw_line.strip()
                    if not line:
                        continue
                    if line.startswith('#EXTINF:'):
                        filtered_lines.append(raw_line)
                        prev_extinf_index = len(filtered_lines) - 1
                        continue
                    if (
                        not line.startswith('#')
                        and 'redirector.googlevideo.com' in line
                    ):
                        # Drop the preceding EXTINF if present, and skip this ad URL
                        if (
                            prev_extinf_index is not None
                            and prev_extinf_index == len(filtered_lines) - 1
                        ):
                            filtered_lines.pop()
                        prev_extinf_index = None
                        continue
                    # Keep all other lines
                    filtered_lines.append(raw_line)
                    if not line.startswith('#'):
                        prev_extinf_index = None
                filtered_m3u8 = '\n'.join(filtered_lines)
                # Attempt bitrate enhancement by mapping TEN-15/30 -> TEN-50 and TEN-1500000/3000000 -> TEN-5000000

                enhanced_probe_urls = []
                replaced_any = False
                enhanced_lines = []
                pat_small = re.compile(r'(-TEN-)(15|30)(\D)')
                pat_numeric = re.compile(r'(-TEN-)(1500000|3000000)(\D)')
                for raw_line in filtered_lines:
                    new_line = pat_small.sub(r'\g<1>50\3', raw_line)
                    new_line = pat_numeric.sub(r'\g<1>5000000\3', new_line)
                    if new_line != raw_line and not new_line.lstrip().startswith('#'):
                        enhanced_probe_urls.append(new_line.strip())
                    if new_line != raw_line:
                        replaced_any = True
                    enhanced_lines.append(new_line)
                enhanced_m3u8 = '\n'.join(enhanced_lines)

                # Build URL->duration map from enhanced playlist for tbr measurement
                seg_durations = []
                last_dur = 0.0
                for raw_line in enhanced_lines:
                    line = raw_line.strip()
                    if not line:
                        continue
                    if line.startswith('#EXTINF:'):
                        try:
                            last_dur = float(line.split(
                                ':', 1)[1].split(',')[0])
                        except Exception:
                            last_dur = 0.0
                        continue
                    if not line.startswith('#'):
                        seg_durations.append((line, last_dur))
                        last_dur = 0.0

                url_to_duration = dict(seg_durations)

                # Single-pass validation + bitrate sampling: probe a subset once
                use_enhanced = False
                tbr_kbps = None
                try:
                    probe_urls = enhanced_probe_urls or [
                        u for u, _ in seg_durations]
                    total = len(probe_urls)
                    idxs = sorted(
                        set(
                            filter(
                                lambda i: 0 <= i < total,
                                [0, total // 2, max(0, total - 2)],
                            ),
                        ),
                    )
                    bytes_sum = 0
                    dur_sum = 0.0
                    for i in idxs:
                        url_i = probe_urls[i]
                        dur_i = url_to_duration.get(url_i, 0.0)
                        _, urlh = self._download_webpage_handle(
                            Request(url_i, headers={'Range': 'bytes=0-0'}),
                            video_id,
                            note=f'Probing enhanced segment {i + 1}/{total}',
                            fatal=True,
                        )
                        length = 0
                        if urlh:
                            cr = urlh.headers.get('Content-Range')
                            if cr and '/' in cr:
                                try:
                                    length = int(cr.rsplit('/', 1)[-1])
                                except Exception:
                                    length = 0
                            if not length:
                                try:
                                    length = int(urlh.headers.get(
                                        'Content-Length') or 0)
                                except Exception:
                                    length = 0
                        if dur_i > 0 and length > 0:
                            bytes_sum += length
                            dur_sum += dur_i
                    use_enhanced = bool(replaced_any)
                    tbr_kbps = int((bytes_sum * 8) / max(dur_sum,
                                   1e-6) / 1000) if dur_sum else None
                except Exception:
                    use_enhanced = False

                # Always inject the filtered (non-enhanced) playlist into the base format
                if not use_enhanced:
                    self.to_screen(
                        'Using original quality media playlist (enhancement unavailable)',
                    )
                else:
                    self.to_screen('Enhanced TEN-50 available (validated)')

                # Attach chosen playlist to the matching format so downloader uses it directly
                for f in formats:
                    if f.get('url') == media_url:
                        f['hls_media_playlist_data'] = filtered_m3u8
                        self.to_screen(
                            'Injected filtered media playlist into selected format',
                        )
                        base_fmt = f
                        break

                # If enhanced is available, append a selectable 1080p format using the enhanced playlist
                if use_enhanced and base_fmt:
                    enh_fmt = dict(base_fmt)
                    # Use measured tbr as numeric format_id to match existing IDs (e.g., 2314, 3849)
                    enh_fmt['format_id'] = str(tbr_kbps or 5200)
                    enh_fmt['format_note'] = 'enhanced'
                    enh_fmt['height'] = 1080
                    enh_fmt['width'] = 1920
                    if tbr_kbps:
                        enh_fmt['tbr'] = tbr_kbps
                    enh_fmt['hls_media_playlist_data'] = enhanced_m3u8
                    formats.append(enh_fmt)

        except Exception as e:
            self.report_warning(f'Failed to prepare filtered playlist: {e}')

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': {'en': [{'url': video_data['captionUrl']}]}
            if url_or_none(video_data.get('captionUrl'))
            else None,
            'uploader': 'Channel 10',
            'uploader_id': '2199827728001',
            **traverse_obj(
                video_data,
                {
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
                },
            ),
        }


class TenPlaySeasonIE(InfoExtractor):
    IE_NAME = '10play:season'
    _VALID_URL = r'https?://(?:www\.)?10(?:play)?\.com\.au/(?P<show>[^/?#]+)/episodes/(?P<season>[^/?#]+)/?(?:$|[?#])'
    _TESTS = [
        {
            'url': 'https://10.com.au/masterchef/episodes/season-15',
            'info_dict': {
                'title': 'Season 15',
                'id': 'MTQ2NjMxOQ==',
            },
            'playlist_mincount': 50,
        },
        {
            'url': 'https://10.com.au/the-bold-and-the-beautiful-fast-tracked/episodes/season-2024',
            'info_dict': {
                'title': 'Season 2024',
                'id': 'Mjc0OTIw',
            },
            'playlist_mincount': 159,
        },
        {
            'url': 'https://10play.com.au/the-bold-and-the-beautiful-fast-tracked/episodes/season-2024',
            'only_matching': True,
        },
    ]

    def _entries(self, load_more_url, display_id=None):
        skip_ids = []
        for page in itertools.count(1):
            episodes_carousel = self._download_json(
                load_more_url,
                display_id,
                query={'skipIds[]': skip_ids},
                note=f'Fetching episodes page {page}',
            )

            episodes_chunk = episodes_carousel['items']
            skip_ids.extend(ep['id'] for ep in episodes_chunk)

            for ep in episodes_chunk:
                yield ep['cardLink']
            if not episodes_carousel['hasMore']:
                break

    def _real_extract(self, url):
        show, season = self._match_valid_url(url).group('show', 'season')
        season_info = self._download_json(
            f'https://10.com.au/api/shows/{show}/episodes/{season}', f'{show}/{season}',
        )

        episodes_carousel = (
            traverse_obj(
                season_info,
                (
                    'content',
                    0,
                    'components',
                    (
                        lambda _, v: v['title'].lower() == 'episodes',
                        (..., {dict}),
                    ),
                ),
                get_all=False,
            )
            or {}
        )

        playlist_id = episodes_carousel['tpId']

        return self.playlist_from_matches(
            self._entries(
                urljoin(url, episodes_carousel['loadMoreUrl']), playlist_id),
            playlist_id,
            traverse_obj(season_info, ('content', 0, 'title', {str})),
            getter=urljoin(url),
        )
