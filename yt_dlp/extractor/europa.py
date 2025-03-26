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
            live\.media\.eup\.glcloud\.eu/hls/live/(?P<live_id>\d+)/(?P<channel>channel-\d+-\w+|[\w-]+)/(?:input/\d+/\d+/[\w-]+/)?(?P<stream_id>[\w-]+)(?:\.m3u8|/master\.m3u8)
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
        # Direct HLS stream URL
        'url': 'https://live.media.eup.glcloud.eu/hls/live/2113753/channel-07-bxl/index-archive.m3u8?startTime=1742828675&endTime=1742832870',
        'info_dict': {
            'id': 'index-archive',
            'ext': 'mp4',
            'title': 'European Parliament Stream',
        },
        'params': {
            'skip_download': True,
        },
    }]

    # Main CDN endpoint - primarily target this instead of trying multiple
    MAIN_ENDPOINT = "2113753"
    
    # Priority channels based on observed success rates
    PRIORITY_CHANNELS = ["channel-07-bxl", "channel-01-bxl", "channel-10-bxl"]
    
    # Default stream types by content type
    LIVE_STREAM_TYPES = ["index", "master", "playlist"]
    ARCHIVE_STREAM_TYPES = ["index-archive", "norsk-archive", "index", "master"]

    def _extract_direct_url_from_webpage(self, webpage):
        """Extract direct m3u8 URLs from webpage with minimal logging"""
        m3u8_urls = []
        
        # Search patterns for m3u8 URLs
        for pattern in [
            r'["\'](https?://live\.media\.eup\.glcloud\.eu/[^"\'\s]+\.m3u8(?:\?[^"\']*)?)["\']',
            r'"url"\s*:\s*"(https?://live\.media\.eup\.glcloud\.eu/[^"]+\.m3u8[^"]*)"',
            r'=[^\n]*["\'](https?://live\.media\.eup\.glcloud\.eu/[^"\'\s]+\.m3u8[^"\']*)["\']',
        ]:
            matches = re.findall(pattern, webpage)
            if matches:
                m3u8_urls.extend(matches)
        
        # Clean up URLs
        clean_urls = []
        for url in m3u8_urls:
            # Remove any JS string escaping
            url = url.replace('\\/', '/').replace('\\\\', '\\')
            clean_urls.append(url)
            
        # Extract from network panel if available
        network_url_match = re.search(r'Request URL:[\s\n]*(?:<[^>]+>)?[\s\n]*(https://live\.media\.eup\.glcloud\.eu/[^\s<]+\.m3u8[^\s<]*)', webpage, re.IGNORECASE)
        if network_url_match:
            clean_urls.append(network_url_match.group(1))
            
        return clean_urls

    def _extract_title_from_webpage(self, webpage, display_id):
        """Extract the title from the webpage"""
        # Try different patterns to extract the title
        for pattern in [
            r'<meta property="og:title" content="([^"]+)"',
            r'<title>([^<]+)</title>',
            r'<h1[^>]*>([^<]+)</h1>',
            r'"title"\s*:\s*"([^"]+)"',
        ]:
            title_match = re.search(pattern, webpage)
            if title_match:
                title = title_match.group(1).strip()
                # Clean up common suffixes
                title = re.sub(r'\s*\|\s*European Parliament$', '', title)
                title = re.sub(r'\s*-\s*Multimedia Centre$', '', title)
                return title
                
        return f"European Parliament Session - {display_id}"

    def _parse_meeting_date(self, display_id):
        """Parse the date from the meeting ID format (YYYYMMDD-HHMM-TYPE)"""
        date_match = re.match(r'(\d{8})-(\d{4})-(.+)', display_id)
        if date_match:
            date_str, time_str, meeting_type = date_match.groups()
            try:
                # Parse the date components
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                hour = int(time_str[:2])
                minute = int(time_str[2:4])
                
                # Create timestamps with a generous window (3 hours before and after)
                meeting_dt = datetime.datetime(year, month, day, hour, minute)
                start_dt = meeting_dt - datetime.timedelta(hours=3)
                end_dt = meeting_dt + datetime.timedelta(hours=6)
                
                # Convert to timestamps
                start_ts = int(start_dt.timestamp())
                end_ts = int(end_dt.timestamp())
                
                return start_ts, end_ts
                
            except (ValueError, OverflowError):
                pass
        
        # Fallback to a recent 48-hour window
        now = int(time.time())
        start_time = now - (48 * 3600)  # 48 hours ago
        return start_time, now

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id = mobj.group('id')
        live_id = mobj.group('live_id')
        stream_id = mobj.group('stream_id')
        channel = mobj.group('channel')

        # Handle direct HLS URLs
        if live_id and stream_id:
            # Remove query parameters from stream_id if present
            clean_stream_id = stream_id.split('?')[0] if '?' in stream_id else stream_id
            
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(
                url, clean_stream_id, 'mp4', m3u8_id='hls', fatal=False, quiet=True)
            
            return {
                'id': clean_stream_id,
                'title': 'European Parliament Stream',
                'formats': formats,
                'subtitles': subtitles,
            }

        # Download the webpage for standard europarl URLs
        webpage = self._download_webpage(url, display_id)
        
        # Check for live indicators
        is_live = bool(re.search(r'(?:isLive|livestream|live-stream|\"live\"\s*:\s*true)', webpage, re.IGNORECASE))
        
        # Extract title
        title = self._extract_title_from_webpage(webpage, display_id)
        
        # First try direct URLs from the webpage (this is the most reliable approach)
        direct_urls = self._extract_direct_url_from_webpage(webpage)
        
        # Track whether we successfully found a stream
        formats = []
        subtitles = {}
        
        if direct_urls:
            for m3u8_url in direct_urls:
                try:
                    fmt, subs = self._extract_m3u8_formats_and_subtitles(
                        m3u8_url, display_id, 'mp4', m3u8_id='hls', fatal=False)
                    
                    if fmt:
                        formats.extend(fmt)
                        self._merge_subtitles(subs, target=subtitles)
                        
                        return {
                            'id': display_id,
                            'display_id': display_id,
                            'title': title,
                            'formats': formats,
                            'subtitles': subtitles,
                            'is_live': is_live,
                        }
                except ExtractorError:
                    pass
        
        # Parse timestamps for archive retrieval (or use current time for live)
        if is_live:
            # For live streams, we don't need timestamps
            start_timestamp, end_timestamp = None, None
        else:
            start_timestamp, end_timestamp = self._parse_meeting_date(display_id)
        
        # Use appropriate stream types for the content type
        stream_types = self.LIVE_STREAM_TYPES if is_live else self.ARCHIVE_STREAM_TYPES
        
        # Try combinations with improved targeting
        for channel in self.PRIORITY_CHANNELS:
            for stream_type in stream_types:
                # For live streams, try without timestamps first
                if is_live:
                    live_url = f"https://live.media.eup.glcloud.eu/hls/live/{self.MAIN_ENDPOINT}/{channel}/{stream_type}.m3u8"
                    
                    try:
                        fmt, subs = self._extract_m3u8_formats_and_subtitles(
                            live_url, display_id, 'mp4', m3u8_id='hls', fatal=False)
                        
                        if fmt:
                            formats.extend(fmt)
                            self._merge_subtitles(subs, target=subtitles)
                            
                            return {
                                'id': display_id,
                                'display_id': display_id,
                                'title': title,
                                'formats': formats,
                                'subtitles': subtitles,
                                'is_live': True,
                            }
                    except ExtractorError:
                        pass
                
                # For archived content (or as fallback for live), try with timestamps
                if start_timestamp and end_timestamp:
                    archive_url = f"https://live.media.eup.glcloud.eu/hls/live/{self.MAIN_ENDPOINT}/{channel}/{stream_type}.m3u8?startTime={start_timestamp}&endTime={end_timestamp}"
                    
                    try:
                        fmt, subs = self._extract_m3u8_formats_and_subtitles(
                            archive_url, display_id, 'mp4', m3u8_id='hls', fatal=False)
                        
                        if fmt:
                            formats.extend(fmt)
                            self._merge_subtitles(subs, target=subtitles)
                            
                            return {
                                'id': display_id,
                                'display_id': display_id,
                                'title': title,
                                'formats': formats,
                                'subtitles': subtitles,
                                'is_live': False,
                            }
                    except ExtractorError:
                        pass
        
        # Provide helpful error with the most likely working URLs
        suggested_urls = []
        
        # Add the URLs that are most likely to work based on the logs and screenshots
        if start_timestamp and end_timestamp:
            suggested_urls.extend([
                f"https://live.media.eup.glcloud.eu/hls/live/{self.MAIN_ENDPOINT}/channel-07-bxl/index-archive.m3u8?startTime={start_timestamp}&endTime={end_timestamp}",
                f"https://live.media.eup.glcloud.eu/hls/live/{self.MAIN_ENDPOINT}/channel-01-bxl/index-archive.m3u8?startTime={start_timestamp}&endTime={end_timestamp}"
            ])
        else:
            suggested_urls.extend([
                f"https://live.media.eup.glcloud.eu/hls/live/{self.MAIN_ENDPOINT}/channel-07-bxl/index.m3u8",
                f"https://live.media.eup.glcloud.eu/hls/live/{self.MAIN_ENDPOINT}/channel-01-bxl/index.m3u8"
            ])
        
        suggestions = "\n".join([f"yt-dlp \"{url}\"" for url in suggested_urls])
        
        raise ExtractorError(
            f"Could not extract stream URL for {display_id or url}. The European Parliament stream may not be available.\n"
            f"Live stream detected: {is_live}\n"
            f"Try using yt-dlp directly with one of these URLs:\n{suggestions}",
            expected=True
        )
