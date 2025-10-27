import json
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    extract_attributes,
    float_or_none,
    int_or_none,
    traverse_obj,
    update_url_query,
    url_or_none,
)


class AudibleIE(InfoExtractor):
    """
    Extract audio samples and metadata from Audible audiobooks.

    This extractor supports:
    - Free sample downloads (no authentication required)
    - Metadata extraction (title, description, duration, thumbnail)
    - DRM-protected DASH manifests for Widevine streams (requires --allow-unplayable-formats;
      yt-dlp cannot decrypt them, but will warn and fall back to samples when possible)

    For full audiobook downloads in AAX format, use audible-cli:
    https://github.com/mkb79/audible-cli
    """
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?audible\.(?:com|ca|co\.uk|com\.au|de|fr|in|it|co\.jp)/
        (
            webplayer\?(?:[^#]*?&)?asin=(?P<id>B[0-9A-Z]{9,10})
            |
            pd/(?:[^/?#]+/)?(?P<id_path>B[0-9A-Z]{9,10})?
        )
    '''

    _TESTS = [{
        'url': 'https://www.audible.com/webplayer?asin=B00NWS13PI&isSample=true',
        'info_dict': {
            'id': 'B00NWS13PI',
            'title': 'The Clash of Civilizations?',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.audible.ca/pd/The-Wild-Womans-Way-Audiobook/B07D9V4F63',
        'info_dict': {
            'id': 'B07D9V4F63',
            'title': str,
        },
        'params': {'skip_download': True},
        'only_matching': True,
    }, {
        # UK domain
        'url': 'https://www.audible.co.uk/pd/Harry-Potter-and-the-Philosophers-Stone-Book-1-Audiobook/B017V4JPOC',
        'info_dict': {
            'id': 'B017V4JPOC',
            'title': str,
        },
        'params': {'skip_download': True},
        'only_matching': True,
    }, {
        # Australian domain
        'url': 'https://www.audible.com.au/pd/The-48-Laws-of-Power-Audiobook/B07F1FP7K4',
        'info_dict': {
            'id': 'B07F1FP7K4',
            'title': str,
        },
        'params': {'skip_download': True},
        'only_matching': True,
    }, {
        # URL with complex query parameters (tracking, referrer, etc.)
        'url': 'https://www.audible.ca/pd/Habits-for-Greatness-Audiobook/B0D6BWGFPS?ref_pageloadid=8JEtZZv5wiIefbuU&pf_rd_p=8f843958-d99e-43df-bf19-95454fb68769&pf_rd_r=XNEAH7WFMR4WVE1TPJT5',
        'info_dict': {
            'id': 'B0D6BWGFPS',
            'title': str,
        },
        'params': {'skip_download': True},
        'only_matching': True,
    }, {
        # Short pd URL without title in path
        'url': 'https://www.audible.com/pd/B002V5A8NA',
        'info_dict': {
            'id': 'B002V5A8NA',
            'title': str,
        },
        'params': {'skip_download': True},
        'only_matching': True,
    }, {
        # German domain
        'url': 'https://www.audible.de/pd/Die-Macht-der-Gewohnheit-Hoerbuch/B00PMQWORM',
        'info_dict': {
            'id': 'B00PMQWORM',
            'title': str,
        },
        'params': {'skip_download': True},
        'only_matching': True,
    }]

    def _extract_player_attrs(self, webpage):
        player_block = self._search_regex(
            r'(<[^>]+id=["\']adbl-cloud-player-container-data["\'][^>]*>)',
            webpage, 'player data', default=None)
        if not player_block:
            return {}
        return extract_attributes(player_block)

    def _extract_json_manifest(self, webpage):
        manifest_url = self._search_regex(
            (
                r'"(https?://[^"\']+\.mpd(?:\?[^"\']*)?)"',
                r"'(https?://[^'\\]+\.mpd(?:\?[^'\\]*)?)'",
            ), webpage, 'MPD manifest', default=None)
        if manifest_url:
            manifest_url = manifest_url.replace('\\/', '/')
        return url_or_none(manifest_url)

    def _real_extract(self, url):
        sanitized_url = re.sub(r'\\(?=[?&#=&])', '', url)
        if sanitized_url != url:
            url = sanitized_url

        mobj = self._match_valid_url(url)
        asin = mobj.group('id') or mobj.group('id_path')
        if not asin:
            raise ExtractorError(
                'Missing ASIN in URL. Audible URLs must include the product ID (ASIN). '
                'Example: https://www.audible.ca/pd/Title-Name/B0XXXXXXXXX',
                expected=True)
        parsed_url = urllib.parse.urlparse(url)
        scheme = parsed_url.scheme or 'https'
        domain = parsed_url.netloc or 'www.audible.com'
        base_url = f'{scheme}://{domain}'

        try:
            webpage = self._download_webpage(url, asin)
        except ExtractorError as exc:
            exc_str = str(exc)
            # Check if this is a 404 error (wrong domain/region)
            if '404' in exc_str:
                # Extract domain extension for helpful message
                domain_ext = domain.split('.')[-1] if domain else 'com'
                other_domains = ['.com', '.ca', '.co.uk', '.com.au', '.de', '.fr', '.in', '.it', '.co.jp']
                suggestions = [d for d in other_domains if not domain.endswith(d)][:3]
                raise ExtractorError(
                    f'This title is not available on audible.{domain_ext}. '
                    f'Try using the correct regional domain for your account (e.g., audible{suggestions[0]}, audible{suggestions[1]})',
                    expected=True, video_id=asin)
            # Check if this is a 400 error (malformed URL)
            elif '400' in exc_str:
                raise ExtractorError(
                    f'Invalid URL format. Please check the URL and remove any trailing characters or backslashes. '
                    f'Expected format: https://www.audible.{domain.split(".")[-1]}/pd/Title-Name/ASIN',
                    expected=True, video_id=asin)
            raise
        pdp_webpage = webpage if '/pd/' in parsed_url.path else None

        if '/webplayer' not in parsed_url.path:
            webplayer_url = update_url_query(f'{base_url}/webplayer', {
                'asin': asin,
                'isSample': 'true',
            })
            webpage = self._download_webpage(webplayer_url, asin, note='Downloading webplayer page')

        player_attrs = self._extract_player_attrs(webpage)

        manifest_url = self._extract_json_manifest(webpage)
        sample_url = player_attrs.get('data-sampleurl')
        formats, subtitles = [], {}

        if manifest_url:
            mpd_formats, subtitles = self._extract_mpd_formats_and_subtitles(
                manifest_url, asin, fatal=False)
            for fmt in mpd_formats:
                fmt['has_drm'] = True
                fmt.setdefault('drm_scheme', 'widevine')
                fmt['preference'] = min(fmt.get('preference', 0), -100)
                fmt.setdefault('format_note', 'DRM-protected DASH manifest (unplayable)')
            formats.extend(mpd_formats)

        license_info = self._download_license_info(
            asin, domain, player_attrs, url, fatal=False)
        if license_info:
            license_mpd = license_info.get('mpd_url')
            if license_mpd:
                placeholder_format = {
                    'url': license_mpd,
                    'format_id': 'dash-manifest',
                    'protocol': 'dash',
                    'manifest_url': license_mpd,
                    'has_drm': True,
                    'drm_scheme': 'widevine',
                    'preference': -100,
                    'format_note': 'DRM-protected DASH manifest (unplayable)',
                }
                self.report_warning(
                    'Audible streaming titles are DRM-protected DASH audio. yt-dlp cannot decrypt them. '
                    'For full audiobook downloads, use audible-cli: https://github.com/mkb79/audible-cli',
                )
                allow_unplayable = bool(getattr(getattr(self, '_downloader', None), 'params', {}).get('allow_unplayable_formats'))
                if allow_unplayable:
                    mpd_formats, api_subs = self._extract_mpd_formats_and_subtitles(
                        license_mpd, asin, fatal=False)
                    if not mpd_formats:
                        mpd_formats = [placeholder_format]
                    for fmt in mpd_formats:
                        fmt['has_drm'] = True
                        fmt.setdefault('drm_scheme', 'widevine')
                        fmt['preference'] = min(fmt.get('preference', 0), -100)
                        fmt.setdefault('format_note', 'DRM-protected DASH manifest (unplayable)')
                    formats.extend(mpd_formats)
                    subtitles = self._merge_subtitles(subtitles, api_subs)
                else:
                    self.to_screen(f'{asin}: Use --allow-unplayable-formats to parse the full DRM manifest')
                    formats.append(placeholder_format)
            sample_url = sample_url or license_info.get('sample_url')
            duration = float_or_none(license_info.get('duration'))
            chapter_duration = float_or_none(license_info.get('chapter_duration'))
        else:
            duration = chapter_duration = None

        sample_added = False
        if url_or_none(sample_url):
            if not any(fmt.get('url') == sample_url for fmt in formats):
                formats.append({
                    'url': sample_url,
                    'format_id': 'http-mp3-sample',
                    'ext': 'mp3',
                    'vcodec': 'none',
                    'protocol': 'http',
                    'acodec': 'mp3',
                    'format_note': 'Audible sample preview',
                })
                sample_added = True
        elif not formats:
            sample_url = None

        if sample_added:
            if any(fmt.get('has_drm') for fmt in formats):
                self.report_warning(
                    'Only the free Audible sample is playable via yt-dlp. '
                    'For full audiobook downloads in AAX format, use audible-cli: https://github.com/mkb79/audible-cli',
                )

        if formats and all(fmt.get('has_drm') for fmt in formats):
            self.raise_no_formats(
                'Audible streaming titles are DRM-protected. yt-dlp cannot decrypt them. '
                'For full audiobook downloads, use audible-cli: https://github.com/mkb79/audible-cli',
                expected=True, video_id=asin)

        if not formats:
            raise ExtractorError('Unable to locate playable media for this title', expected=True)

        subtitles = subtitles or {}

        title = (player_attrs.get('data-title')
                 or self._html_extract_title(pdp_webpage or webpage, default=None)
                 or self._og_search_title(pdp_webpage or webpage, default=None)
                 or asin)
        description = (self._html_search_meta('description', pdp_webpage, default=None)
                       if pdp_webpage else None)
        thumbnail = self._search_regex(
            r'id=["\']adbl-cloudBook["\'][^>]+src="([^"]+)"',
            webpage, 'thumbnail', default=None)

        return {
            'id': asin,
            'title': title,
            'description': clean_html(description),
            'thumbnail': url_or_none(thumbnail),
            'uploader': player_attrs.get('data-authororparent'),
            'duration': duration or chapter_duration,
            'formats': formats,
            'subtitles': subtitles,
        }

    def _merge_subtitles(self, subs1, subs2):
        if not subs1:
            return subs2
        if not subs2:
            return subs1
        out = subs1.copy()
        for lang, entries in subs2.items():
            out.setdefault(lang, []).extend(entries)
        return out

    def _download_license_info(self, asin, domain, player_attrs, referer_url, *, fatal=False):
        api_root = f'https://{domain}/audible-api/1.0'
        license_url = f'{api_root}/content/{asin}/licenserequest'
        # Simplified payload based on API requirements
        payload = {
            'asin': asin,
            'response_groups': 'chapter_info,content_reference,last_position_heard,certificate',
            'consumption_type': 'Streaming',
            'chapter_titles_type': 'Tree',
            'spatial': True,
            'use_adaptive_bit_rate': True,
            'supported_media_features': {
                'drm_types': ['Mpeg', 'Widevine'],
                'codecs': ['mp4a.40.2'],
                'chapter_titles_type': 'Tree',
                'previews': False,
                'catalog_samples': False,
            },
        }

        token = player_attrs.get('data-token')
        key = player_attrs.get('data-key')
        if token and key:
            payload['token'] = token
            payload['key'] = key

        market = player_attrs.get('data-membershipsubscriptionasin')
        if market:
            payload['membership_subscription_asin'] = market

        base_url = f'https://{domain}'
        downloader_cookies = getattr(getattr(self, '_downloader', None), 'cookiejar', None)

        def find_cookie(names, domains=None):
            if not downloader_cookies:
                return None
            lower_names = {name.lower() for name in names}
            for cookie in downloader_cookies:
                if cookie.name.lower() not in lower_names:
                    continue
                if domains and cookie.domain not in domains:
                    continue
                return cookie.value
            return None

        session_id = find_cookie(['session-id', 'sess-at-ac'])
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'client-id': 'WebPlayerApplication',
            'Origin': base_url,
            'Referer': referer_url,
            'device-type': 'A3SSF9KOQX7TIJ',
            'Accept-Language': 'en-CA,en;q=0.9',
            'Cache-Control': 'no-cache',
        }

        session_id_attr = traverse_obj(player_attrs, 'data-sessionid')
        session_id = session_id or session_id_attr
        if session_id:
            headers['session-id'] = session_id

        cookie_header = None
        if downloader_cookies:
            try:
                cookie_header = downloader_cookies.get_cookie_header(license_url)
            except Exception:
                cookie_header = None
        if cookie_header:
            headers['Cookie'] = cookie_header

        try:
            license_json = self._download_json(
                license_url, asin, data=json.dumps(payload).encode('utf-8'), headers=headers,
                fatal=True, note='Downloading license request')
        except ExtractorError as exc:
            cause = getattr(exc, 'cause', None)
            status = int_or_none(getattr(cause, 'code', None))
            if status is None:
                status = int_or_none(getattr(cause, 'status', None))

            if not fatal and status in (400, 401, 403, 404):
                self.report_warning(
                    f'Unable to fetch streaming license (HTTP {status}). '
                    'Falling back to sample audio. '
                    'For full audiobook downloads, see: https://github.com/mkb79/audible-cli',
                )
                return {}
            raise

        if not license_json:
            return {}

        # The API returns content_license at the root level, not under 'data'
        content_license = license_json.get('content_license') or traverse_obj(license_json, ('data', 'content_license')) or {}

        license_denied = bool(content_license.get('license_denial_reasons'))
        if license_denied:
            denial_reasons = content_license.get('license_denial_reasons')
            # Check if any denials mention authentication issues
            has_auth_issue = any('Empty customerId' in str(reason.get('message', ''))
                                 or 'does not has access' in str(reason.get('message', ''))
                                 for reason in denial_reasons)
            if has_auth_issue:
                self.report_warning(
                    'Unable to access full audiobook - authentication required. '
                    'Use --cookies-from-browser BROWSER to provide credentials. '
                    'Falling back to free sample.',
                )
            else:
                # Show simplified denial messages for other cases
                messages = [reason.get('message') for reason in denial_reasons if reason.get('message')]
                if messages:
                    self.report_warning(f'License denied: {"; ".join(set(messages))}')
        if content_license.get('message'):
            message = content_license.get('message')
            if 'rights' in message.lower() or 'membership' in message.lower():
                self.to_screen(f'{asin}: {message}')
        mpd_url = self._find_mpd_url(content_license)
        if not mpd_url and not license_denied:
            # Only warn about missing MPD if license wasn't denied (expected failure)
            mpd_url = self._search_regex(
                r'https?://[^"\s]+\.mpd(?:\?[^"\s]*)?',
                json.dumps(content_license), 'MPD manifest', fatal=False)

        chapter_info = traverse_obj(content_license, ('content_metadata', 'chapter_info')) or {}
        playback_info = content_license.get('playback_info') or {}
        runtime_sec = (
            float_or_none(playback_info.get('runtime_length_sec'))
            or float_or_none(chapter_info.get('runtime_length_sec'))
            or float_or_none(playback_info.get('runtime_length_ms'), 1000)
            or float_or_none(chapter_info.get('runtime_length_ms'), 1000)
        )
        return {
            'mpd_url': mpd_url,
            'duration': runtime_sec,
            'chapter_duration': float_or_none(chapter_info.get('runtime_length_sec')),
            'sample_url': traverse_obj(content_license, ('content_metadata', 'content_url', 'sample_url')),
        }

    def _find_mpd_url(self, data):
        if isinstance(data, str):
            return data if '.mpd' in data else None
        if isinstance(data, list):
            for item in data:
                result = self._find_mpd_url(item)
                if result:
                    return result
        elif isinstance(data, dict):
            # Check for license_response first (this is what the real API returns)
            candidate = data.get('license_response')
            if candidate and isinstance(candidate, str) and '.mpd' in candidate:
                return candidate

            # Other possible locations
            candidate = traverse_obj(data, ('content_metadata', 'manifest', 'url'), expected_type=str)
            if candidate:
                return candidate
            candidate = traverse_obj(data, ('content_metadata', 'content_url', 'url'), expected_type=str)
            if candidate:
                return candidate
            candidate = traverse_obj(data, ('content_metadata', 'content_url', 'urls', ..., 'url'), expected_type=str)
            if candidate:
                return candidate
            candidate = traverse_obj(data, ('content_metadata', 'content_reference', 'content_url'), expected_type=str)
            if candidate:
                return candidate
            candidate = traverse_obj(data, ('playback_info', 'manifest', 'url'), expected_type=str)
            if candidate:
                return candidate
            for value in data.values():
                result = self._find_mpd_url(value)
                if result:
                    return result
        return None
