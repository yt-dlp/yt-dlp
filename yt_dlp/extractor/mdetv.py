import re
import time

from .common import InfoExtractor
from ..utils import jwt_decode_hs256


class MDETVBaseIE(InfoExtractor):
    """Base class for MDE.TV extractors"""

    @staticmethod
    def _is_jwt_expired(token):
        return jwt_decode_hs256(token)['exp'] - time.time() < 120

    def _do_cookie_refresh_and_check(self, video_id):
        """Refreshes the mde-access-token and mde-refresh-token if necessary. No-op otherwise."""
        cookie = self._get_cookies('https://www.mde.tv')
        try:
            access_token = cookie['mde-access-token'].value
            refresh_token = cookie['mde-refresh-token'].value
        except KeyError:
            self.raise_login_required()
        if self._is_jwt_expired(refresh_token):
            raise ValueError("Refresh token is expired. Can't continue.")
        elif self._is_jwt_expired(access_token):
            # calling the method will return a set-cookie header; should handle it all
            self._download_json('https://api.mde.tv/v1/auth',
                                video_id, note='Refreshing token',
                                headers={'Accept': 'application/json'})

    def _call_api(self, path, video_id, note='Downloading API JSON', authenticated=False):
        if authenticated:
            self._do_cookie_refresh_and_check(video_id)
        return self._download_json(
            f'https://api.mde.tv/v1/{path}',
            video_id, note=note,
            headers={'Accept': 'application/json'})


class MDETVIE(MDETVBaseIE):
    IE_NAME = 'mde.tv'
    IE_DESC = 'MDE.TV videos'
    _VALID_URL = r'https?://www\.mde\.tv/series/(?P<series_id>[^/]+)/(?P<id>[^/?#]+)'

    _TESTS = [{
        'url': 'https://www.mde.tv/series/ren-men/renmen-ep1-driving-manual-pilot',
        'info_dict': {
            'id': 'renmen-ep1-driving-manual-pilot',
            'ext': 'mp4',
            'title': 'EP01 - Manual Transmission',
            'description': 'The Renaissance Men attempt to drive a truck into traffic.',
            'uploader': 'ren-men',
            'thumbnail': 'https://cdn.mde.tv/thumbnails/videos/ed99925c-5a3d-4d0e-bfc3-d55f6e8f687c-thumbnail-1769961030294.png',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        series_id = mobj.group('series_id')

        # Download the webpage to extract the video UUID from structured data
        webpage = self._download_webpage(url, video_id)

        # Extract video UUID from the structured data in the page
        # The page contains minified JavaScript with video data in a specific pattern
        # Look for UUID in object properties that are part of video data structures
        video_uuid = self._search_regex(
            r'\bid\s*:\s*["\']([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})["\']',
            webpage, 'video UUID')

        # Get signature tokens from the API
        sign_data = self._call_api(
            f'videos/{video_uuid}/sign', video_id,
            'Downloading signature', True)

        token = sign_data['token']
        expires = sign_data['expires']

        # Construct the iframe URL to fetch the actual playlist URL
        # The iframe contains the authenticated streaming URL in its JavaScript
        iframe_url = (
            f'https://iframe.mediadelivery.net/embed/85972/{video_uuid}'
            f'?token={token}&expires={expires}'
        )

        # Download the iframe page to extract the playlist URL
        iframe_page = self._download_webpage(
            iframe_url, video_id, 'Downloading iframe page',
            headers={
                'sec-fetch-dest': 'iframe',
                'sec-fetch-mode': 'navigate',
                'referer': 'https://www.mde.tv/',
            })

        # Extract the playlist URL from the iframe's JavaScript
        # The playlist URL has format: https://stream.mde.tv/bcdn_token=...&expires=.../uuid/playlist.m3u8
        playlist_url = self._search_regex(
            r'urlPlaylistUrl\s*=\s*["\']([^"\']+)["\']',
            iframe_page, 'playlist URL')
        formats, subs = self._extract_m3u8_formats_and_subtitles(
            playlist_url, video_id, 'mp4', m3u8_id='hls', fatal=False)

        # Extract more metadata from the page script tag
        title = self._search_regex(
            r'title:\s*"([^"]+)"', webpage, 'title', default=video_id)
        description = self._search_regex(
            r'description:\s*"([^"]+)"', webpage, 'description', default=None)
        thumbnail = self._search_regex(
            r'thumbnail:\s*"([^"]+)"', webpage, 'thumbnail', default=None)

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'subtitles': subs,
            'formats': formats,
            'uploader': series_id,
        }


class MDETVSeriesIE(MDETVBaseIE):
    IE_NAME = 'mde.tv:series'
    IE_DESC = 'MDE.TV series'
    _VALID_URL = r'https?://www\.mde\.tv/series/(?P<id>[^/?#]+)/?(?:$|[?#])'

    _TESTS = [{
        'url': 'https://www.mde.tv/series/ren-men',
        'info_dict': {
            'id': 'ren-men',
            'title': 'Renaissance Men',
            'description': 'Luke Valentine and Ryan Rivera learn it all.',
        },
        'playlist_mincount': 3,
    }]

    def _real_extract(self, url):
        series_id = self._match_id(url)

        # Download the webpage
        webpage = self._download_webpage(url, series_id)

        # Extract all video tags from the structured data
        # The page contains a 'videos' array with objects that have 'tag' properties
        # Pattern: tag: "episode-slug-here"
        entries = []
        for match in re.finditer(
                r'\btag\s*:\s*["\']([^"\']+)["\']',
                webpage):
            episode_slug = match.group(1)
            episode_url = f'https://www.mde.tv/series/{series_id}/{episode_slug}'
            entries.append(self.url_result(
                episode_url, ie=MDETVIE.ie_key()))

        # Extract series title
        title = (self._og_search_title(webpage, default=None) or self._html_search_regex(
            r'<div class="_title[^"]*">([^<]+)</div>', webpage, 'title', default=series_id))
        description = (self._og_search_title(webpage, default=None) or self._html_search_regex(
            r'<div class="_description[^"]*">([^<]+)</div>', webpage, 'description', default=series_id))

        return self.playlist_result(entries, series_id, title, description)


class MDETVSiteIE(MDETVBaseIE):
    IE_NAME = 'mde.tv:site'
    IE_DESC = 'MDE.TV sitemap'
    _VALID_URL = r'https?://www\.mde\.tv/series/?(?:$|[?#])'

    _TESTS = [{
        'url': 'https://www.mde.tv/series',
        'info_dict': {
            'id': 'sitemap',
            'title': 'Series',
        },
        'playlist_mincount': 5,
    }]

    def _real_extract(self, url):
        playlist_id = 'sitemap'
        # alternative name: "master playlist"?
        # sitemap works better imo since there is no "playlist" concept in mde.tv

        # Download the webpage
        webpage = self._download_webpage(url, playlist_id)

        # Extract all series tags from the structured data
        # The main page contains a 'series' array with objects containing 'tag' properties
        # We need to distinguish series tags from video tags - series tags appear before 'episodes' property
        entries = []
        seen_tags = set()
        # Match pattern: tag: "series-slug", ... episodes: N
        for match in re.finditer(
                r'\btag\s*:\s*["\']([^"\']+)["\'][^}]*?\bepisodes\s*:\s*\d+',
                webpage, re.DOTALL):
            series_tag = match.group(1)
            if series_tag not in seen_tags:
                seen_tags.add(series_tag)
                series_url = f'https://www.mde.tv/series/{series_tag}'
                entries.append(self.url_result(
                    series_url, ie=MDETVSeriesIE.ie_key()))

        return self.playlist_result(entries, playlist_id, 'Series')
