# -*- coding: utf-8 -*-
from .common import InfoExtractor
from ..utils import (
    ExtractorError, # Import ExtractorError for raising specific errors
    int_or_none,
    orderedSet,
    parse_duration,
    parse_iso8601,
    parse_qs,
    qualities,
    traverse_obj, # Useful for safely navigating nested dictionaries
    unified_strdate,
    xpath_text,
)
import re # Import re for findall

# --- EuropaIE (Older extractor - unchanged) ---
# This extractor handles older ec.europa.eu/avservices URLs and is likely defunct.
class EuropaIE(InfoExtractor):
    _WORKING = False # Marked as not working
    _VALID_URL = r'https?://ec\.europa\.eu/avservices/(?:video/player|audio/audioDetails)\.cfm\?.*?\bref=(?P<id>[A-Za-z0-9-]+)'
    _TESTS = [{
        'url': 'http://ec.europa.eu/avservices/video/player.cfm?ref=I107758',
        'md5': '574f080699ddd1e19a675b0ddf010371',
        'info_dict': {
            'id': 'I107758', 'ext': 'mp4', 'title': 'TRADE - Wikileaks on TTIP',
            'description': 'NEW  LIVE EC Midday press briefing of 11/08/2015',
            'thumbnail': r're:^https?://.*\.jpg$', 'upload_date': '20150811',
            'duration': 34, 'view_count': int, 'formats': 'mincount:3',
        },
    }, {
        'url': 'http://ec.europa.eu/avservices/video/player.cfm?sitelang=en&ref=I107786',
        'only_matching': True,
    }, {
        'url': 'http://ec.europa.eu/avservices/audio/audioDetails.cfm?ref=I-109295&sitelang=en',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        # (Implementation remains the same as previous versions)
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


# --- EuroParlWebstreamIE (Modified extractor to handle potential site changes) ---
class EuroParlWebstreamIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://multimedia\.europarl\.europa\.eu/
        (?:\w+/)?webstreaming/(?:[\w-]+_)?(?P<id>[\w-]+) # Matches /en/webstreaming/event_id format
    '''
    _TESTS = [{
        # Existing VOD test
        'url': 'https://multimedia.europarl.europa.eu/pl/webstreaming/plenary-session_20220914-0900-PLENARY',
        'info_dict': {
            'id': '62388b15-d85b-4add-99aa-ba12ccf64f0d', 'display_id': '20220914-0900-PLENARY',
            'ext': 'mp4', 'title': 'Plenary session', 'release_timestamp': 1663139069, 'release_date': '20220914',
        },
        'params': {'skip_download': True},
    }, {
        # Test case that previously failed with regex method
        'url': 'https://multimedia.europarl.europa.eu/en/webstreaming/euroscola_20250328-1000-SPECIAL-EUROSCOLA',
        'info_dict': {
            'id': str, # ID might be a string UUID or similar
            'display_id': '20250328-1000-SPECIAL-EUROSCOLA',
            'ext': 'mp4',
            'title': r're:Euroscola', # Expect title containing Euroscola
            'release_timestamp': int, # Expecting a Unix timestamp
            'release_date': '20250328',
            'is_live': bool, # Could be True (if near event time) or False
        },
        'params': {'skip_download': True},
        # Note: This test might fail after 2025-03-28 if the URL becomes invalid or content changes significantly
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url) # Get ID from URL
        webpage = self._download_webpage(url, display_id) # Get page HTML

        # --- Extract Metadata (prioritize Next.js data) ---
        nextjs_data = self._search_nextjs_data(webpage, display_id, default={})
        # Use traverse_obj for safer nested dictionary access
        media_info = traverse_obj(nextjs_data, ('props', 'pageProps', 'mediaItem')) or {}

        # Extract basic info, falling back to display_id if metadata is sparse
        internal_id = media_info.get('id') or display_id
        title = media_info.get('title') or media_info.get('name') or display_id
        release_timestamp = traverse_obj(media_info, ('startDateTime', {parse_iso8601}))
        # Determine live status based on metadata hint, if available
        is_live = media_info.get('mediaSubType') == 'Live'

        hls_url = None # Variable to store the found HLS URL

        # --- Attempt 1: Find direct HLS URL in media_info ---
        # Check common dictionary keys where the full HLS URL might be stored.
        # Add more potential keys here if observed in website data.
        possible_keys = ('hlsUrl', 'streamUrl', 'manifestUrl', 'url', 'playerUrl', 'videoUrl')
        hls_url = traverse_obj(media_info, possible_keys)
        if hls_url and 'm3u8' in hls_url: # Basic check if it looks like an HLS URL
            self.to_screen(f'Found direct HLS URL in metadata: {hls_url}')
        else:
            hls_url = None # Reset if found value wasn't an HLS URL

        # --- Attempt 2: Construct HLS URL from IDs in media_info ---
        if not hls_url:
            self.to_screen('Attempting to construct HLS URL from metadata IDs...')
            # Try to extract relevant IDs. Keys like 'eventId', 'channelId' are common,
            # but might differ. Use traverse_obj to safely get values.
            # 'id' from media_info is often the event ID.
            event_id = traverse_obj(media_info, ('id', 'eventId', 'event_id'))
            # Channel ID might be numeric or a string name.
            channel_id = traverse_obj(media_info, ('channelId', 'channel_id', 'channelName', 'channel'))

            if event_id and channel_id:
                # Construct the URL using the assumed live/default pattern.
                # For archive/VOD, '/index-archive.m3u8?startTime=...&endTime=...' might be needed.
                # This assumes the event is live or uses the default endpoint.
                constructed_url = f'https://live.media.eup.glcloud.eu/hls/live/{event_id}/{channel_id}/index.m3u8'
                hls_url = constructed_url
                self.to_screen(f'Constructed potential HLS URL: {hls_url}')
            else:
                self.to_screen('Could not find sufficient event/channel IDs in metadata to construct URL.')

        # --- Attempt 3: Fallback to regex search on raw webpage (Original Method) ---
        if not hls_url:
            self.to_screen('Could not find or construct HLS URL from metadata, trying webpage regex search...')
            m3u8_url_pattern = r'(https?://[^"]*live\.media\.eup\.glcloud\.eu/hls/live/\d+/[^"]+\.m3u8[^"]*)'
            hls_url = self._search_regex(
                m3u8_url_pattern, webpage, 'm3u8 URL (regex fallback)', default=None, fatal=False)
            if hls_url:
                 self.to_screen(f'Found HLS URL via regex fallback: {hls_url}')
            else:
                # This is where the original "Could not find any .m3u8 link" warning occurred.
                 self.report_warning('Could not find any .m3u8 link via metadata or webpage regex.')

        # --- Process HLS Playlist ---
        if not hls_url:
            # If no URL was found after all attempts, raise an error.
             raise ExtractorError(
                 'No HLS URL (.m3u8) could be found or constructed. The website structure might have changed.',
                 expected=True) # expected=True prevents stack trace for common errors

        # Pass the found HLS URL to the HLS processing function.
        # The _extract_m3u8_formats function usually detects live/VOD automatically.
        # The 'live=is_live' hint can sometimes help but isn't strictly necessary.
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            hls_url, display_id, ext='mp4', live=is_live, fatal=False)

        # Check if HLS processing returned any formats
        if not formats:
             raise ExtractorError(f'HLS manifest found at {hls_url} but yielded no video formats.', expected=True)

        # --- Return Extracted Information ---
        return {
            'id': internal_id,
            'display_id': display_id,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
            'release_timestamp': release_timestamp,
            'is_live': is_live or None, # Use None if not explicitly marked Live
        }
