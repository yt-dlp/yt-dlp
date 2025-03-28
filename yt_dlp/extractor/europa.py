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
)

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
                lang, label = (
                    xpath_text(item, 'lg', default=None),
                    xpath_text(item, 'label', default=None)
                )
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
        https?://multimedia\.europarl\.europa\.eu/
        (?:\w+/)?webstreaming/(?:[\w-]+_)?(?P<id>[\w-]+)
    '''
    _TESTS = [{
        'url': 'https://multimedia.europarl.europa.eu/pl/webstreaming/plenary-session_20220914-0900-PLENARY',
        'info_dict': {
            'id': '62388b15-d85b-4add-99aa-ba12ccf64f0d',
            'display_id': '20220914-0900-PLENARY',
            'ext': 'mp4',
            'title': 'Plenary session',
            'release_timestamp': 1663139069,
            'release_date': '20220914',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # example of old live webstream
        'url': 'https://multimedia.europarl.europa.eu/en/webstreaming/euroscola_20221115-1000-SPECIAL-EUROSCOLA',
        'info_dict': {
            'ext': 'mp4',
            'id': '510eda7f-ba72-161b-7ee7-0e836cd2e715',
            'release_timestamp': 1668502800,
            'title': 'Euroscola 2022-11-15 19:21',
            'release_date': '20221115',
            'live_status': 'is_live',
        },
        'skip': 'not live anymore',
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        # Try to parse Next.js data for metadata
        nextjs = self._search_nextjs_data(webpage, display_id, default={})
        page_props = traverse_obj(nextjs, ('props', 'pageProps'), default={})
        media_info = page_props.get('mediaItem') or {} # Look for start/end times here for archives?

        title = media_info.get('title') or media_info.get('name') or display_id
        release_timestamp = None
        # Existing logic uses startDateTime, might need adjustment for archive start/end
        if 'startDateTime' in media_info:
             release_timestamp = parse_iso8601(media_info['startDateTime'])

        # Determine if it's Live or VOD/Archive (might need refinement)
        # mediaSubType might be 'Live' or 'VOD' or something else
        is_live = media_info.get('mediaSubType') == 'Live'

        # Search for any .m3u8 link first
        m3u8_links = self._search_regex(
            r'(https?://[^"]+live\.media\.eup\.glcloud\.eu/hls/live/\d+/[^"]+\.m3u8[^"]*)',
            webpage, 'm3u8 URL', default=None, group=1, fatal=False
        )

        # --- Potential modification area START ---
        # If it's NOT live, and we have start/end times, and m3u8_links points to a live URL,
        # try constructing the index-archive.m3u8 URL here.
        # Example (conceptual - requires actual start/end times and base URL logic):
        # if not is_live and media_info.get('startTime') and media_info.get('endTime'):
        #     start_time = media_info['startTime'] # Assuming these keys exist and hold timestamps
        #     end_time = media_info['endTime']
        #     # Assuming m3u8_links contains a base URL that needs modification
        #     base_url = m3u8_links.split('/')[0:-1] # Highly simplified base URL extraction
        #     archive_url = '/'.join(base_url) + f'/index-archive.m3u8?startTime={start_time}&endTime={end_time}'
        #     m3u8_links = archive_url # Replace the found link with the constructed one
        # --- Potential modification area END ---


        if not m3u8_links:
            self.report_warning('Could not find any .m3u8 link in the page. The site structure may have changed.')
            # Return basic info if no HLS manifest found
            return {
                'id': media_info.get('id') or display_id,
                'display_id': display_id,
                'title': title,
                'release_timestamp': release_timestamp,
                'formats': [],
            }

        # Process all found .m3u8 links (handles case where multiple are found or the first one is a master playlist)
        # The regex used here is identical to the one above, ensures we capture all instances
        import re
        all_links_text = self._html_search_regex(
             r'(https?://[^"]+live\.media\.eup\.glcloud\.eu/hls/live/\d+/[^"]+\.m3u8[^"]*)',
             webpage, 'all m3u8 URLs', default='', fatal=False, group=0 # Find all occurrences
        )
        candidates = re.findall(r'(https?://[^"]+live\.media\.eup\.glcloud\.eu/hls/live/\d+/[^"]+\.m3u8[^"]*)', all_links_text)

        # If the specific constructed URL was made above, ensure it's prioritized or the only candidate
        # (Refined logic needed here based on the modification above)
        if not candidates and m3u8_links: # Fallback if findall failed but initial search worked
             candidates = [m3u8_links]
        elif m3u8_links not in candidates and m3u8_links: # Ensure the primary (possibly constructed) link is included
             candidates.insert(0, m3u8_links)

        candidates = list(dict.fromkeys(candidates)) # Make unique, preserving order

        if not candidates: # Final check if still no candidates
             self.report_warning('Could not extract any valid .m3u8 URLs.')
             return {
                 'id': media_info.get('id') or display_id,
                 'display_id': display_id,
                 'title': title,
                 'release_timestamp': release_timestamp,
                 'formats': [],
             }


        formats, subtitles = [], {}
        for link in candidates:
            # Pass the identified m3u8 URL (could be live, index-archive, or norsk-archive)
            # The 'live' flag might need adjustment based on mediaSubType
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                link, display_id, ext='mp4', live=is_live, fatal=False) # Pass is_live status
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)

        return {
            'id': media_info.get('id') or display_id,
            'display_id': display_id,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
            'release_timestamp': release_timestamp,
             # Report 'is_live' based on detected mediaSubType
            'is_live': is_live or None # Report None if not explicitly Live
        }
