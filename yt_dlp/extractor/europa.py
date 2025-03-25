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
            live\.media\.eup\.glcloud\.eu/hls/live/(?P<live_id>\d+)/(?:channel-\d+-\w+|[\w-]+)/(?:input/\d+/\d+/[\w-]+/)?(?P<stream_id>[\w-]+)(?:\.m3u8|/master\.m3u8)
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
        # New URL format for direct HLS streams
        'url': 'https://live.media.eup.glcloud.eu/hls/live/2113753/channel-07-bxl/index-archive.m3u8?startTime=1742828675&endTime=1742832870',
        'info_dict': {
            'id': 'index-archive',
            'ext': 'mp4',
            'title': 'European Parliament Stream',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://multimedia.europarl.europa.eu/en/webstreaming/special-committee-on-housing-crisis-in-european-union-ordinary-meeting_20250324-1500-COMMITTEE-HOUS',
        'info_dict': {
            'id': '20250324-1500-COMMITTEE-HOUS',
            'display_id': '20250324-1500-COMMITTEE-HOUS',
            'ext': 'mp4',
            'title': 'Special committee on the Housing Crisis in the European Union Ordinary meeting',
        },
        'params': {
            'skip_download': True,
        },
    }]

    # Known working stream IDs (in order of likely success)
    KNOWN_STREAM_IDS = [
        "index-archive",
        "norsk-archive",
    ]

    # Known CDN endpoints (in order of likely success)
    KNOWN_ENDPOINTS = [
        "2113753",  # This appears to be the main endpoint
        "2113749",
        "2113750",
        "2113751",
        "2113752",
        "2113754",
    ]

    # Prioritized channel list based on observations (channel-07-bxl is often used)
    PRIORITIZED_CHANNELS = [
        "channel-07-bxl",  # Most common based on examples
        "channel-03-bxl",  # Also seen in examples
        "channel-01-bxl",
        "channel-02-bxl",
        "channel-04-bxl",
        "channel-05-bxl",
        "channel-06-bxl",
        "channel-08-bxl",
        "channel-09-bxl",
        "channel-10-bxl",
    ]

    def _parse_meeting_id(self, display_id):
        """Extract date and time information from the meeting ID."""
        # Format: YYYYMMDD-HHMM-COMMITTEE-TYPE
        date_match = re.match(r'(\d{8})-(\d{4})-(.+)', display_id)
        if date_match:
            date_str, time_str, meeting_type = date_match.groups()
            try:
                # Parse the date and time
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                hour = int(time_str[:2])
                minute = int(time_str[2:4])
                
                # Create datetime object
                meeting_dt = datetime.datetime(year, month, day, hour, minute)
                
                # Calculate a reasonable meeting duration (2 hours by default)
                end_dt = meeting_dt + datetime.timedelta(hours=2)
                
                return {
                    'date': date_str,
                    'time': time_str,
                    'type': meeting_type,
                    'start_dt': meeting_dt,
                    'end_dt': end_dt,
                    'start_timestamp': int(meeting_dt.timestamp()),
                    'end_timestamp': int(end_dt.timestamp()),
                }
            except (ValueError, OverflowError) as e:
                self.report_warning(f"Failed to parse meeting date/time: {e}")
        
        # If we can't parse the date/time, use the current time minus 24 hours to now
        current_time = int(time.time())
        return {
            'start_timestamp': current_time - 86400,  # 24 hours ago
            'end_timestamp': current_time,
        }

    def _find_m3u8_in_webpage(self, webpage):
        """Look for m3u8 URLs directly in the webpage."""
        # Look for direct m3u8 URLs with timestamps
        m3u8_matches = re.findall(
            r'[\'"]((https?://live\.media\.eup\.glcloud\.eu/[^"\']+\.m3u8(?:\?[^\'"]*)?)[\'"])',
            webpage
        )
        if m3u8_matches:
            return [url[0].replace('\\/', '/').replace('\\\\', '\\') for url in m3u8_matches]
        
        return []

    def _extract_title_from_webpage(self, webpage):
        """Extract the title from the webpage."""
        title = self._html_search_regex(
            r'<meta property="og:title" content="([^"]+)"',
            webpage, 'title', default=None) or \
            self._html_search_regex(
            r'<title>([^<]+)</title>',
            webpage, 'title', default='European Parliament Stream')
        
        # Clean up title
        title = re.sub(r'\s*\|\s*European Parliament$', '', title).strip()
        return title

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id = mobj.group('id')
        live_id = mobj.group('live_id')
        stream_id = mobj.group('stream_id')

        # Handle direct HLS stream URLs
        if live_id and stream_id:
            # Strip any query parameters from stream_id
            if '?' in stream_id:
                stream_id = stream_id.split('?')[0]
            
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                url, stream_id, 'mp4', m3u8_id='hls', fatal=False)

            return {
                'id': stream_id,
                'title': 'European Parliament Stream',
                'formats': formats,
                'subtitles': subtitles,
            }

        # If we're dealing with a europarl.europa.eu URL, download the webpage first
        webpage = self._download_webpage(url, display_id)
        title = self._extract_title_from_webpage(webpage)
        
        # First, look for m3u8 URLs directly in the page
        direct_urls = self._find_m3u8_in_webpage(webpage)
        if direct_urls:
            self.to_screen(f"Found {len(direct_urls)} potential stream URLs in webpage")
            for m3u8_url in direct_urls:
                try:
                    self.to_screen(f"Trying direct URL: {m3u8_url}")
                    formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                        m3u8_url, display_id, 'mp4', m3u8_id='hls', fatal=False)
                    
                    if formats:
                        return {
                            'id': display_id,
                            'display_id': display_id,
                            'title': title,
                            'formats': formats,
                            'subtitles': subtitles,
                        }
                except ExtractorError as e:
                    self.report_warning(f"Failed with direct URL {m3u8_url}: {e}")
        
        # If no direct URLs found, parse the meeting ID and generate likely timestamps
        meeting_info = self._parse_meeting_id(display_id)
        start_timestamp = meeting_info.get('start_timestamp')
        end_timestamp = meeting_info.get('end_timestamp')
        
        self.to_screen(f"Generated timestamps for meeting: start={start_timestamp}, end={end_timestamp}")
        
        # Try a variety of possibilities, starting with the most likely combinations
        formats = []
        subtitles = {}
        working_url = None
        
        # Main endpoint with prioritized channels
        for channel in self.PRIORITIZED_CHANNELS:
            for stream_type in self.KNOWN_STREAM_IDS:
                candidate_url = f"https://live.media.eup.glcloud.eu/hls/live/2113753/{channel}/{stream_type}.m3u8?startTime={start_timestamp}&endTime={end_timestamp}"
                self.to_screen(f"Trying URL: {candidate_url}")
                
                try:
                    fmt, subs = self._extract_m3u8_formats_and_subtitles(
                        candidate_url, display_id, 'mp4', m3u8_id='hls', fatal=False)
                    
                    if fmt:
                        formats.extend(fmt)
                        self._merge_subtitles(subs, target=subtitles)
                        working_url = candidate_url
                        self.to_screen(f"Success! Found working URL: {working_url}")
                        
                        return {
                            'id': display_id,
                            'display_id': display_id,
                            'title': title,
                            'formats': formats,
                            'subtitles': subtitles,
                        }
                except ExtractorError as e:
                    self.report_warning(f"Failed with URL {candidate_url}: {e}")
        
        # If main endpoint + prioritized channels didn't work, try other endpoints
        for endpoint in self.KNOWN_ENDPOINTS[1:]:  # Skip the first one as we already tried it
            for channel in self.PRIORITIZED_CHANNELS[:3]:  # Only try the top 3 channels for other endpoints
                for stream_type in self.KNOWN_STREAM_IDS:
                    candidate_url = f"https://live.media.eup.glcloud.eu/hls/live/{endpoint}/{channel}/{stream_type}.m3u8?startTime={start_timestamp}&endTime={end_timestamp}"
                    self.to_screen(f"Trying URL: {candidate_url}")
                    
                    try:
                        fmt, subs = self._extract_m3u8_formats_and_subtitles(
                            candidate_url, display_id, 'mp4', m3u8_id='hls', fatal=False)
                        
                        if fmt:
                            formats.extend(fmt)
                            self._merge_subtitles(subs, target=subtitles)
                            working_url = candidate_url
                            self.to_screen(f"Success! Found working URL: {working_url}")
                            
                            return {
                                'id': display_id,
                                'display_id': display_id,
                                'title': title,
                                'formats': formats,
                                'subtitles': subtitles,
                            }
                    except ExtractorError as e:
                        self.report_warning(f"Failed with URL {candidate_url}: {e}")
        
        # If we've reached here, we need to give a helpful error message
        parsed_date = f"{meeting_info.get('date', 'unknown-date')}"
        parsed_time = f"{meeting_info.get('time', 'unknown-time')}"
        
        # Provide the most likely URL for manual use
        suggested_url = f"https://live.media.eup.glcloud.eu/hls/live/2113753/channel-07-bxl/index-archive.m3u8?startTime={start_timestamp}&endTime={end_timestamp}"
        
        raise ExtractorError(
            f"Could not extract stream URL for {display_id}. The European Parliament stream may not be available.\n"
            f"Attempted to find a stream for date: {parsed_date}, time: {parsed_time}.\n"
            f"Try using yt-dlp directly with: yt-dlp \"{suggested_url}\"",
            expected=True
        )
