# coding: utf-8
from .common import InfoExtractor
from ..utils import (
    int_or_none,
    orderedSet,
    parse_duration,
    parse_iso8601,
    parse_qs,
    qualities,
    traverse_obj,
    unified_strdate,
    xpath_text,
    ExtractorError,
    js_to_json,
    urljoin
)
import re
import json
import time
import datetime


class EuropaIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://ec\.europa\.eu/avservices/(?:video/player|audio/audioDetails)\.cfm\?.*?\bref=(?P<id>[A-Za-z0-9-]+)'
    _TESTS = [{
        'url': 'http://ec.europa.eu/avservices/video/player.cfm?ref=I107758',
        'md5': '574f080699ddd1e19a675b0ddf010371',
        'info_dict': {
            'id': 'I107758',
            'ext': 'mp4',
            'title': 'TRADE - Wikileaks on TTIP',
            'description': 'NEW  LIVE EC Midday press briefing of 11/08/2015',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20150811',
            'duration': 34,
            'view_count': int,
            'formats': 'mincount:3',
        },
    }, {
        'url': 'http://ec.europa.eu/avservices/video/player.cfm?sitelang=en&ref=I107786',
        'only_matching': True,
    }, {
        'url': 'http://ec.europa.eu/avservices/audio/audioDetails.cfm?ref=I-109295&sitelang=en',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        playlist = self._download_xml(
            f'http://ec.europa.eu/avservices/video/player/playlist.cfm?ID={video_id}', video_id)

        def get_item(type_, preference):
            items = {}
            for item in playlist.findall(f'./info/{type_}/item'):
                lang, label = xpath_text(item, 'lg', default=None), xpath_text(item, 'label', default=None)
                if lang and label:
                    items[lang] = label.strip()
            for p in preference:
                if items.get(p):
                    return items[p]

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
            if not video_url:
                continue
            lang = xpath_text(file_, './lg')
            formats.append({
                'url': video_url,
                'format_id': lang,
                'format_note': xpath_text(file_, './lglabel'),
                'language_preference': language_preference(lang),
            })

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'upload_date': upload_date,
            'duration': duration,
            'view_count': view_count,
            'formats': formats,
        }


class EuroParlWebstreamIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(?:
            multimedia\.europarl\.europa\.eu/(?:\w+/)?webstreaming/(?:[\w-]+_)?(?P<id>[\w-]+)|
            live\.media\.eup\.glcloud\.eu/hls/live/(?P<live_id>[\w-]+)/(?P<channel>channel-\d+-\w+|[\w-]+)/(?:input/\d+/\d+/[\w-]+/)?(?P<stream_id>[\w.-]+)(?:\.m3u8|/master\.m3u8|\?) # Allow dots and hyphens in stream_id, make .m3u8 optional if query follows
        )
    '''
    _TESTS = [{
        'url': 'https://multimedia.europarl.europa.eu/pl/webstreaming/plenary-session_20220914-0900-PLENARY',
        'info_dict': {
            'id': '20220914-0900-PLENARY',
            'display_id': '20220914-0900-PLENARY',
            'ext': 'mp4',
            'title': 'Plenary session',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # Direct HLS stream URL (archive example similar to user provided)
        'url': 'https://live.media.eup.glcloud.eu/hls/live/2113713/channel-01-stb/input/1/256/p1080___6798871408e31898bdd1a1af/norsk-archive.m3u8?startTime=1743152400&endTime=1743162442',
        'info_dict': {
            'id': 'norsk-archive', # ID derived from filename before query
            'ext': 'mp4',
            'title': 'European Parliament Stream',
        },
        'params': {
            'skip_download': True,
        },
    },{
        # Direct HLS stream URL (live example)
        'url': 'https://live.media.eup.glcloud.eu/hls/live/2113753/channel-07-bxl/index.m3u8',
        'info_dict': {
            'id': 'index',
            'ext': 'mp4',
            'title': 'European Parliament Stream',
        },
        'params': {
            'skip_download': True,
        },
    }]

    # Known CDN endpoints - try these if direct extraction fails
    # Added 2113713 and 2113713-b based on user's M3U8
    ENDPOINTS = ["2113753", "2113713", "2113713-b"]

    # Priority channels based on observed success rates & user M3U8
    # Added channel-01-stb
    PRIORITY_CHANNELS = ["channel-07-bxl", "channel-01-stb", "channel-01-bxl", "channel-10-bxl"]

    # Default stream types/filenames by content type
    # These are used in the *fallback* guessing logic.
    # The complex paths like input/1/256/... seen in the user M3U8 CANNOT be guessed.
    LIVE_STREAM_FILENAMES = ["index.m3u8", "master.m3u8", "playlist.m3u8"]
    ARCHIVE_STREAM_FILENAMES = ["index-archive.m3u8", "norsk-archive.m3u8", "index.m3u8", "master.m3u8"]

    def _extract_direct_url_from_webpage(self, webpage):
        """Extract direct m3u8 URLs from webpage with minimal logging"""
        m3u8_urls = set() # Use a set to avoid duplicates

        # Search patterns for m3u8 URLs
        # Added more flexibility for quotes and paths
        for pattern in [
            r'["\'](https?://live\.media\.eup\.glcloud\.eu/[^"\'\s]+\.m3u8(?:\?[^"\'\s]*)?)["\']',
            r'"url"\s*:\s*"(https?://live\.media\.eup\.glcloud\.eu/[^"]+\.m3u8[^"]*)"',
            # Look for assignments or attributes
            r'=\s*["\'](https?://live\.media\.eup\.glcloud\.eu/[^"\'\s]+\.m3u8[^"\']*)["\']',
            # Look for URLs within JSON-like structures in script tags
            r'"src"\s*:\s*"(https?://live\.media\.eup\.glcloud\.eu/[^"]+\.m3u8[^"]*)"',
            r'"file"\s*:\s*"(https?://live\.media\.eup\.glcloud\.eu/[^"]+\.m3u8[^"]*)"',
        ]:
            matches = re.findall(pattern, webpage)
            for match in matches:
                # Handle potential tuple results from findall if multiple groups exist in regex
                url_match = match if isinstance(match, str) else match[0]
                # Basic sanity check
                if '.m3u8' in url_match and 'live.media.eup.glcloud.eu' in url_match:
                    # Remove any JS string escaping
                    url_match = url_match.replace('\\/', '/').replace('\\\\', '\\')
                    m3u8_urls.add(url_match)

        # Extract from network panel if available (less reliable parsing)
        network_url_match = re.search(r'Request URL:[\s\n]*(?:<[^>]+>)?[\s\n]*(https://live\.media\.eup\.glcloud\.eu/[^\s<]+\.m3u8[^\s<]*)', webpage, re.IGNORECASE)
        if network_url_match:
            url_match = network_url_match.group(1).replace('\\/', '/').replace('\\\\', '\\')
            m3u8_urls.add(url_match)

        self.to_screen(f'Found {len(m3u8_urls)} potential direct M3U8 URLs in webpage')
        return list(m3u8_urls)

    def _extract_title_from_webpage(self, webpage, display_id):
        """Extract the title from the webpage"""
        # Try different patterns to extract the title
        for pattern in [
            r'<meta property="og:title" content="([^"]+)"',
            r'<title>([^<]+)</title>',
            r'<h1[^>]*class="erpl_title-h1"[^>]*>([^<]+)</h1>', # Specific title class
            r'<h1[^>]*>([^<]+)</h1>',
            r'"title"\s*:\s*"([^"]+)"',
        ]:
            title_match = re.search(pattern, webpage)
            if title_match:
                title = title_match.group(1).strip()
                # Clean up common suffixes
                title = re.sub(r'\s*\|\s*European Parliament$', '', title).strip()
                title = re.sub(r'\s*-\s*Multimedia Centre$', '', title).strip()
                if title:
                    return title

        return f"European Parliament Session - {display_id}" # Fallback title

    def _parse_meeting_date(self, display_id):
        """Parse the date from the meeting ID format (YYYYMMDD-HHMM-TYPE)"""
        date_match = re.match(r'(\d{8})-(\d{4})-(.+)', display_id)
        if date_match:
            date_str, time_str, _ = date_match.groups()
            try:
                # Parse the date components
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                hour = int(time_str[:2])
                minute = int(time_str[2:4])

                # Create timestamps with a generous window (e.g., 3 hours before, 6 hours after)
                # This helps catch streams that start slightly early or run long
                meeting_dt = datetime.datetime(year, month, day, hour, minute, tzinfo=datetime.timezone.utc) # Assume UTC
                start_dt = meeting_dt - datetime.timedelta(hours=3)
                end_dt = meeting_dt + datetime.timedelta(hours=6) # Increased end window

                # Convert to Unix timestamps
                start_ts = int(start_dt.timestamp())
                end_ts = int(end_dt.timestamp())

                self.to_screen(f'Parsed date {date_str}-{time_str}. Using archive time window: {start_ts} to {end_ts}')
                return start_ts, end_ts

            except (ValueError, OverflowError) as e:
                 self.to_screen(f'Error parsing date from display_id "{display_id}": {e}')
                 pass # Fall through to fallback

        # Fallback to a recent window if parsing fails or ID format is different
        self.to_screen(f'Could not parse specific date from "{display_id}". Using generic recent time window.')
        now = int(time.time())
        start_time = now - (24 * 3600)  # 24 hours ago (might be too short for older archives)
        end_time = now + (1 * 3600)      # 1 hour in the future (for live/recent)
        return start_time, end_time

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        # Get potential IDs from the regex match groups
        display_id = mobj.group('id')
        live_id = mobj.group('live_id')
        stream_id = mobj.group('stream_id')
        channel = mobj.group('channel')

        # Use the most specific ID available
        video_id = display_id or stream_id or live_id or channel

        # Handle direct HLS URLs first (most reliable if provided)
        if live_id and (stream_id or channel):
            # Clean up stream_id (remove query parameters for use as info dict id)
            clean_stream_id = stream_id.split('?')[0] if stream_id and '?' in stream_id else stream_id
            # If stream_id is missing but channel exists, use channel as part of the id
            final_id = clean_stream_id or channel or 'unknown_stream'
            # Remove potential .m3u8 suffix for cleaner ID
            if final_id.endswith('.m3u8'):
                 final_id = final_id[:-5]

            self.to_screen(f'Processing direct HLS URL: {url}')
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                url, final_id, 'mp4', m3u8_id='hls', fatal=False, quiet=True) # Don't fail hard if extraction issues

            if not formats:
                 self.report_warning(f'Could not extract any formats from the direct M3U8 URL: {url}')
                 # Optionally, you could attempt webpage download here as a fallback, but direct URLs should ideally work
                 # raise ExtractorError('Failed to extract formats from direct HLS URL.', expected=True)

            return {
                'id': final_id,
                'title': 'European Parliament Stream', # Generic title for direct URLs
                'formats': formats or [],
                'subtitles': subtitles or {},
                'is_live': '?startTime=' not in url and 'archive' not in url.lower(), # Basic guess based on URL
            }

        # --- Fallback for multimedia.europarl.europa.eu URLs ---
        if not display_id: # Should have display_id if it's not a direct HLS URL
             raise ExtractorError('Failed to identify video ID from URL.')

        self.to_screen(f'Processing webpage URL: {url}')
        webpage = self._download_webpage(url, display_id)

        # Check for live indicators more reliably
        # Look for common live indicators in JS, classes, or text
        is_live = bool(re.search(
            r'(?:isLive\s*:\s*true|"liveStatus"\s*:\s*"live"|player-live|Live now|En direct|IN DIRETTA|EN VIVO|NA ŻYWO)',
            webpage,
            re.IGNORECASE))
        self.to_screen(f'Detected as live: {is_live}')

        # Extract title
        title = self._extract_title_from_webpage(webpage, display_id)

        # *** Strategy 1: Extract direct URLs from webpage (Preferred) ***
        direct_urls = self._extract_direct_url_from_webpage(webpage)
        formats = []
        subtitles = {}

        if direct_urls:
            self.to_screen(f'Attempting extraction from {len(direct_urls)} direct URLs found in webpage...')
            for m3u8_url in direct_urls:
                # Clean stream ID from URL for format identification
                m3u8_stream_id = m3u8_url.split('/')[-1].split('?')[0]
                if m3u8_stream_id.endswith('.m3u8'):
                    m3u8_stream_id = m3u8_stream_id[:-5]

                try:
                    fmt, subs = self._extract_m3u8_formats_and_subtitles(
                        m3u8_url, display_id, 'mp4', m3u8_id=f'hls-{m3u8_stream_id}', fatal=False) # Don't stop on first error

                    if fmt:
                        self.to_screen(f'Successfully extracted formats from: {m3u8_url}')
                        formats.extend(fmt)
                        self._merge_subtitles(subs, target=subtitles)
                        # If we found formats, we are likely done, return immediately
                        return {
                            'id': display_id,
                            'display_id': display_id,
                            'title': title,
                            'formats': formats,
                            'subtitles': subtitles,
                            'is_live': is_live or ('?startTime=' not in m3u8_url and 'archive' not in m3u8_url.lower()), # Refine live status based on URL
                        }
                    else:
                        self.to_screen(f'No formats found in: {m3u8_url}')
                except ExtractorError as e:
                    self.to_screen(f'Error extracting from direct URL {m3u8_url}: {e}')
                    pass # Try the next direct URL
        else:
            self.to_screen('No direct M3U8 URLs found in webpage.')


        # *** Strategy 2: Fallback - Guessing URLs (Less Reliable, esp. for complex paths) ***
        self.to_screen('Attempting fallback URL guessing strategy (may not work for all streams)...')

        # Parse timestamps for archive retrieval (or use a window for live/unknown)
        # Always parse, even if live, as it might be a recently finished live event
        start_timestamp, end_timestamp = self._parse_meeting_date(display_id)

        # Use appropriate stream filenames for the content type
        stream_filenames = self.LIVE_STREAM_FILENAMES if is_live else self.ARCHIVE_STREAM_FILENAMES

        # Try combinations with updated endpoints and channels
        for endpoint in self.ENDPOINTS:
            for channel_to_try in self.PRIORITY_CHANNELS:
                for filename in stream_filenames:
                    base_url = f"https://live.media.eup.glcloud.eu/hls/live/{endpoint}/{channel_to_try}/{filename}"

                    # Determine if timestamps should be added
                    # Add timestamps if it's explicitly not live, OR if the filename suggests archive,
                    # OR if start/end timestamps were successfully parsed from the ID.
                    # Avoid timestamps for clearly live filenames unless forced by non-live status.
                    use_timestamps = (
                        (not is_live or 'archive' in filename.lower())
                        and start_timestamp and end_timestamp
                    )

                    test_url = f"{base_url}?startTime={start_timestamp}&endTime={end_timestamp}" if use_timestamps else base_url

                    try:
                        self.to_screen(f'Trying guessed URL: {test_url}')
                        fmt, subs = self._extract_m3u8_formats_and_subtitles(
                            test_url, display_id, 'mp4', m3u8_id=f'hls-guessed-{channel_to_try}-{filename.replace(".m3u8", "")}', fatal=False)

                        if fmt:
                            self.to_screen(f'Success with guessed URL: {test_url}')
                            formats.extend(fmt)
                            self._merge_subtitles(subs, target=subtitles)
                            # Found a working combination
                            return {
                                'id': display_id,
                                'display_id': display_id,
                                'title': title,
                                'formats': formats,
                                'subtitles': subtitles,
                                'is_live': not use_timestamps, # If we used timestamps, assume not live
                            }
                        else:
                            self.to_screen(f'No formats found in guessed URL: {test_url}')

                    except ExtractorError as e:
                        # Log error lightly, as many guesses are expected to fail
                        self.to_screen(f'Guessed URL failed: {test_url} ({e})')
                        pass # Continue trying other combinations

        # *** If all strategies fail ***
        self.to_screen('All extraction strategies failed.')

        # Provide helpful error with suggestions
        error_message = (
            f"Could not extract stream URL for {display_id or url}. "
            "The stream may be old, expired, or use an unsupported format.\n"
            f"Live status detected: {is_live}\n"
            "Common issues:\n"
            "- The specific URL structure (especially for archives like 'norsk-archive.m3u8' with deep paths) might not be guessable.\n"
            "- The event might not be available via the standard CDN endpoints/channels.\n"
            "If you know the direct `.m3u8` URL, try using it with yt-dlp directly.\n"
            "Example (using parsed times, adjust if needed):\n"
        )
        if start_timestamp and end_timestamp:
             example_url = f"https://live.media.eup.glcloud.eu/hls/live/{self.ENDPOINTS[0]}/{self.PRIORITY_CHANNELS[0]}/index-archive.m3u8?startTime={start_timestamp}&endTime={end_timestamp}"
             error_message += f'yt-dlp "{example_url}"'
        else:
             example_url = f"https://live.media.eup.glcloud.eu/hls/live/{self.ENDPOINTS[0]}/{self.PRIORITY_CHANNELS[0]}/index.m3u8"
             error_message += f'yt-dlp "{example_url}"'


        raise ExtractorError(error_message, expected=True)
