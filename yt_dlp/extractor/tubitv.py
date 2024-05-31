import re

from .common import InfoExtractor
from ..networking import Request
from ..utils import (
    ExtractorError,
    int_or_none,
    js_to_json,
    traverse_obj,
    url_or_none,
    urlencode_postdata,
)


class TubiTvIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tubitv\.com/(?P<type>video|movies|tv-shows)/(?P<id>\d+)'
    _LOGIN_URL = 'http://tubitv.com/login'
    _NETRC_MACHINE = 'tubitv'
    _TESTS = [{
        'url': 'https://tubitv.com/movies/100004539/the-39-steps',
        'info_dict': {
            'id': '100004539',
            'ext': 'mp4',
            'title': 'The 39 Steps',
            'description': 'md5:bb2f2dd337f0dc58c06cb509943f54c8',
            'uploader_id': 'abc2558d54505d4f0f32be94f2e7108c',
            'release_year': 1935,
            'thumbnail': r're:^https?://.+\.(jpe?g|png)$',
            'duration': 5187,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://tubitv.com/tv-shows/554628/s01-e01-rise-of-the-snakes',
        'info_dict': {
            'id': '554628',
            'ext': 'mp4',
            'title': 'S01:E01 - Rise of the Snakes',
            'description': 'md5:ba136f586de53af0372811e783a3f57d',
            'episode': 'Rise of the Snakes',
            'episode_number': 1,
            'season': 'Season 1',
            'season_number': 1,
            'uploader_id': '2a9273e728c510d22aa5c57d0646810b',
            'release_year': 2011,
            'thumbnail': r're:^https?://.+\.(jpe?g|png)$',
            'duration': 1376,
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'http://tubitv.com/video/283829/the_comedian_at_the_friday',
        'md5': '43ac06be9326f41912dc64ccf7a80320',
        'info_dict': {
            'id': '283829',
            'ext': 'mp4',
            'title': 'The Comedian at The Friday',
            'description': 'A stand up comedian is forced to look at the decisions in his life while on a one week trip to the west coast.',
            'uploader_id': 'bc168bee0d18dd1cb3b86c68706ab434',
        },
        'skip': 'Content Unavailable'
    }, {
        'url': 'http://tubitv.com/tv-shows/321886/s01_e01_on_nom_stories',
        'only_matching': True,
    }, {
        'url': 'https://tubitv.com/movies/560057/penitentiary?start=true',
        'info_dict': {
            'id': '560057',
            'ext': 'mp4',
            'title': 'Penitentiary',
            'description': 'md5:8d2fc793a93cc1575ff426fdcb8dd3f9',
            'uploader_id': 'd8fed30d4f24fcb22ec294421b9defc2',
            'release_year': 1979,
        },
        'skip': 'Content Unavailable'
    }]

    # DRM formats are included only to raise appropriate error
    _UNPLAYABLE_FORMATS = ('hlsv6_widevine', 'hlsv6_widevine_nonclearlead', 'hlsv6_playready_psshv0',
                           'hlsv6_fairplay', 'dash_widevine', 'dash_widevine_nonclearlead')

    def _perform_login(self, username, password):
        self.report_login()
        form_data = {
            'username': username,
            'password': password,
        }
        payload = urlencode_postdata(form_data)
        request = Request(self._LOGIN_URL, payload)
        request.headers['Content-Type'] = 'application/x-www-form-urlencoded'
        login_page = self._download_webpage(
            request, None, False, 'Wrong login info')
        if not re.search(r'id="tubi-logout"', login_page):
            raise ExtractorError(
                'Login failed (invalid username/password)', expected=True)

    def _real_extract(self, url):
        video_id, video_type = self._match_valid_url(url).group('id', 'type')
        webpage = self._download_webpage(f'https://tubitv.com/{video_type}/{video_id}/', video_id)
        video_data = self._search_json(
            r'window\.__data\s*=', webpage, 'data', video_id,
            transform_source=js_to_json)['video']['byId'][video_id]

        formats = []
        drm_formats = False

        for resource in traverse_obj(video_data, ('video_resources', lambda _, v: url_or_none(v['manifest']['url']))):
            resource_type = resource.get('type')
            manifest_url = resource['manifest']['url']
            if resource_type == 'dash':
                formats.extend(self._extract_mpd_formats(manifest_url, video_id, mpd_id=resource_type, fatal=False))
            elif resource_type in ('hlsv3', 'hlsv6'):
                formats.extend(self._extract_m3u8_formats(manifest_url, video_id, 'mp4', m3u8_id=resource_type, fatal=False))
            elif resource_type in self._UNPLAYABLE_FORMATS:
                drm_formats = True
            else:
                self.report_warning(f'Skipping unknown resource type "{resource_type}"')

        if not formats and drm_formats:
            self.report_drm(video_id)
        elif not formats and not video_data.get('policy_match'):  # policy_match is False if content was removed
            raise ExtractorError('This content is currently unavailable', expected=True)

        subtitles = {}
        for sub in traverse_obj(video_data, ('subtitles', lambda _, v: url_or_none(v['url']))):
            subtitles.setdefault(sub.get('lang', 'English'), []).append({
                'url': self._proto_relative_url(sub['url']),
            })

        title = traverse_obj(video_data, ('title', {str}))
        season_number, episode_number, episode_title = self._search_regex(
            r'^S(\d+):E(\d+) - (.+)', title, 'episode info', fatal=False, group=(1, 2, 3), default=(None, None, None))

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
            'season_number': int_or_none(season_number),
            'episode_number': int_or_none(episode_number),
            'episode': episode_title,
            **traverse_obj(video_data, {
                'description': ('description', {str}),
                'duration': ('duration', {int_or_none}),
                'uploader_id': ('publisher_id', {str}),
                'release_year': ('year', {int_or_none}),
                'thumbnails': ('thumbnails', ..., {url_or_none}, {'url': {self._proto_relative_url}}),
            }),
        }


class TubiTvShowIE(InfoExtractor):
    _WORKING = False
    _VALID_URL = r'https?://(?:www\.)?tubitv\.com/series/[0-9]+/(?P<show_name>[^/?#]+)'
    _TESTS = [{
        'url': 'https://tubitv.com/series/3936/the-joy-of-painting-with-bob-ross?start=true',
        'playlist_mincount': 390,
        'info_dict': {
            'id': 'the-joy-of-painting-with-bob-ross',
        }
    }]

    def _entries(self, show_url, show_name):
        show_webpage = self._download_webpage(show_url, show_name)

        show_json = self._parse_json(self._search_regex(
            r'window\.__data\s*=\s*({[^<]+});\s*</script>',
            show_webpage, 'data'), show_name, transform_source=js_to_json)['video']

        for episode_id in show_json['fullContentById'].keys():
            if traverse_obj(show_json, ('byId', episode_id, 'type')) == 's':
                continue
            yield self.url_result(
                f'https://tubitv.com/tv-shows/{episode_id}/',
                ie=TubiTvIE.ie_key(), video_id=episode_id)

    def _real_extract(self, url):
        show_name = self._match_valid_url(url).group('show_name')
        return self.playlist_result(self._entries(url, show_name), playlist_id=show_name)
