import html
import json
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    parse_iso8601,
    traverse_obj,
)

_VTT_TIMESTAMP_RE = re.compile(r'(?:(\d+):)?(\d{2}):(\d{2}\.\d{3})')


def _vtt_time_to_seconds(ts):
    if not ts:
        return None
    m = _VTT_TIMESTAMP_RE.match(ts)
    if not m:
        try:
            return float(ts)
        except Exception:
            return None
    hours = int(m.group(1)) if m.group(1) else 0
    minutes = int(m.group(2))
    seconds = float(m.group(3))
    return hours * 3600 + minutes * 60 + seconds


def parse_vtt_chapters(vtt_text):
    """
    Minimal WebVTT chapter parser.
    Returns list of dicts: {'start_time': float, 'end_time': float, 'title': str}
    """
    chapters = []
    if not vtt_text:
        return chapters
    lines = vtt_text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    i = 0
    if i < len(lines) and lines[i].strip().upper().startswith('WEBVTT'):
        i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1

    while i < len(lines):
        if lines[i].strip() and '-->' not in lines[i]:
            i += 1
            if i >= len(lines):
                break
        if i < len(lines) and '-->' in lines[i]:
            timing = lines[i].strip()
            parts = timing.split('-->')
            start_ts = parts[0].strip()
            end_ts = parts[1].split()[0].strip() if len(parts) > 1 else None
            start = _vtt_time_to_seconds(start_ts)
            end = _vtt_time_to_seconds(end_ts) if end_ts else None
            i += 1
            text_lines = []
            while i < len(lines) and lines[i].strip():
                text_lines.append(lines[i])
                i += 1
            title = html.unescape(' '.join(l.strip() for l in text_lines)).strip()
            if start is not None:
                chapters.append({
                    'start_time': start,
                    'end_time': end,
                    'title': title or None,
                })
        else:
            i += 1
    return chapters


class BeaconTvIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?beacon\.tv/content/(?P<id>[\w-]+)'

    _TESTS = [{
        'url': 'https://beacon.tv/content/welcome-to-beacon',
        'md5': 'b3f5932d437f288e662f10f3bfc5bd04',
        'info_dict': {
            'id': 'welcome-to-beacon',
            'ext': 'mp4',
            'upload_date': '20240509',
            'description': 'md5:ea2bd32e71acf3f9fca6937412cc3563',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/I4CkkEvN/poster.jpg?width=720',
            'title': 'Your home for Critical Role!',
            'timestamp': 1715227200,
            'duration': 105.494,
        },
    }, {
        'url': 'https://beacon.tv/content/re-slayers-take-trailer',
        'md5': 'd879b091485dbed2245094c8152afd89',
        'info_dict': {
            'id': 're-slayers-take-trailer',
            'ext': 'mp4',
            'title': 'The Re-Slayer’s Take | Official Trailer',
            'timestamp': 1715189040,
            'upload_date': '20240508',
            'duration': 53.249,
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/PW5ApIw3/poster.jpg?width=720',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        content_data = traverse_obj(self._search_nextjs_data(webpage, video_id), (
            'props', 'pageProps', '__APOLLO_STATE__',
            lambda k, v: k.startswith('Content:') and v['slug'] == video_id, any))
        if not content_data:
            raise ExtractorError('Failed to extract content data')

        jwplayer_data = traverse_obj(content_data, (
            (('contentVideo', 'video', 'videoData'),
             ('contentPodcast', 'podcast', 'audioData')), {json.loads}, {dict}, any))
        if not jwplayer_data:
            if content_data.get('contentType') not in ('videoPodcast', 'video', 'podcast'):
                raise ExtractorError('Content is not a video/podcast', expected=True)
            if traverse_obj(content_data, ('contentTier', '__ref')) != 'MemberTier:65b258d178f89be87b4dc0a4':
                self.raise_login_required('This video/podcast is for members only')
            raise ExtractorError('Failed to extract content')

        info = {**self._parse_jwplayer_data(jwplayer_data, video_id),
                **traverse_obj(content_data, {
                    'title': ('title', {str}),
                    'description': ('description', {str}),
                    'timestamp': ('publishedAt', {parse_iso8601}),
                })}

        chapter_url = None

        def pick_from_track_obj(t):
            file_url = (t.get('file') or t.get('src') or t.get('url') or '').strip()
            kind = (t.get('kind') or '').lower()
            label = (t.get('label') or t.get('name') or '').lower()
            if not file_url or not file_url.lower().endswith('.vtt'):
                return None
            if kind == 'chapters' or 'chapter' in label or 'chapter' in file_url.lower() or 'chapters' in file_url.lower():
                return file_url
            return None

        tracks = None
        if isinstance(jwplayer_data, dict):
            tracks = jwplayer_data.get('tracks') or jwplayer_data.get('textTracks') or None
        if isinstance(tracks, list):
            for t in tracks:
                candidate = pick_from_track_obj(t)
                if candidate:
                    chapter_url = candidate
                    break

        if not chapter_url:
            subs = info.get('subtitles') if isinstance(info, dict) else None
            if isinstance(subs, dict):
                for _lang, tracks_list in subs.items():
                    if not isinstance(tracks_list, list):
                        continue
                    for t in tracks_list:
                        candidate = pick_from_track_obj(t)
                        if candidate:
                            chapter_url = candidate
                            break
                    if chapter_url:
                        break

        def scan_for_tracks(obj):
            if isinstance(obj, dict):
                if 'tracks' in obj and isinstance(obj['tracks'], list):
                    for t in obj['tracks']:
                        if isinstance(t, dict):
                            candidate = pick_from_track_obj(t)
                            if candidate:
                                return candidate
                for _k, v in obj.items():
                    if isinstance(v, str):
                        if ('{' in v and '}' in v):
                            try:
                                parsed = json.loads(v)
                                res = scan_for_tracks(parsed)
                                if res:
                                    return res
                            except Exception:
                                pass
                    else:
                        res = scan_for_tracks(v)
                        if res:
                            return res
            elif isinstance(obj, list):
                for item in obj:
                    res = scan_for_tracks(item)
                    if res:
                        return res
            return None

        if not chapter_url:
            chapter_url = scan_for_tracks(content_data)

        if chapter_url:
            try:
                vtt_text = self._download_webpage(chapter_url, video_id, note='Downloading chapter VTT', fatal=False)
                if vtt_text:
                    chapters = parse_vtt_chapters(vtt_text)
                    if chapters:
                        if not info.get('chapters'):
                            info['chapters'] = chapters
            except Exception:
                self.report_warning('Failed to download/parse chapter VTT', video_id)

        return info
