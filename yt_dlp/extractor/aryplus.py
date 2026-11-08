import json
import os
import re
import urllib.parse

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    parse_duration,
    traverse_obj,
    unified_timestamp,
    url_or_none,
)


class ARYPlusIE(InfoExtractor):
    IE_NAME = 'aryplus'
    IE_DESC = 'ARY Plus (aryplus.tv)'

    # Supports:
    # - https://aryplus.tv/video/v2/3/<episode_id>/<series_id>
    # - https://aryplus.tv/video/v2/1/<video_id>
    # - https://aryplus.tv/title/<series_id>
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?aryplus\.tv/
        (?:
            video/v2/(?P<vtype>\d+)/(?P<id>[0-9a-fA-F]{24})(?:/(?P<series_id>[0-9a-fA-F]{24}))? |
            (?P<route>title|watch|live)/(?P<title_id>[0-9a-fA-F]{24})
        )
        (?:[/?#&]|$)
    '''

    _TESTS = [{
        'url': 'https://aryplus.tv/video/v2/3/6a6e0b1e9bc4b079859bc14b/6a57868b5bf57c474cc00a50',
        'info_dict': {
            'id': '6a6e0b1e9bc4b079859bc14b',
            'ext': 'mp4',
            'title': str,
        },
    }, {
        'url': 'https://aryplus.tv/title/6a57868b5bf57c474cc00a50',
        'only_matching': True,
    }]

    _STREAM_KEYS = (
        'streamUrl', 'stream_url', 'videoUrl', 'video_url', 'videoSource',
        'hlsUrl', 'hls_url', 'hls', 'cdnLink', 'cdn_link', 'playbackUrl',
        'playback_url', 'manifestUrl', 'file', 'source', 'url', 'link',
    )

    _cached_api_config = None

    def _unescape(self, text):
        if not text:
            return ''
        return (
            text.replace(r'\/', '/')
            .replace(r'\"', '"')
            .replace(r'\u0026', '&')
            .replace(r'\u003d', '=')
        )

    def _discover_api_config(self, webpage, page_url, video_id):
        """
        Extract ARYPLUS_API_BASE and ARYPLUS_API_KEY (public client key) from env
        or by scanning aryplus.tv's Next.js client chunks.
        """
        if self._cached_api_config:
            return self._cached_api_config

        env_base = os.environ.get('ARYPLUS_API_BASE', '').strip().rstrip('/')
        env_key = os.environ.get('ARYPLUS_API_KEY', '').strip()

        discovered_bases = [env_base] if env_base else []
        discovered_keys = [env_key] if env_key else []
        discovered_routes = []

        script_srcs = re.findall(r'<script[^>]+src=["\']([^"\']+\.js[^"\']*)["\']', webpage)
        # Prioritize page/layout/app chunks over framework/polyfill chunks
        script_srcs.sort(key=lambda s: 1 if any(k in s for k in ('polyfills', 'framework', 'webpack')) else 0)

        for src in script_srcs[:12]:
            full_src = urllib.parse.urljoin(page_url, src)
            js = self._download_webpage(
                full_src, video_id,
                note=f'Inspecting JS bundle {src.split("/")[-1]}',
                fatal=False)
            if not js:
                continue

            ujs = self._unescape(js)

            # 1. Find backend API hosts (aryzap.com / aryplus.tv / aryservices / cloudfront / etc.)
            for m in re.finditer(
                r'https?://[a-zA-Z0-9.-]+\.(?:aryzap\.com|aryplus\.tv|aryservices\.com|onedigital\.tv)(?::\d+)?(?:/api(?:/v\d+)?)?',
                ujs
            ):
                host = m.group(0).rstrip('/')
                if not any(host.endswith(ext) for ext in ('.js', '.css', '.png', '.jpg', '.svg', '.woff2')):
                    if host not in discovered_bases:
                        discovered_bases.append(host)

            # 2. Find public client keys / Bearer tokens / x-api-key values in JS
            for km in re.finditer(
                r'(?:x-api-key|apiKey|api_key|clientKey|client_key|NEXT_PUBLIC_[A-Z0-9_]*KEY|Authorization)["\'\s:=]+["\']([A-Za-z0-9._\-+/=]{16,128})["\']',
                ujs, re.I
            ):
                key_val = km.group(1).strip()
                if key_val not in discovered_keys and not key_val.startswith('http'):
                    discovered_keys.append(key_val)

            # 3. Find API path templates containing v2, episode, series, single, or media
            for pm in re.finditer(
                r'["\']((?:/api)?/v[12]/[a-zA-Z0-9_/${}:.-]+|/api/[a-zA-Z0-9_/${}:.-]+)["\']',
                ujs
            ):
                route = pm.group(1)
                if not route.endswith(('.js', '.css')) and route not in discovered_routes:
                    discovered_routes.append(route)

        self.write_debug(f'Discovered API bases: {discovered_bases}')
        self.write_debug(f'Discovered API keys count: {len(discovered_keys)}')
        self.write_debug(f'Discovered API routes: {discovered_routes}')

        self._cached_api_config = {
            'bases': discovered_bases or [
                'https://backend.aryzap.com/api',
                'https://api.aryzap.com/api',
                'https://node.aryzap.com/api',
                'https://aryplus.tv/api',
            ],
            'keys': discovered_keys,
            'routes': discovered_routes,
        }
        return self._cached_api_config

    def _extract_rsc_objects(self, webpage):
        """Parse JSON objects embedded inside Next.js App Router self.__next_f.push() scripts."""
        objs = []
        marker = 'self.__next_f.push('
        pos = 0
        while True:
            idx = webpage.find(marker, pos)
            if idx == -1:
                break
            start = idx + len(marker)
            end = webpage.find(')</script>', start)
            if end == -1:
                end = webpage.find(');', start)
            if end == -1:
                break
            raw = webpage[start:end].strip()
            pos = end + 1
            try:
                parsed_outer = json.loads(raw)
                if isinstance(parsed_outer, list) and len(parsed_outer) >= 2 and isinstance(parsed_outer[1], str):
                    for line in parsed_outer[1].splitlines():
                        _, sep, payload = line.partition(':')
                        if sep and payload.strip().startswith(('{', '[')):
                            try:
                                objs.append(json.loads(payload.strip()))
                            except Exception:
                                pass
            except Exception:
                pass
        return objs

    def _find_stream_in_dict(self, d):
        if not isinstance(d, dict):
            return None
        for k in self._STREAM_KEYS:
            val = d.get(k)
            if isinstance(val, str) and val.strip():
                if any(tok in val for tok in ('.m3u8', '.mp4', 'aryzap', 'cdn.', 'vod.', 'youtube.com', 'youtu.be', 'dailymotion.com')):
                    return val.strip()
        return None

    def _search_json_tree(self, root, target_id=None):
        """Recursively collect episode dicts, stream URLs, and metadata from any JSON structure."""
        episodes = []
        streams = []
        matched_meta = {}
        series_meta = {}

        def _walk(node):
            if isinstance(node, dict):
                nid = str(node.get('_id') or node.get('id') or '')
                if traverse_obj(node, 'is_drm', 'drm', 'widevineUrl', 'fairplayUrl'):
                    self.report_drm(nid or target_id or 'aryplus')

                stream = self._find_stream_in_dict(node)
                if stream:
                    streams.append((nid, stream, node))

                if target_id and nid == target_id:
                    matched_meta.update(node)

                for list_key in ('episode', 'episodes', 'episodeList', 'videos', 'data', 'items', 'results'):
                    arr = node.get(list_key)
                    if isinstance(arr, list) and arr and isinstance(arr[0], dict):
                        for item in arr:
                            if isinstance(item, dict) and (
                                self._find_stream_in_dict(item)
                                or any(k in item for k in ('episodeNumber', 'episode_number', 'title', 'name', '_id'))
                            ):
                                episodes.append(item)

                if ('title' in node or 'name' in node) and any(k in node for k in ('description', 'storyline', 'cast', 'episode', 'episodes')):
                    if not series_meta.get('title'):
                        series_meta.update(node)

                for v in node.values():
                    _walk(v)
            elif isinstance(node, list):
                for item in node:
                    _walk(item)

        _walk(root)
        return episodes, streams, matched_meta, series_meta

    def _build_Headers(self, referer_url, api_keys):
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://aryplus.tv',
            'Referer': referer_url,
        }
        if api_keys:
            key = api_keys[0]
            headers['x-api-key'] = key
            headers['Authorization'] = key if key.startswith('Bearer ') else f'Bearer {key}'
        return headers

    def _query_backend_apis(self, config, video_id, series_id, vtype, referer_url):
        headers = self._build_Headers(referer_url, config.get('keys'))
        candidate_urls = []

        for base in config.get('bases', []):
            base = base.rstrip('/')
            # Build candidate API URLs using discovered bases
            candidate_urls.extend([
                f'{base}/v2/{vtype}/{video_id}' + (f'/{series_id}' if series_id else ''),
                f'{base}/v2/{vtype}/{video_id}',
                f'{base}/episode/{video_id}',
                f'{base}/single/{video_id}',
                f'{base}/media/{video_id}',
                f'{base}/vod/{video_id}',
            ])
            if series_id:
                candidate_urls.extend([
                    f'{base}/v2/{vtype}/{series_id}',
                    f'{base}/series/{series_id}',
                    f'{base}/episode/bySeries/{series_id}',
                ])

        seen = set()
        for api_url in candidate_urls:
            if api_url in seen:
                continue
            seen.add(api_url)
            res = self._download_json(
                api_url, video_id,
                note=f'Querying API {api_url}',
                headers=headers, fatal=False, expected_status=lambda s: True)
            if isinstance(res, (dict, list)) and res:
                episodes, streams, matched_meta, series_meta = self._search_json_tree(res, video_id)
                if streams or episodes:
                    return episodes, streams, matched_meta, series_meta
        return [], [], {}, {}

    def _format_video_result(self, stream_url, video_id, meta, webpage='', series_title=None):
        meta = meta or {}
        title = (
            traverse_obj(meta, 'title', 'name', 'episodeTitle', 'episode_title')
            or (self._og_search_title(webpage, default=None) if webpage else None)
            or (self._html_extract_title(webpage, default=None) if webpage else None)
            or video_id
        )
        title = re.sub(r'^\s*Watch\s+|\s*\|\s*ARY Plus.*$', '', title, flags=re.I).strip()

        # Check if stream is a YouTube ID or external player URL
        if re.match(r'^[A-Za-z0-9_-]{11}$', stream_url):
            return self.url_result(
                f'https://www.youtube.com/watch?v={stream_url}',
                'Youtube', video_id=stream_url, video_title=title)
        if 'youtube.com/' in stream_url or 'youtu.be/' in stream_url:
            return self.url_result(stream_url, 'Youtube', video_id=video_id, video_title=title)
        if 'dailymotion.com/' in stream_url or 'dai.ly/' in stream_url:
            return self.url_result(stream_url, 'Dailymotion', video_id=video_id, video_title=title)

        headers = {'Referer': 'https://aryplus.tv/', 'Origin': 'https://aryplus.tv'}
        formats, subtitles = [], {}
        if '.m3u8' in stream_url:
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                stream_url, video_id, 'mp4', m3u8_id='hls', fatal=True, headers=headers)
        else:
            formats.append({
                'url': stream_url,
                'format_id': 'http-mp4',
                'ext': 'mp4',
                'http_headers': headers,
            })

        return {
            'id': video_id,
            'title': title,
            'description': clean_html(
                traverse_obj(meta, 'description', 'synopsis', 'storyline')
                or (self._og_search_description(webpage, default=None) if webpage else None)
            ),
            'thumbnail': (
                traverse_obj(meta, 'thumbnail', 'poster', 'image', 'imagePoster', 'mobileImage', expected_type=url_or_none)
                or (self._og_search_thumbnail(webpage, default=None) if webpage else None)
            ),
            'duration': (
                int_or_none(traverse_obj(meta, 'duration', 'length'))
                or parse_duration(traverse_obj(meta, 'duration', 'time', expected_type=str))
            ),
            'episode_number': int_or_none(traverse_obj(meta, 'episodeNumber', 'episode_number', 'epNo')),
            'season_number': int_or_none(traverse_obj(meta, 'seasonNumber', 'season_number', 'season')),
            'series': series_title or traverse_obj(meta, 'seriesTitle', ('seriesId', 'title')),
            'timestamp': unified_timestamp(traverse_obj(meta, 'createdAt', 'created_at', 'publishedAt')),
            'formats': formats,
            'subtitles': subtitles,
            'http_headers': headers,
        }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        vtype = mobj.group('vtype') or '3'
        video_id = mobj.group('id')
        series_id = mobj.group('series_id')
        title_id = mobj.group('title_id')
        active_id = video_id or title_id

        webpage = self._download_webpage(url, active_id)
        unescaped_html = self._unescape(webpage)

        # 1. Check Next.js RSC payload & raw HTML first
        rsc_objs = self._extract_rsc_objects(webpage)
        episodes, streams, matched_meta, series_meta = self._search_json_tree(rsc_objs, active_id)

        if not streams:
            for m3u8 in re.findall(r'https?://[a-zA-Z0-9.-]+/[a-zA-Z0-9._/~%&=\-+:?]+\.m3u8(?:\?[a-zA-Z0-9._/~%&=\-+:]+)?', unescaped_html):
                streams.append((active_id, m3u8, {}))

        # 2. If not embedded in HTML, discover API base & client key from JS bundles and query API
        if not streams and not (title_id and episodes):
            config = self._discover_api_config(webpage, url, active_id)
            episodes, streams, matched_meta, series_meta = self._query_backend_apis(
                config, active_id, series_id, vtype, url)

        series_title = traverse_obj(series_meta, 'title', 'name')

        # 3. Handle /title/<series_id> Playlist
        if title_id and episodes:
            entries = []
            seen_ids = set()
            for idx, ep in enumerate(episodes, 1):
                ep_id = str(traverse_obj(ep, '_id', 'id') or '')
                if not ep_id or ep_id in seen_ids:
                    continue
                seen_ids.add(ep_id)
                ep_title = traverse_obj(ep, 'title', 'name', 'episodeTitle') or f'{series_title or title_id} - Episode {idx}'
                ep_stream = self._find_stream_in_dict(ep)
                if ep_stream:
                    entries.append(self._format_video_result(ep_stream, ep_id, ep, series_title=series_title))
                else:
                    entries.append(self.url_result(
                        f'https://aryplus.tv/video/v2/3/{ep_id}/{title_id}',
                        ie=ARYPlusIE.ie_key(), video_id=ep_id, video_title=ep_title))
            return self.playlist_result(entries, title_id, series_title)

        # 4. Handle Single Video (/video/v2/3/<video_id>/<series_id>)
        target_stream = self._find_stream_in_dict(matched_meta)
        if not target_stream:
            for sid, s_url, s_node in streams:
                if sid == active_id:
                    target_stream = s_url
                    matched_meta = matched_meta or s_node
                    break
            if not target_stream and streams:
                target_stream = streams[0][1]
                matched_meta = matched_meta or streams[0][2]

        if target_stream:
            return self._format_video_result(target_stream, active_id, matched_meta, webpage=webpage, series_title=series_title)

        raise ExtractorError(
            f'Could not resolve stream for {active_id}. Run `yt-dlp -v "{url}"` and check the '
            '"Discovered API bases" debug output, or set ARYPLUS_API_BASE and ARYPLUS_API_KEY.',
            expected=True)
    
