import json
import re

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    parse_duration,
    traverse_obj,
    try_get,
    unified_timestamp,
    url_or_none,
)


class ARYPlusIE(InfoExtractor):
    IE_NAME = 'aryplus'
    IE_DESC = 'ARY Plus (aryplus.tv / ARY ZAP)'
    _VALID_URL = r'https?://(?:www\.)?aryplus\.tv/(?P<type>title|watch|live|episode|movie)/(?P<id>[0-9a-fA-F]{24})(?:[/?#&]|$)'

    _TESTS = [{
        # Drama Series (Dar-E-Nijaat) - 24-char hex ObjectId
        'url': 'https://aryplus.tv/title/6a57868b5bf57c474cc00a50',
        'info_dict': {
            'id': '6a57868b5bf57c474cc00a50',
            'title': 'Dar-E-Nijaat',
        },
        'playlist_mincount': 1,
    }, {
        # Drama Series (Betiyaan)
        'url': 'https://aryplus.tv/title/677293014b7252e04f377ab0',
        'only_matching': True,
    }, {
        # TV Show (Jeeto Pakistan)
        'url': 'https://aryplus.tv/title/669a5959398ab0adb46b6344',
        'only_matching': True,
    }]

    # Known backend API endpoints used by ARY Plus / ARY ZAP
    _API_ENDPOINTS = (
        'https://aryplus.tv/api/v1/content/{id}',
        'https://api.aryplus.tv/api/v1/series/{id}',
        'https://api.aryzap.com/api/series/{id}',
        'https://api.aryzap.com/api/v1/vod/{id}',
        'https://node.aryzap.com/api/series/{id}',
        'https://node.aryzap.com/api/episode/{id}',
    )

    def _extract_nextjs_rsc_json(self, webpage):
        """Extract JSON objects embedded inside Next.js App Router self.__next_f.push() scripts."""
        results = []
        for match in re.finditer(r'self\.__next_f\.push\(\s*\[\s*\d+\s*,\s*("(?:\\.|[^"\\])*")\s*\]\s*\)', webpage):
            try:
                unquoted = json.loads(match.group(1))
            except Exception:
                continue
            for line in unquoted.splitlines():
                 _, _, payload = line.partition(':')
                payload = payload.strip()
                if payload.startswith(('{', '[')):
                    try:
                        results.append(json.loads(payload))
                    except Exception:
                        pass
        return results

    def _find_media_objects(self, data):
        """Recursively search parsed JSON trees for title metadata, episode arrays, or stream URLs."""
        found_meta = {}
        found_episodes = []
        found_streams = []

        def _walk(obj):
            if isinstance(obj, dict):
                # Detect stream URLs on the current dict
                for k in ('streamUrl', 'stream_url', 'videoUrl', 'video_url', 'hlsUrl', 'hls', 'url', 'file', 'manifest', 'link'):
                    val = obj.get(k)
                    if isinstance(val, str) and ('.m3u8' in val or 'aryzap.com' in val or '.mp4' in val):
                        found_streams.append(val)

                # Detect if this dict represents a Series / Title container
                if ('title' in obj or 'name' in obj) and any(k in obj for k in ('episodes', 'episode', 'seasons', 'cast', 'genres', 'description', 'storyline')):
                    if not found_meta.get('title'):
                        found_meta.update(obj)

                # Detect episode arrays
                for ep_key in ('episodes', 'episodeList', 'videos', 'items', 'data'):
                    ep_val = obj.get(ep_key)
                    if isinstance(ep_val, list) and ep_val and isinstance(ep_val[0], dict):
                        if any(k in ep_val[0] for k in ('episodeNumber', 'episode_number', 'streamUrl', 'videoUrl', 'title', 'duration', '_id')):
                            found_episodes.extend(ep_val)

                for v in obj.values():
                    _walk(v)
            elif isinstance(obj, list):
                for item in obj:
                    _walk(item)

        _walk(data)
        return found_meta, found_episodes, found_streams

    def _parse_stream_target(self, stream_url, video_id, title, metadata=None):
        """Build a yt-dlp info_dict from a resolved stream URL (HLS, MP4, or external ID)."""
        metadata = metadata or {}
        headers = {
            'Referer': 'https://aryplus.tv/',
            'Origin': 'https://aryplus.tv',
        }

        # Check if the backend returned a YouTube video ID or URL
        if re.match(r'^[A-Za-z0-9_-]{11}$', stream_url):
            return self.url_result(f'https://www.youtube.com/watch?v={stream_url}', 'Youtube', video_id=stream_url, video_title=title)
        if 'youtube.com/' in stream_url or 'youtu.be/' in stream_url:
            return self.url_result(stream_url, 'Youtube', video_id=video_id, video_title=title)
        if 'dailymotion.com/' in stream_url or 'dai.ly/' in stream_url:
            return self.url_result(stream_url, 'Dailymotion', video_id=video_id, video_title=title)

        formats, subtitles = [], {}
        if '.m3u8' in stream_url:
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                stream_url, video_id, 'mp4', m3u8_id='hls', fatal=False, headers=headers)
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
            'description': clean_html(traverse_obj(metadata, 'description', 'synopsis', 'storyline', 'plot')),
            'thumbnail': traverse_obj(
                metadata, 'thumbnail', 'poster', 'image', 'imagePoster', 'cover',
                expected_type=url_or_none),
            'duration': (
                int_or_none(traverse_obj(metadata, 'duration', 'length'))
                or parse_duration(traverse_obj(metadata, 'duration', 'time', expected_type=str))
            ),
            'episode_number': int_or_none(traverse_obj(metadata, 'episodeNumber', 'episode_number', 'episode', 'epNo')),
            'season_number': int_or_none(traverse_obj(metadata, 'seasonNumber', 'season_number', 'season')),
            'series': traverse_obj(metadata, 'seriesTitle', 'series_name'),
            'timestamp': unified_timestamp(traverse_obj(metadata, 'createdAt', 'created_at', 'publishedAt', 'releaseDate')),
            'formats': formats,
            'subtitles': subtitles,
            'http_headers': headers,
        }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        content_id = mobj.group('id')
        url_type = mobj.group('type')

        webpage = self._download_webpage(url, content_id)

        # 1. Extract OpenGraph / HTML fallback metadata
        page_title = (
            self._og_search_title(webpage, default=None)
            or self._html_extract_title(webpage, default=None)
            or content_id
        )
        page_title = re.sub(r'^\s*Watch\s+|\s*\|\s*ARY Plus.*$', '', page_title, flags=re.I).strip()
        page_desc = self._og_search_description(webpage, default=None)
        page_thumb = self._og_search_thumbnail(webpage, default=None)

        # 2. Gather JSON payloads from __NEXT_DATA__, Next.js RSC chunks, or API endpoints
        json_trees = []

        next_data = self._search_nextjs_data(webpage, content_id, fatal=False)
        if next_data:
            json_trees.append(next_data)

        rsc_data = self._extract_nextjs_rsc_json(webpage)
        if rsc_data:
            json_trees.extend(rsc_data)

        meta, episodes, direct_streams = self._find_media_objects(json_trees)

        # 3. If HTML hydration didn't contain stream URLs, query backend API endpoints
        if not episodes and not direct_streams:
            api_headers = {
                'Accept': 'application/json',
                'Origin': 'https://aryplus.tv',
                'Referer': url,
            }
            for ep_template in self._API_ENDPOINTS:
                api_url = ep_template.format(id=content_id)
                api_json = self._download_json(
                    api_url, content_id, note=f'Checking API {api_url}',
                    headers=api_headers, fatal=False)
                if api_json:
                    m, eps, strms = self._find_media_objects(api_json)
                    meta = meta or m
                    episodes.extend(eps)
                    direct_streams.extend(strms)
                    if episodes or direct_streams:
                        break

        # 4. Regex scan webpage for direct vod.aryzap.com / .m3u8 URLs if still empty
        if not episodes and not direct_streams:
            direct_streams = re.findall(
                r'https?://(?:[a-zA-Z0-9-]+\.)?(?:aryzap\.com|aryplus\.tv)/[^"\'\s<>]+\.m3u8(?:\?[^"\'\s<>]+)?',
                webpage)

        series_title = traverse_obj(meta, 'title', 'name') or page_title

        # 5. If this is a multi-episode Series (/title/<id>), return a Playlist
        if episodes and url_type == 'title':
            entries = []
            seen_ids = set()
            for idx, ep in enumerate(episodes, 1):
                ep_id = str(traverse_obj(ep, '_id', 'id') or f'{content_id}_ep{idx}')
                if ep_id in seen_ids:
                    continue
                seen_ids.add(ep_id)

                ep_title = traverse_obj(ep, 'title', 'name', 'episodeTitle') or f'{series_title} - Episode {idx}'
                ep_stream = traverse_obj(
                    ep, 'streamUrl', 'stream_url', 'videoUrl', 'video_url',
                    'hlsUrl', 'hls', 'file', 'url', 'link', 'youtubeId',
                )

                if ep_stream:
                    ep['seriesTitle'] = series_title
                    entries.append(self._parse_stream_target(ep_stream, ep_id, ep_title, ep))
                elif re.match(r'^[0-9a-fA-F]{24}$', ep_id) and ep_id != content_id:
                    # Point to the individual watch/episode route if stream requires per-episode fetch
                    entries.append(self.url_result(
                        f'https://aryplus.tv/watch/{ep_id}',
                        ie=ARYPlusIE.ie_key(), video_id=ep_id, video_title=ep_title))

            if entries:
                return self.playlist_result(
                    entries, content_id, series_title,
                    description=traverse_obj(meta, 'description', 'storyline') or page_desc)

        # 6. Single video / movie / live stream extraction
        if direct_streams:
            info = self._parse_stream_target(direct_streams[0], content_id, series_title, meta)
            info.setdefault('description', page_desc)
            info.setdefault('thumbnail', page_thumb)
            info['is_live'] = (url_type == 'live') or bool(traverse_obj(meta, 'isLive', 'is_live'))
            return info

        raise ExtractorError(
            f'Could not find a playable .m3u8 stream for {content_id}. '
            'If aryplus.tv requires an active session token to return the vod.aryzap.com URL, '
            'pass your browser cookies using: --cookies-from-browser chrome',
            expected=True)
              
