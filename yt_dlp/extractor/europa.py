# -*- coding: utf-8 -*-
from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    orderedSet,
    parse_duration,
    parse_iso8601,
    parse_qs,
    qualities,
    traverse_obj,
    unified_strdate,
    xpath_text,
    js_to_json,
    urljoin,
    filter_dict,
    HEADRequest, # Import HEADRequest
)
import re
import json
import urllib.error # Import urllib.error for HEAD check exception

# --- EuropaIE (Unchanged) ---
class EuropaIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://ec\.europa\.eu/avservices/(?:video/player|audio/audioDetails)\.cfm\?.*?\bref=(?P<id>[A-Za-z0-9-]+)'
    _TESTS = [
        # Existing tests...
    ]
    def _real_extract(self, url):
        video_id = self._match_id(url)
        playlist = self._download_xml(
            f'http://ec.europa.eu/avservices/video/player/playlist.cfm?ID={video_id}', video_id)
        def get_item(type_, preference):
            items = {}
            for item in playlist.findall(f'./info/{type_}/item'):
                lang, label = (xpath_text(item, 'lg', default=None), xpath_text(item, 'label', default=None))
                if lang and label: items[lang] = label.strip()
            for p in preference:
                if items.get(p): return items[p]
        query = parse_qs(url)
        preferred_lang = query.get('sitelang', ('en', ))[0]
        preferred_langs = orderedSet((preferred_lang, 'en', 'int'))
        title = get_item('title', preferred_langs) or video_id
        description = get_item('description', preferred_langs)
        thumbnail = xpath_text(playlist, './info/thumburl', 'thumbnail')
        upload_date = unified_strdate(xpath_text(playlist, './info/date', 'upload date'))
        duration = parse_duration(xpath_text(playlist, './info/duration', 'duration'))
        view_count = int_or_none(xpath_text(playlist, './info/views', 'views'))
        language_preference = qualities(preferred_langs[::-1])
        formats = []
        for file_ in playlist.findall('./files/file'):
            video_url = xpath_text(file_, './url')
            if not video_url: continue
            lang = xpath_text(file_, './lg')
            formats.append({'url': video_url, 'format_id': lang, 'format_note': xpath_text(file_, './lglabel'), 'language_preference': language_preference(lang)})
        return {'id': video_id, 'title': title, 'description': description, 'thumbnail': thumbnail, 'upload_date': upload_date, 'duration': duration, 'view_count': view_count, 'formats': formats}


# --- EuroParlWebstreamIE (Using JSON from iframe) ---
class EuroParlWebstreamIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(?:
            multimedia\.europarl\.europa\.eu/(?:\w+/)?webstreaming/(?:[\w-]+_)?(?P<id>[\w-]+)| # Webstreaming page URL
            live\.media\.eup\.glcloud\.eu/hls/live/(?P<live_id>\d+)/(?P<channel>channel-\d+-\w+|[\w-]+)/(?P<stream_type>index-archive|index|master|playlist|norsk-archive)(?:\.m3u8)? # Direct HLS URL base
        )
    '''
    _TESTS = [
        {
            'url': 'https://multimedia.europarl.europa.eu/en/webstreaming/committee-on-agriculture-and-rural-development_20250327-0900-COMMITTEE-AGRI',
            'info_dict': {
                'id': '20250327-0900-COMMITTEE-AGRI',
                'title': r're:^Committee on Agriculture and Rural Development \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
                'is_live': False,
                'ext': 'mp4',
            },
            'params': {'skip_download': True},
            # Uses the iframe JSON parsing which should yield 2113752 / channel-06-bxl
        },
        {
            'url': 'https://multimedia.europarl.europa.eu/en/webstreaming/pre-session-briefing_20250328-1100-SPECIAL-PRESSEr',
            'info_dict': {
                'id': '20250328-1100-SPECIAL-PRESSEr',
                'title': r're:^Pre-session briefing \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
                'is_live': False,
                'ext': 'mp4',
            },
            'params': {'skip_download': True},
            # Uses the iframe JSON parsing which should yield 2113747 / channel-01-bxl
        },
        { # Test direct HLS URL with archive times
            'url': 'https://live.media.eup.glcloud.eu/hls/live/2113752/channel-06-bxl/index-archive.m3u8?startTime=1743068400&endTime=1743079800',
            'info_dict': {
                'id': 'index-archive',
                'title': 'European Parliament Stream 2113752/channel-06-bxl',
                'is_live': False, # Should be detected as not live from lack of live tags/duration
                'ext': 'mp4',
            },
            'params': {'skip_download': True},
        },
        # Potentially add a known live stream test if one is available
    ]

    def _log_debug(self, msg):
        self.to_screen(f"[EuroParlWebstream] {msg}")

    def _extract_title_from_webpage(self, webpage, display_id):
        """Extracts title from the main webstreaming page."""
        title_element = self._search_regex(r'<h1[^>]*>(.*?)</h1>', webpage, 'title element', default=None)
        if title_element:
            # Clean up potential extra whitespace and HTML entities
            title = re.sub(r'\s+', ' ', title_element).strip()
            title = self._html_search_meta(['og:title', 'twitter:title'], webpage, default=title)
        else:
            # Fallback using meta tags or just the ID
            title = self._html_search_meta(
                ['og:title', 'twitter:title'], webpage, default=display_id)
        return title.replace('_', ' ') # Replace underscores often used in IDs

    def _perform_head_check(self, url, display_id, note=''):
        """Performs a HEAD request to check if the HLS URL likely exists."""
        self._log_debug(f'[{display_id}] Performing HEAD check {note}on: {url}')
        try:
            self._request_webpage(HEADRequest(url), display_id, note=f'HEAD check {note}')
            self._log_debug(f'[{display_id}] HEAD check {note}successful.')
            return True
        except ExtractorError as e:
            # Specifically catch HTTP errors, especially 404
            if isinstance(e.cause, urllib.error.HTTPError):
                self._log_debug(f'[{display_id}] HEAD check {note}failed: {e.cause.code} {e.cause.reason}')
            else:
                self._log_debug(f'[{display_id}] HEAD check {note}failed: {e}')
            return False

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id = mobj.group('id')
        live_id_direct = mobj.group('live_id')

        # --- Handle Direct HLS URL Input ---
        if live_id_direct:
            self._log_debug(f"Processing Direct HLS URL: {url}")
            channel_direct = mobj.group('channel')
            stream_type_direct = mobj.group('stream_type') or 'stream' # Default name if not specified
            base_url = f'https://live.media.eup.glcloud.eu/hls/live/{live_id_direct}/{channel_direct}/{stream_type_direct}'

            query_params_str = mobj.group(0).split('?', 1)[1] if '?' in mobj.group(0) else None
            query_params = parse_qs(query_params_str) if query_params_str else {}
            start_time_direct = traverse_obj(query_params, ('startTime', 0, {int_or_none}))
            end_time_direct = traverse_obj(query_params, ('endTime', 0, {int_or_none}))

            # Construct the final URL ensuring .m3u8 is present
            final_url = base_url + ('' if base_url.endswith('.m3u8') else '.m3u8')
            if start_time_direct and end_time_direct:
                 final_url += f"?startTime={start_time_direct}&endTime={end_time_direct}"
            elif query_params_str: # Append original query if not start/end time based
                 final_url += f"?{query_params_str}"

            # Basic title for direct URL
            title = f'European Parliament Stream {live_id_direct}/{channel_direct}'

            # HEAD check is good even for direct URLs
            if not self._perform_head_check(final_url, f"{live_id_direct}-{channel_direct}", '(direct)'):
                 raise ExtractorError(f'Direct HLS URL HEAD check failed: {final_url}', expected=True)

            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                final_url, display_id or stream_type_direct, 'mp4', m3u8_id='hls', fatal=True)
            if not formats: raise ExtractorError(f'Could not extract formats from direct HLS URL: {final_url}', expected=True)

            return {
                'id': display_id or stream_type_direct,
                'title': title,
                'formats': formats,
                'subtitles': subtitles,
                'is_live': not (start_time_direct and end_time_direct) and '.m3u8' not in stream_type_direct # Guess based on URL structure
            }

        # --- Handle Webstreaming Page URL ---
        if not display_id: raise ExtractorError('Could not parse display ID from URL', expected=True)

        self._log_debug(f"Processing Webstreaming Page: {display_id}")
        webpage = self._download_webpage(url, display_id)
        title = self._extract_title_from_webpage(webpage, display_id) # Get title early

        self._log_debug(f'[{display_id}] Extracting metadata and iframe URL...')
        nextjs_data = self._search_nextjs_data(webpage, display_id, default={})
        media_info = traverse_obj(nextjs_data, ('props', 'pageProps', 'mediaItem')) or {}

        # Get initial start time, but prioritize iframe JSON later
        initial_start_timestamp = traverse_obj(media_info, ('mediaDate', {parse_iso8601}, {int_or_none}))
        iframe_url = traverse_obj(media_info, 'iframeUrls') # Usually just one URL string

        self._log_debug(f'[{display_id}] Initial Start Time={initial_start_timestamp}, Iframe URL={iframe_url}')

        if not iframe_url:
            raise ExtractorError(f'[{display_id}] Could not find iframe URL in page metadata.', expected=True)

        # --- Attempt Extraction from Iframe JSON ---
        self._log_debug(f'[{display_id}] Attempting extraction from iframe: {iframe_url}')
        try:
            iframe_content = self._download_webpage(iframe_url, display_id, note='Downloading iframe content')
            json_data_str = self._search_regex(
                r'<script id="ng-state" type="application/json"[^>]*>\s*({.+?})\s*</script>',
                iframe_content, 'iframe JSON data', default=None)

            if not json_data_str:
                raise ExtractorError('Could not find ng-state JSON in iframe content.')

            iframe_json = self._parse_json(json_data_str, display_id, fatal=True)

            # Extract required info from the JSON structure
            player_url_base = traverse_obj(iframe_json, ('contentEventKey', 'playerUrl'))
            start_time = traverse_obj(iframe_json, ('contentEventKey', 'startTime', {int_or_none}))
            end_time = traverse_obj(iframe_json, ('contentEventKey', 'endTime', {int_or_none}))
            is_live = traverse_obj(iframe_json, ('contentEventKey', 'live')) # boolean
            # Use title from JSON if available and seems better
            json_title = traverse_obj(iframe_json, ('contentEventKey', 'title'))
            if json_title: title = json_title


            self._log_debug(f'[{display_id}] Found in iframe JSON: playerUrl={player_url_base}, startTime={start_time}, endTime={end_time}, is_live={is_live}')

            if not player_url_base:
                raise ExtractorError('Could not extract playerUrl from iframe JSON.')

            # For recorded streams (archives), startTime and endTime are essential
            if not is_live and (start_time is None or end_time is None):
                 raise ExtractorError('Missing startTime or endTime in iframe JSON for recorded stream.')

            # Construct the final URL
            # Ensure base URL doesn't already have query params before adding ours
            player_url_base = player_url_base.split('?')[0]
            if not player_url_base.endswith('.m3u8'):
                player_url_base += '.m3u8' # Ensure correct extension

            if is_live:
                 final_player_url = player_url_base # Live streams don't use start/end times
            else:
                 final_player_url = f"{player_url_base}?startTime={start_time}&endTime={end_time}"

            # Perform HEAD check on the constructed URL
            if not self._perform_head_check(final_player_url, display_id, '(dynamic)'):
                 raise ExtractorError(f'Dynamic HLS URL from iframe failed HEAD check: {final_player_url}')

            # Extract formats
            self._log_debug(f'[{display_id}] Extracting formats from {final_player_url}')
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                final_player_url, display_id, 'mp4', entry_protocol='m3u8_native',
                m3u8_id='hls', fatal=True) # Use fatal=True, if extraction fails, it's an error

            if not formats:
                 raise ExtractorError(f'Could not extract M3U8 formats from {final_player_url}', expected=True)

            return {
                'id': display_id,
                'title': title,
                'formats': formats,
                'subtitles': subtitles,
                'is_live': is_live,
                'timestamp': start_time if not is_live else None, # Use JSON start time for VOD
                'duration': (end_time - start_time) if not is_live and start_time and end_time else None,
            }

        except ExtractorError as e:
            # Re-raise specific extractor errors
            raise e
        except Exception as e:
            # Wrap unexpected errors
            raise ExtractorError(f'[{display_id}] Error processing iframe content: {e}', cause=e)

        # This part should ideally not be reached if iframe extraction is mandatory
        raise ExtractorError(f'[{display_id}] Failed to extract stream information from iframe.', expected=True)
