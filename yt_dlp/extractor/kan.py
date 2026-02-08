from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    traverse_obj,
    unified_strdate,
)
from ..networking import HEADRequest
import contextlib
import json
import re


class KanIE(InfoExtractor):
    IE_NAME = 'kan.org.il'
    IE_DESC = 'Kan 11 (כאן 11) - Israeli Public Broadcasting'
    _VALID_URL = r'https?://(?:www\.)?kan\.org\.il/(?:content/)?(?:kan[^/]*/)?(?:[^/]+/)*(?P<id>\d+)|kan:(?P<kaltura_id>1_[a-z0-9]{8})'
    _TESTS = [{
        # Kaltura-based video (drama series)
        'url': 'https://www.kan.org.il/content/kan/kan-11/p-12317/s3/846647/',
        'info_dict': {
            'id': '1_l4f97mga',
            'ext': 'mp4',
            'title': 'תהרן - עונה 3 - פרק 6',
            'description': 'md5:9c0cd2dc64eb84d0f9e0e8a5327e7736',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 2388,
        },
        'params': {
            'skip_download': True,
        },
    }, {
        # Redge HLS video (talk show)
        'url': 'https://www.kan.org.il/content/kan/kan-11/p-11486/s10/996446/',
        'info_dict': {
            'id': '996446',
            'ext': 'mp4',
            'title': str,
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': int,
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        kaltura_id = mobj.group('kaltura_id')
        
        # If kaltura_id was provided directly (kan:1_xxxxxxxx format)
        if kaltura_id:
            video_id = kaltura_id
        else:
            # Fetch the webpage with browser impersonation to bypass Cloudflare
            webpage = self._download_webpage(
                url,
                video_id,
                impersonate=True,
            )
            
            # Try to extract Kaltura entry ID from page
            # Pattern: window.entryId = "1_xxxxxxxx"
            kaltura_id = self._search_regex(
                r'(?:entryId\s*[:=]\s*["\']|vod/)(1_[a-z0-9]{8})',
                webpage,
                'kaltura id',
                default=None,
            )
            
            # Check if this is a placeholder (non-Kaltura content)
            if kaltura_id == '1_item0700':
                kaltura_id = None
            
            # If no valid Kaltura ID, try Redge HLS player fallback
            if not kaltura_id:
                return self._extract_redge_video(webpage, video_id)
        
        # Extract Kaltura-based video
        return self._extract_kaltura_video(kaltura_id, webpage if 'webpage' in locals() else None)
    
    def _extract_kaltura_video(self, kaltura_id, webpage=None):
        """Extract video using Kaltura CDN (for drama series)"""
        # Build DASH manifest URL using cdn-redge load balancer
        # The load balancer redirects to actual CDN server (n-121-X)
        lb_dash_url = f'https://r.il.cdn-redge.media/webcache/gorigin/dash/oil/kancdn/vod/{kaltura_id}/LIBCODER_SMOOTH_1080_KAN/Manifest.ism'
        
        # Follow redirect to get actual CDN server URL
        # This is critical because server numbers vary per video
        redirect_response = self._request_webpage(
            HEADRequest(lb_dash_url),
            kaltura_id,
            note='Resolving CDN server',
            errnote='Could not resolve CDN server',
        )
        
        dash_url = redirect_response.url
        
        # Extract formats from DASH manifest
        formats = self._extract_mpd_formats(
            dash_url,
            kaltura_id,
            mpd_id='dash',
            fatal=False,
        )
        
        # Extract metadata from webpage
        title = None
        description = None
        thumbnail = None
        duration = None
        upload_date = None
        
        if webpage:
            # Extract from VideoObject JSON-LD schema
            schemas = re.findall(
                r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
                webpage,
                re.DOTALL,
            )
            video_schema = {}
            for schema_text in schemas:
                with contextlib.suppress(Exception):
                    schema_data = json.loads(schema_text)
                    if isinstance(schema_data, dict) and schema_data.get('@type') == 'VideoObject':
                        video_schema = schema_data
                        break
            
            # Extract metadata from VideoObject if found
            if video_schema:
                title = video_schema.get('name')
                description = video_schema.get('description')
                thumbnail = video_schema.get('thumbnailUrl')
                upload_date = unified_strdate(video_schema.get('uploadDate'))
            
            # Fallback to OpenGraph tags
            if not title:
                title = self._og_search_title(webpage, default=None)
            if not description:
                description = self._og_search_description(webpage, default=None)
            if not thumbnail:
                thumbnail = self._og_search_thumbnail(webpage, default=None)
            
            # Extract duration from item_duration
            if not duration:
                duration_str = self._search_regex(
                    r'item_duration:\s*["\'](\d+)["\']',
                    webpage,
                    'duration',
                    default=None,
                )
                if duration_str:
                    duration = int(duration_str)
            
            # Fallback to __INITIAL_STATE__
            if not duration:
                duration = traverse_obj(
                    self._search_json(
                        r'window\.__INITIAL_STATE__\s*=',
                        webpage,
                        'initial state',
                        kaltura_id,
                        default={},
                    ),
                    ('video', 'duration'),
                )
        
        return {
            'id': kaltura_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'upload_date': upload_date,
            'formats': formats,
        }
    
    def _extract_redge_video(self, webpage, video_id):
        """Extract video using Redge HLS player (for talk shows, comedy, docs)"""
        # Extract HLS URL from data-hls-url attribute
        hls_url = self._search_regex(
            r'data-hls-url="([^"]+)"',
            webpage,
            'hls url',
            default=None,
        )
        
        if not hls_url:
            raise ExtractorError('Could not find video source', expected=True)
        
        # Fix protocol-relative URLs
        if hls_url.startswith('//'):
            hls_url = 'https:' + hls_url
        
        # Extract formats from HLS manifest
        formats = self._extract_m3u8_formats(
            hls_url,
            video_id,
            'mp4',
            entry_protocol='m3u8_native',
            m3u8_id='hls',
            fatal=False,
        )
        
        # Extract metadata from Redge player data attributes
        title = self._search_regex(
            r'data-meta-title="([^"]*)"',
            webpage,
            'title',
            default=None,
        )
        if not title:
            title = self._og_search_title(webpage, default=None)
        
        series = self._search_regex(
            r'data-meta-series-name="([^"]*)"',
            webpage,
            'series',
            default=None,
        )
        if series and title:
            title = f'{series} - {title}'
        
        duration = self._search_regex(
            r'item_duration:\s*["\'](\d+)["\']',
            webpage,
            'duration',
            default=None,
        )
        if duration:
            duration = int(duration)
        
        thumbnail = self._search_regex(
            r'data-poster-url="([^"]*)"',
            webpage,
            'thumbnail',
            default=None,
        )
        if thumbnail and not thumbnail.startswith('http'):
            thumbnail = 'https://www.kan.org.il' + thumbnail
        if not thumbnail:
            thumbnail = self._og_search_thumbnail(webpage, default=None)
        
        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'duration': duration,
            'formats': formats,
        }
