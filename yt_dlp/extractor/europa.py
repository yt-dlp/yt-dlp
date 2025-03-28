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
# Removed unused 're' import, added 'urllib.parse' for potential future use if needed
# but not strictly required for current modification.

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


# --- EuroParlWebstreamIE (Modified extractor to handle VOD/Archive streams correctly) ---
class EuroParlWebstreamIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://multimedia\.europarl\.europa\.eu/
        (?:\w+/)?webstreaming/(?:[\w-]+_)?(?P<id>[\w-]+) # Matches /en/webstreaming/event_id format
    '''
    _TESTS = [{
        # Existing VOD test (Should now work better if metadata is consistent)
        'url': 'https://multimedia.europarl.europa.eu/pl/webstreaming/plenary-session_20220914-0900-PLENARY',
        'info_dict': {
            'id': '62388b15-d85b-4add-99aa-ba12ccf64f0d', 'display_id': '20220914-0900-PLENARY',
            'ext': 'mp4', 'title': 'Plenary session', 'release_timestamp': 1663139069, 'release_date': '20220914',
        },
        'params': {'skip_download': True},
    }, {
        # Test case likely representing an archive/VOD (based on previous context)
        'url': 'https://multimedia.europarl.europa.eu/en/webstreaming/euroscola_20250328-1000-SPECIAL-EUROSCOLA',
        'info_dict': {
            'id': str, # ID might be a string UUID or similar
            'display_id': '20250328-1000-SPECIAL-EUROSCOLA',
            'ext': 'mp4',
            'title': r're:Euroscola', # Expect title containing Euroscola
            'release_timestamp': int, # Expecting a Unix timestamp (start time)
            'release_date': '20250328',
            'is_live': False, # Should be detected as not live
        },
        'params': {'skip_download': True},
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

        # Extract start and end timestamps, if available
        # parse_iso8601 typically returns a float/int timestamp
        start_timestamp = traverse_obj(media_info, ('startDateTime', {parse_iso8601}, {int_or_none}))
        end_timestamp = traverse_obj(media_info, ('endDateTime', {parse_iso8601}, {int_or_none}))
        release_timestamp = start_timestamp # Use start time as the release timestamp

        # Determine live status based on metadata hint, if available
        # Treat as not live if 'Live' subtype isn't explicitly present
        is_live = media_info.get('mediaSubType') == 'Live'

        hls_url = None # Variable to store the found HLS URL

        # --- Attempt 1: Find direct HLS URL in media_info ---
        # Check common dictionary keys where the full HLS URL might be stored.
        possible_keys = ('hlsUrl', 'streamUrl', 'manifestUrl', 'url', 'playerUrl', 'videoUrl')
        hls_url = traverse_obj(media_info, possible_keys)
        if hls_url and 'm3u8' in hls_url: # Basic check if it looks like an HLS URL
            self.to_screen(f'Found direct HLS URL in metadata: {hls_url}')
            # Check if it's an archive URL but missing time params - might need correction later if it fails
            if not is_live and 'index-archive.m3u8' in hls_url and '?startTime=' not in hls_url and start_timestamp and end_timestamp:
                 self.to_screen('Direct URL looks like archive but missing time params, attempting to add them.')
                 hls_url = f'{hls_url.split("?")[0]}?startTime={start_timestamp}&endTime={end_timestamp}'
                 self.to_screen(f'Corrected direct HLS URL: {hls_url}')

        else:
            hls_url = None # Reset if found value wasn't an HLS URL or needs construction

        # --- Attempt 2: Construct HLS URL from IDs and Times in media_info ---
        if not hls_url:
            self.to_screen('Attempting to construct HLS URL from metadata...')
            event_id = traverse_obj(media_info, ('id', 'eventId', 'event_id'))
            channel_id = traverse_obj(media_info, ('channelId', 'channel_id', 'channelName', 'channel'))

            if event_id and channel_id:
                if not is_live and start_timestamp and end_timestamp:
                    # Construct ARCHIVE/VOD URL with time parameters
                    constructed_url = (
                        f'https://live.media.eup.glcloud.eu/hls/live/{event_id}/{channel_id}/'
                        f'index-archive.m3u8?startTime={start_timestamp}&endTime={end_timestamp}'
                    )
                    hls_url = constructed_url
                    self.to_screen(f'Constructed Archive HLS URL: {hls_url}')
                elif is_live:
                     # Construct LIVE URL (basic pattern, might need adjustments)
                    constructed_url = f'https://live.media.eup.glcloud.eu/hls/live/{event_id}/{channel_id}/index.m3u8'
                    hls_url = constructed_url
                    self.to_screen(f'Constructed Live HLS URL: {hls_url}')
                else:
                    self.to_screen('Could not construct URL: Missing live status or timestamps for archive.')
            else:
                self.to_screen('Could not construct URL: Missing event or channel ID in metadata.')

        # --- Attempt 3: Fallback to regex search on raw webpage (Original Method) ---
        if not hls_url:
            self.to_screen('Could not find or construct HLS URL from metadata, trying webpage regex search...')
            # Updated regex to potentially capture archive URLs with parameters, but prioritize construction
            m3u8_url_pattern = r'(https?://[^"\']*\.media\.eup\.glcloud\.eu/hls/live/\d+/[^"\']+\.m3u8[^"\']*)'
            hls_url = self._search_regex(
                m3u8_url_pattern, webpage, 'm3u8 URL (regex fallback)', default=None, fatal=False)
            if hls_url:
                self.to_screen(f'Found HLS URL via regex fallback: {hls_url}')
                # If regex found an archive URL without params, try adding them as a last resort
                if not is_live and 'index-archive.m3u8' in hls_url and '?startTime=' not in hls_url and start_timestamp and end_timestamp:
                    self.to_screen('Regex URL looks like archive but missing time params, attempting to add them.')
                    hls_url = f'{hls_url.split("?")[0]}?startTime={start_timestamp}&endTime={end_timestamp}'
                    self.to_screen(f'Corrected regex HLS URL: {hls_url}')
            else:
                self.report_warning('Could not find any .m3u8 link via metadata or webpage regex.')

        # --- Process HLS Playlist ---
        if not hls_url:
            raise ExtractorError(
                'No HLS URL (.m3u8) could be found or constructed. The website structure might have changed.',
                expected=True)

        # Pass the final HLS URL to the processing function
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            hls_url, display_id, ext='mp4', live=is_live, fatal=False) # fatal=False allows checking empty formats

        # Check if HLS processing returned any formats
        if not formats:
             # Try again, forcing VOD interpretation if it was marked live but failed
             if is_live:
                 self.to_screen('Live HLS processing failed, attempting again as VOD...')
                 formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                     hls_url, display_id, ext='mp4', live=False, fatal=False)

             # If still no formats, raise error
             if not formats:
                 raise ExtractorError(f'HLS manifest found at {hls_url} but yielded no video formats, even after retry.', expected=True)


        # --- Return Extracted Information ---
        return {
            'id': internal_id,
            'display_id': display_id,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
            'release_timestamp': release_timestamp,
            'is_live': is_live, # Keep original detected live status
        }
