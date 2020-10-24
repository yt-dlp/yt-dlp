from __future__ import unicode_literals

import re
import json

from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urlparse,
    compat_HTTPError,
)
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_iso8601,
)


class VevoBaseIE(InfoExtractor):
    def _extract_json(self, webpage, video_id):
        return self._parse_json(
            self._search_regex(
                r'window\.__INITIAL_STORE__\s*=\s*({.+?});\s*</script>',
                webpage, 'initial store'),
            video_id)


class VevoIE(VevoBaseIE):
    '''
    Accepts urls from vevo.com or in the format 'vevo:{id}'
    (currently used by MTVIE and MySpaceIE)
    '''
    _VALID_URL = r'''(?x)
        (?:https?://(?:www\.)?vevo\.com/watch/(?!playlist|genre)(?:[^/]+/(?:[^/]+/)?)?|
           https?://cache\.vevo\.com/m/html/embed\.html\?video=|
           https?://videoplayer\.vevo\.com/embed/embedded\?videoId=|
           https?://embed\.vevo\.com/.*?[?&]isrc=|
           vevo:)
        (?P<id>[^&?#]+)'''

    _TESTS = []
    _VERSIONS = {
        0: 'youtube',  # only in AuthenticateVideo videoVersions
        1: 'level3',
        2: 'akamai',
        3: 'level3',
        4: 'amazon',
    }

    def _initialize_api(self, video_id):
        webpage = self._download_webpage(
            'https://accounts.vevo.com/token', None,
            note='Retrieving oauth token',
            errnote='Unable to retrieve oauth token',
            data=json.dumps({
                'client_id': 'SPupX1tvqFEopQ1YS6SS',
                'grant_type': 'urn:vevo:params:oauth:grant-type:anonymous',
            }).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
            })

        if re.search(r'(?i)THIS PAGE IS CURRENTLY UNAVAILABLE IN YOUR REGION', webpage):
            self.raise_geo_restricted(
                '%s said: This page is currently unavailable in your region' % self.IE_NAME)

        auth_info = self._parse_json(webpage, video_id)
        self._api_url_template = self.http_scheme() + '//apiv2.vevo.com/%s?token=' + auth_info['legacy_token']

    def _call_api(self, path, *args, **kwargs):
        try:
            data = self._download_json(self._api_url_template % path, *args, **kwargs)
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError):
                errors = self._parse_json(e.cause.read().decode(), None)['errors']
                error_message = ', '.join([error['message'] for error in errors])
                raise ExtractorError('%s said: %s' % (self.IE_NAME, error_message), expected=True)
            raise
        return data

    def _real_extract(self, url):
        video_id = self._match_id(url)

        self._initialize_api(video_id)

        video_info = self._call_api(
            'video/%s' % video_id, video_id, 'Downloading api video info',
            'Failed to download video info')

        video_versions = self._call_api(
            'video/%s/streams' % video_id, video_id,
            'Downloading video versions info',
            'Failed to download video versions info',
            fatal=False)

        # Some videos are only available via webpage (e.g.
        # https://github.com/ytdl-org/youtube-dl/issues/9366)
        if not video_versions:
            webpage = self._download_webpage(url, video_id)
            json_data = self._extract_json(webpage, video_id)
            if 'streams' in json_data.get('default', {}):
                video_versions = json_data['default']['streams'][video_id][0]
            else:
                video_versions = [
                    value
                    for key, value in json_data['apollo']['data'].items()
                    if key.startswith('%s.streams' % video_id)]

        uploader = None
        artist = None
        featured_artist = None
        artists = video_info.get('artists')
        for curr_artist in artists:
            if curr_artist.get('role') == 'Featured':
                featured_artist = curr_artist['name']
            else:
                artist = uploader = curr_artist['name']

        formats = []
        for video_version in video_versions:
            version = self._VERSIONS.get(video_version.get('version'), 'generic')
            version_url = video_version.get('url')
            if not version_url:
                continue

            if '.ism' in version_url:
                continue
            elif '.mpd' in version_url:
                formats.extend(self._extract_mpd_formats(
                    version_url, video_id, mpd_id='dash-%s' % version,
                    note='Downloading %s MPD information' % version,
                    errnote='Failed to download %s MPD information' % version,
                    fatal=False))
            elif '.m3u8' in version_url:
                formats.extend(self._extract_m3u8_formats(
                    version_url, video_id, 'mp4', 'm3u8_native',
                    m3u8_id='hls-%s' % version,
                    note='Downloading %s m3u8 information' % version,
                    errnote='Failed to download %s m3u8 information' % version,
                    fatal=False))
            else:
                m = re.search(r'''(?xi)
                    _(?P<width>[0-9]+)x(?P<height>[0-9]+)
                    _(?P<vcodec>[a-z0-9]+)
                    _(?P<vbr>[0-9]+)
                    _(?P<acodec>[a-z0-9]+)
                    _(?P<abr>[0-9]+)
                    \.(?P<ext>[a-z0-9]+)''', version_url)
                if not m:
                    continue

                formats.append({
                    'url': version_url,
                    'format_id': 'http-%s-%s' % (version, video_version['quality']),
                    'vcodec': m.group('vcodec'),
                    'acodec': m.group('acodec'),
                    'vbr': int(m.group('vbr')),
                    'abr': int(m.group('abr')),
                    'ext': m.group('ext'),
                    'width': int(m.group('width')),
                    'height': int(m.group('height')),
                })
        self._sort_formats(formats)

        track = video_info['title']
        if featured_artist:
            artist = '%s ft. %s' % (artist, featured_artist)
        title = '%s - %s' % (artist, track) if artist else track

        genres = video_info.get('genres')
        genre = (
            genres[0] if genres and isinstance(genres, list)
            and isinstance(genres[0], compat_str) else None)

        is_explicit = video_info.get('isExplicit')
        if is_explicit is True:
            age_limit = 18
        elif is_explicit is False:
            age_limit = 0
        else:
            age_limit = None

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': video_info.get('imageUrl') or video_info.get('thumbnailUrl'),
            'timestamp': parse_iso8601(video_info.get('releaseDate')),
            'uploader': uploader,
            'duration': int_or_none(video_info.get('duration')),
            'view_count': int_or_none(video_info.get('views', {}).get('total')),
            'age_limit': age_limit,
            'track': track,
            'artist': uploader,
            'genre': genre,
        }


class VevoPlaylistIE(VevoBaseIE):
    _VALID_URL = r'https?://(?:www\.)?vevo\.com/watch/(?P<kind>playlist|genre)/(?P<id>[^/?#&]+)'

    _TESTS = [{
        'url': 'http://www.vevo.com/watch/genre/rock',
        'info_dict': {
            'id': 'rock',
            'title': 'Rock',
        },
        'playlist_count': 20,
    }, {
        'url': 'http://www.vevo.com/watch/genre/rock?index=0',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        playlist_id = mobj.group('id')
        playlist_kind = mobj.group('kind')

        webpage = self._download_webpage(url, playlist_id)

        qs = compat_urlparse.parse_qs(compat_urlparse.urlparse(url).query)
        index = qs.get('index', [None])[0]

        if index:
            video_id = self._search_regex(
                r'<meta[^>]+content=(["\'])vevo://video/(?P<id>.+?)\1[^>]*>',
                webpage, 'video id', default=None, group='id')
            if video_id:
                return self.url_result('vevo:%s' % video_id, VevoIE.ie_key())

        playlists = self._extract_json(webpage, playlist_id)['default']['%ss' % playlist_kind]

        playlist = (list(playlists.values())[0]
                    if playlist_kind == 'playlist' else playlists[playlist_id])

        entries = [
            self.url_result('vevo:%s' % src, VevoIE.ie_key())
            for src in playlist['isrcs']]

        return self.playlist_result(
            entries, playlist.get('playlistId') or playlist_id,
            playlist.get('name'), playlist.get('description'))
