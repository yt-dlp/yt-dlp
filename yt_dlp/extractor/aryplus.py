import json
import os
import re

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

    # Matches:
    # - https://aryplus.tv/video/v2/3/<video_id>/<series_id>
    # - https://aryplus.tv/video/v2/3/<video_id>
    # - https://aryplus.tv/video/api/v2/3/<video_id>
    # - https://aryplus.tv/title/<series_id>
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?aryplus\.tv/
        (?:
            video/(?:api/)?v2/(?P<vtype>\d+)/(?P<id>[0-9a-fA-F]{24})(?:/(?P<series_id>[0-9a-fA-F]{24}))? |
            (?P<route>title|watch|live)/(?P<title_id>[0-9a-fA-F]{24})
        )
        (?:[/?#&]|$)
    '''

    _TESTS = [{
        # Direct v2 episode player URL (Dar-E-Nijaat)
        'url': 'https://aryplus.tv/video/v2/3/6aa569699ce8620de08e66f1/6a57868b5bf57c474cc00a50',
        'info_dict': {
            'id': '6aa569699ce8620de08e66f1',
            'ext': 'mp4',
            'title': str,
        },
    }, {
        # Direct v2 episode player URL (Tamasha Season 5)
        'url': 'https://aryplus.tv/video/v2/3/6aac3ae8aba453733d851a7a/6a2da7d7088916f961f22e52',
        'only_matching': True,
    }, {
        # Direct v2 API link passed into yt-dlp
        'url': 'https://aryplus.tv/video/api/v2/3/6aa569699ce8620de08e66f1',
        'only_matching': True,
    }, {
        # Series / Title page (Main Tera)
        'url': 'https://aryplus.tv/title/6a4bbae15bf57c474cab6d0a',
        'only_matching': True,
    }]

    _STREAM_KEYS = (
        'streamUrl', 'stream_url', 'videoUrl', 'video_url', 'videoSource',
        'hlsUrl', 'hls_url', 'hls', 'cdnLink', 'cdn_link', 'playbackUrl',
        'playback_url', 'manifestUrl', 'file', 'source', 'url', 'link',
    )

    def _get_api_headers(self, referer_url):
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://aryplus.tv',
            'Referer': referer_url,
        }
        api_key = os.environ.get('ARYPLUS_API_KEY')
        if api_key:
            headers['x-api-key'] = api_key
            headers['Authorization'] = f'Bearer {api_key}' if not api_key.startswith('Bearer ') else api_key
        return headers

    def _call_v2_api(self, vtype, target_id, referer_url, extra_id=None):
        """Query aryplus.tv/video/api/v2/<vtype>/<id> endpoints."""
        base = os.environ.get('ARYPLUS_API_BASE', 'https://aryplus.tv').rstrip('/')
        headers = self._get_api_headers(referer_url)

        candidate_urls = [
            f'{base}/video/api/v2/{vtype}/{target_id}',
        ]
        if extra_id:
            candidate_urls.extend([
                f'{base}/video/api/v2/{vtype}/{target_id}/{extra_id}',
                f'{base}/video/api/v2/{vtype}/{extra_id}/{target_id}',
                f'{base}/video/api/v2/{vtype}/{extra_id}',
            ])

        for api_url in candidate_urls:
            data = self._download_json(
                api_url, target_id,
                note=f'Fetching v2 API: {api_url}',
                headers=headers, fatal=False)
            if data:
                return data
        return None

    def _extract_nextjs_rsc_json(self, webpage):
        """Parse JSON chunks from Next.js App Router self.__next_f.push() scripts."""
        objs = []
        for match in re.finditer(r'self\.__next_f\.push\(\s*\[\s*\d+\s*,\s*("(?:\\.|[^"\\])*")\s*\]\s*\)', webpage):
            try:
                raw_chunk = json.loads(match.group(1))
            except Exception:
                continue
            for line in raw_chunk.splitlines():
                _, sep, payload = line.partition(':')
                if not sep:
                    continue
                payload = payload.strip()
                if payload.startswith(('{', '[')):
                    try:
                        objs.append(json.loads(payload))
                    except Exception:
                        pass
        return objs

    def _find_stream_url(self, obj):
        """Find a playable .m3u8, .mp4, or external stream URL inside a dict."""
        if not isinstance(obj, dict):
            return None
        for key in self._STREAM_KEYS:
            val = obj.get(key)
            if isinstance(val, str) and val.strip():
                if any(x in val for x in ('.m3u8', '.mp4', 'aryzap.com', 'aryplus.tv', 'youtube.com', 'youtu.be', 'dailymotion.com')):
                    return val.strip()
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        nested = self._find_stream_url(item)
                        if nested:
                            return nested
                    elif isinstance(item, str) and ('.m3u8' in item or '.mp4' in item):
                        return item.strip()
            elif isinstance(val, dict):
                nested = self._find_stream_url(val)
                if nested:
                    return nested
        return None

    def _collect_nodes(self, root):
        """Walk arbitrary JSON response to collect episode dicts, stream URLs, and series metadata."""
        episodes = []
        streams = []
        dicts_by_id = {}
        series_meta = {}

        def _walk(node):
            if isinstance(node, dict):
                node_id = str(node.get('_id') or node.get('id') or '')
                if re.match(r'^[0-9a-fA-F]{24}$', node_id):
                    dicts_by_id.setdefault(node_id, {}).update(node)

                if traverse_obj(node, 'is_drm', 'drm', 'widevineUrl', 'fairplayUrl'):
                    self.report_drm(node_id or 'aryplus')

                stream = self._find_stream_url(node)
                if stream:
                    streams.append((node_id, stream, node))

                # Check if node holds a list of episodes
                for list_key in ('episode', 'episodes', 'episodeList', 'videos', 'data', 'items', 'results'):
                    arr = node.get(list_key)
                    if isinstance(arr, list) and arr and isinstance(arr[0], dict):
                        for item in arr:
                            if isinstance(item, dict) and (
                                self._find_stream_url(item)
                                or any(k in item for k in ('episodeNumber', 'episode_number', 'epNo', 'title', 'name', '_id'))
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
        return dicts_by_id, episodes, streams, series_meta

    def _build_video_info(self, stream_url, video_id, meta, fallback_title=None, series_title=None):
        meta = meta or {}
        title = (
            traverse_obj(meta, 'title', 'name', 'episodeTitle', 'episode_title')
            or fallback_title
            or video_id
        )
        headers = {
            'Referer': 'https://aryplus.tv/',
            'Origin': 'https://aryplus.tv',
        }

        # Handle YouTube / Dailymotion embeds if returned by API
        if re.match(r'^[A-Za-z0-9_-]{11}$', stream_url):
            return self.url_result(
                f'https://www.youtube.com/watch?v={stream_url}',
                'Youtube', video_id=stream_url, video_title=title)
        if 'youtube.com/' in stream_url or 'youtu.be/' in stream_url:
            return self.url_result(stream_url, 'Youtube', video_id=video_id, video_title=title)
        if 'dailymotion.com/' in stream_url or 'dai.ly/' in stream_url:
            return self.url_result(stream_url, 'Dailymotion', video_id=video_id, video_title=title)

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
            'description': clean_html(traverse_obj(meta, 'description', 'synopsis', 'storyline', 'plot')),
            'thumbnail': traverse_obj(
                meta, 'thumbnail', 'poster', 'image', 'imagePoster', 'cover', 'mobileImage',
                expected_type=url_or_none),
            'duration': (
                int_or_none(traverse_obj(meta, 'duration', 'length'))
                or parse_duration(traverse_obj(meta, 'duration', 'time', expected_type=str))
            ),
            'episode_number': int_or_none(traverse_obj(meta, 'episodeNumber', 'episode_number', 'epNo', 'episode')),
            'season_number': int_or_none(traverse_obj(meta, 'seasonNumber', 'season_number', 'season')),
            'series': series_title or traverse_obj(meta, 'seriesTitle', 'series_name', ('seriesId', 'title')),
            'timestamp': unified_timestamp(traverse_obj(meta, 'createdAt', 'created_at', 'publishedAt', 'releaseDate')),
            'formats': formats,
            'subtitles': subtitles,
            'http_headers': headers,
        }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        vtype = mobj.group('vtype') or '3'
        video_id = mobj.group('id')
        series_id = mobj.group('series_id')
        route = mobj.group('route')
        title_id = mobj.group('title_id')

        # ------------------------------------------------------------------
        # CASE 1: /video/v2/<vtype>/<video_id>(/<series_id>) or /video/api/v2/...
        # ------------------------------------------------------------------
        if video_id:
            page_url = f'https://aryplus.tv/video/v2/{vtype}/{video_id}' + (f'/{series_id}' if series_id else '')
            api_data = self._call_v2_api(vtype, video_id, page_url, extra_id=series_id)

            webpage = ''
            if not api_data:
                webpage = self._download_webpage(page_url, video_id, fatal=False) or ''
                rsc_chunks = self._extract_nextjs_rsc_json(webpage)
                next_data = self._search_nextjs_data(webpage, video_id, fatal=False)
                api_data = [x for x in ([next_data] + rsc_chunks) if x]

            dicts_by_id, episodes, streams, series_meta = self._collect_nodes(api_data)

            # 1a. Exact match for video_id in collected nodes
            target_meta = dicts_by_id.get(video_id) or {}
            target_stream = self._find_stream_url(target_meta)

            # 1b. If not on dicts_by_id directly, check streams list
            if not target_stream:
                for sid, s_url, s_node in streams:
                    if sid == video_id:
                        target_stream = s_url
                        target_meta = s_node
                        break
                if not target_stream and streams:
                    target_stream = streams[0][1]
                    target_meta = target_meta or streams[0][2]

            # 1c. Last-resort regex scan on the player HTML for vod.aryzap.com / .m3u8
            if not target_stream:
                if not webpage:
                    webpage = self._download_webpage(page_url, video_id, fatal=False) or ''
                m3u8_matches = re.findall(
                    r'https?://(?:[a-zA-Z0-9-]+\.)?(?:aryzap\.com|aryplus\.tv)/[^"\'\s<>\\]+\.m3u8(?:\?[^"\'\s<>\\]+)?',
                    webpage)
                if m3u8_matches:
                    target_stream = m3u8_matches[0]

            if not target_stream:
                raise ExtractorError(
                    f'No stream URL found for video {video_id} (v2/{vtype}). '
                    'Try passing browser cookies with --cookies-from-browser chrome',
                    expected=True)

            series_title = traverse_obj(series_meta, 'title', 'name')
            return self._build_video_info(target_stream, video_id, target_meta, series_title=series_title)

        # ------------------------------------------------------------------
        # CASE 2: /title/<title_id> (Series / Movie Landing Page)
        # ------------------------------------------------------------------
        webpage = self._download_webpage(url, title_id, fatal=False) or ''
        page_title = (
            self._og_search_title(webpage, default=None)
            or self._html_extract_title(webpage, default=None)
            or title_id
        )
        page_title = re.sub(r'^\s*Watch\s+|\s*\|\s*ARY Plus.*$', '', page_title, flags=re.I).strip()

        # Try v2 API for series/episodes (type 3, then 1 and 2) + page RSC payload
        payloads = []
        for candidate_vtype in ('3', '1', '2'):
            data = self._call_v2_api(candidate_vtype, title_id, url)
            if data:
                payloads.append(data)
                break

        next_data = self._search_nextjs_data(webpage, title_id, fatal=False)
        if next_data:
            payloads.append(next_data)
        payloads.extend(self._extract_nextjs_rsc_json(webpage))

        dicts_by_id, episodes, streams, series_meta = self._collect_nodes(payloads)
        series_title = traverse_obj(series_meta, 'title', 'name') or page_title

        if episodes:
            entries = []
            seen = set()
            for idx, ep in enumerate(episodes, 1):
                ep_id = str(traverse_obj(ep, '_id', 'id') or '')
                if not ep_id or ep_id in seen:
                    continue
                seen.add(ep_id)

                ep_title = traverse_obj(ep, 'title', 'name', 'episodeTitle') or f'{series_title} - Episode {idx}'
                ep_stream = self._find_stream_url(ep)
                if ep_stream:
                    entries.append(self._build_video_info(ep_stream, ep_id, ep, fallback_title=ep_title, series_title=series_title))
                elif re.match(r'^[0-9a-fA-F]{24}$', ep_id):
                    entries.append(self.url_result(
                        f'https://aryplus.tv/video/v2/3/{ep_id}/{title_id}',
                        ie=ARYPlusIE.ie_key(), video_id=ep_id, video_title=ep_title))

            if entries:
                return self.playlist_result(
                    entries, title_id, series_title,
                    description=clean_html(traverse_obj(series_meta, 'description', 'storyline')))

        if streams:
            return self._build_video_info(streams[0][1], title_id, streams[0][2], fallback_title=series_title)

        raise ExtractorError(
            f'Could not extract episodes or stream from {url}. '
            'Use a direct video link (https://aryplus.tv/video/v2/3/<ep_id>/<series_id>) or pass --cookies-from-browser chrome.',
            expected=True)
            
