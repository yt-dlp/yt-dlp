from .common import InfoExtractor
from ..utils import traverse_obj, ExtractorError, js_to_json
import re
import json


class TVIPlayerIE(InfoExtractor):
    _VALID_URL = r'https?://tviplayer\.iol\.pt/(?:programa/[^/]+/[0-9a-f]+/(?:video|episodio)|video|episodio|[^/]+/[^/]+|[^/]+)/(?P<id>[0-9A-Za-z]+)(?:[/?#]|$)'
    _TESTS = [{
        'url': 'https://tviplayer.iol.pt/programa/a-protegida/67a63479d34ef72ee441fa79/episodio/t1e120',
        'info_dict': {
            'id': '689683000cf20ac1d5f35341',
            'ext': 'mp4',
            'duration': 1593,
            'title': 'A Protegida - Clarice descobre o que une Óscar a Gonçalo e Mónica',
            'thumbnail': 'https://img.iol.pt/image/id/68971037d34ef72ee44941a6/',
            'season_number': 1,
        },
    }]

    def _real_initialize(self):
        # try to obtain the wmsAuthSign token; if it fails, continue without it
        try:
            self.wms_auth_sign_token = self._download_webpage(
                'https://services.iol.pt/matrix?userId=', 'wmsAuthSign',
                note='Downloading wmsAuthSign token')
        except Exception:
            self.wms_auth_sign_token = None

    def _extract_enclosing_js_object(self, webpage, keyword):
        """
        Find a JS object (balanced braces) that contains keyword (e.g. "videoUrl").
        Returns the text of the object (including braces) or None.
        """
        k = re.search(re.escape(keyword), webpage)
        if not k:
            return None
        pos = k.start()
        # find an opening brace before pos
        start = webpage.rfind('{', 0, pos)
        if start == -1:
            return None
        depth = 0
        for i in range(start, len(webpage)):
            ch = webpage[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return webpage[start:i+1]
        return None

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id or 'tviplayer')

        video_info = None

        # 1) Try to find a literal "const opts = { ... };" block first
        m_opts = re.search(r'const\s+opts\s*=\s*({.*?})\s*;', webpage, flags=re.S)
        if m_opts:
            try:
                opts = self._parse_json(m_opts.group(1), video_id or 'tviplayer', transform_source=js_to_json)
            except Exception:
                opts = None
            if opts:
                # try opts.video[0] or opts itself
                video_info = traverse_obj(opts, ('video', 0)) or opts.get('video') or opts

        # 2) If not found, try to extract any JS object that contains "videoUrl"
        if not video_info:
            obj_text = self._extract_enclosing_js_object(webpage, 'videoUrl')
            if obj_text:
                try:
                    parsed = self._parse_json(obj_text, video_id or 'tviplayer', transform_source=js_to_json)
                except Exception:
                    # fallback: try to json.loads after small cleanup
                    try:
                        cleaned = re.sub(r',\s*([}\]])', r'\1', obj_text).replace("'", '"')
                        parsed = json.loads(cleaned)
                    except Exception:
                        parsed = None
                if parsed:
                    # parsed might be the video object or contain video: [...]
                    if isinstance(parsed, dict):
                        video_info = traverse_obj(parsed, ('video', 0)) or parsed

        # 3) Legacy fallback: jsonData = {...}
        if not video_info:
            try:
                jd = self._search_json(r'jsonData\s*=', webpage, 'json data', video_id)
                if jd:
                    video_info = traverse_obj(jd, ('video', 0)) or jd
            except ExtractorError:
                video_info = None

        # 4) Last resort: search for a direct "videoUrl" key anywhere and build minimal object
        if not video_info:
            m = re.search(r'["\']videoUrl["\']\s*:\s*["\'](https?://[^"\']+)["\']', webpage, flags=re.S)
            if m:
                video_info = {
                    'id': video_id or None,
                    'videoUrl': m.group(1),
                }

        if not video_info:
            raise ExtractorError('Unable to locate video data in webpage', expected=True)

        # Determine id/title/thumbnail/duration/videoUrl
        vid = video_info.get('id') or video_id
        title = video_info.get('title') or self._og_search_title(webpage)
        thumbnail = video_info.get('cover') or video_info.get('thumbnail') or self._og_search_thumbnail(webpage)
        duration = video_info.get('duration')
        try:
            duration = int(duration) if duration is not None else None
        except Exception:
            try:
                duration = int(float(duration))
            except Exception:
                duration = None

        video_url = video_info.get('videoUrl') or video_info.get('url') or video_info.get('video_url')
        if not video_url:
            raise ExtractorError('No video URL found in the page data', expected=True)

        # append token if we have it
        if self.wms_auth_sign_token:
            sep = '&' if '?' in video_url else '?'
            video_url = f'{video_url}{sep}wmsAuthSign={self.wms_auth_sign_token}'

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(video_url, vid or video_id, ext='mp4')

        return {
            'id': vid or video_id,
            'title': title,
            'thumbnail': thumbnail,
            'duration': duration,
            'formats': formats,
            'subtitles': subtitles,
            'season_number': traverse_obj(video_info, ('program', 'seasonNum')),
        }
