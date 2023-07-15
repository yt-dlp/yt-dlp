import re

from .common import InfoExtractor
from ..networking import Request
from ..utils import (
    ExtractorError,
    int_or_none,
    js_to_json,
    traverse_obj,
    urlencode_postdata,
)


class TubiTvIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    (?:
                        tubitv:|
                        https?://(?:www\.)?tubitv\.com/(?:video|movies|tv-shows)/
                    )
                    (?P<id>[0-9]+)'''
    _LOGIN_URL = 'http://tubitv.com/login'
    _NETRC_MACHINE = 'tubitv'
    _GEO_COUNTRIES = ['US']
    _TESTS = [{
        'url': 'https://tubitv.com/movies/383676/tracker',
        'md5': '566fa0f76870302d11af0de89511d3f0',
        'info_dict': {
            'id': '383676',
            'ext': 'mp4',
            'title': 'Tracker',
            'description': 'md5:ff320baf43d0ad2655e538c1d5cd9706',
            'uploader_id': 'f866e2677ea2f0dff719788e4f7f9195',
            'release_year': 2010,
            'thumbnail': r're:^https?://.+\.(jpe?g|png)$',
            'duration': 6122,
        },
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
        video_id = self._match_id(url)
        video_data = self._download_json(f'https://tubitv.com/oz/videos/{video_id}/content', video_id, query={
            'video_resources': ['dash', 'hlsv3', 'hlsv6', *self._UNPLAYABLE_FORMATS],
        })
        title = video_data['title']

        formats = []
        drm_formats = False

        for resource in video_data['video_resources']:
            if resource['type'] in ('dash', ):
                formats += self._extract_mpd_formats(resource['manifest']['url'], video_id, mpd_id=resource['type'], fatal=False)
            elif resource['type'] in ('hlsv3', 'hlsv6'):
                formats += self._extract_m3u8_formats(resource['manifest']['url'], video_id, 'mp4', m3u8_id=resource['type'], fatal=False)
            elif resource['type'] in self._UNPLAYABLE_FORMATS:
                drm_formats = True

        if not formats and drm_formats:
            self.report_drm(video_id)
        elif not formats and not video_data.get('policy_match'):  # policy_match is False if content was removed
            raise ExtractorError('This content is currently unavailable', expected=True)

        thumbnails = []
        for thumbnail_url in video_data.get('thumbnails', []):
            if not thumbnail_url:
                continue
            thumbnails.append({
                'url': self._proto_relative_url(thumbnail_url),
            })

        subtitles = {}
        for sub in video_data.get('subtitles', []):
            sub_url = sub.get('url')
            if not sub_url:
                continue
            subtitles.setdefault(sub.get('lang', 'English'), []).append({
                'url': self._proto_relative_url(sub_url),
            })

        season_number, episode_number, episode_title = self._search_regex(
            r'^S(\d+):E(\d+) - (.+)', title, 'episode info', fatal=False, group=(1, 2, 3), default=(None, None, None))

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': thumbnails,
            'description': video_data.get('description'),
            'duration': int_or_none(video_data.get('duration')),
            'uploader_id': video_data.get('publisher_id'),
            'release_year': int_or_none(video_data.get('year')),
            'season_number': int_or_none(season_number),
            'episode_number': int_or_none(episode_number),
            'episode_title': episode_title
        }


class TubiTvShowIE(InfoExtractor):
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
                'tubitv:%s' % episode_id,
                ie=TubiTvIE.ie_key(), video_id=episode_id)

    def _real_extract(self, url):
        show_name = self._match_valid_url(url).group('show_name')
        return self.playlist_result(self._entries(url, show_name), playlist_id=show_name)
