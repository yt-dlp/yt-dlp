import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    js_to_json,
    sanitized_Request,
    urlencode_postdata,
    traverse_obj,
    smuggle_url,
    unsmuggle_url
)


class TubiTvBaseIE(InfoExtractor):

    def _parse_page_data(self, webpage, show_id):
        return self._parse_json(self._search_regex(
            r'window\.__data\s*=\s*({[^<]+});\s*</script>',
            webpage, 'data'), show_id, transform_source=js_to_json)['video']

    def _get_show_title(self, show_json, show_id):
        return traverse_obj(show_json, ('byId', '0' + show_id, 'title'))


class TubiTvIE(TubiTvBaseIE):
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
        'skip': 'Content Unavailable'
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
    }, {
        # movie (Tubi original movie 'Swim', lower likelihood of becoming unavailable)
        'url': 'https://tubitv.com/movies/613766/swim?start=true',
        'md5': 'acde434a720fb2e22cb96bf8b99a102d',
        'info_dict': {
            'id': '613766',
            'ext': 'mp4',
            'title': 'Swim',
            'uploader_id': '6b82d97d873a91e75936a79c984c9b65',
            'release_year': 2021,
            'duration': 5208,
            'description': 'md5:77a9064861aedbe0761ce7b2b4fce26e',
            'thumbnail': r're:^https?://.*\.jpg$',
        }
    }, {
        # episode (Tubi original series 'The Freak Brothers', lower likelihood of becoming unavailable)
        'url': 'https://tubitv.com/tv-shows/624837/s01-e01-pilot?start=true',
        'md5': 'c38ef60e8b3ff8b15d4c5780a2cae5f6',
        'info_dict': {
            'id': '624837',
            'ext': 'mp4',
            'uploader_id': '8362002ebcb54c3aeee2431cbf075e8e',
            'series': 'The Freak Brothers',
            'duration': 1536,
            'season_number': 1,
            'title': 'S01:E01 - Pilot',
            'release_year': 2021,
            'episode_number': 1,
            'season': 'Season 1',
            'episode': 'Pilot',
            'description': 'After smoking the magical weed sauce, four stoners get flung fifty years into the future.',
            'thumbnail': r're:^https?://.*\.jpg$',
        }
    }, {
        # "video" (redirects to "movies" or "tv-shows" in browser depending on media type, in this case to Tubi original movie 'Swim')
        'url': 'https://tubitv.com/video/613766/swim',
        'only_matching': True
    }, {
        # alternative to URL
        'url': 'tubitv:613766',
        'only_matching': True
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
        request = sanitized_Request(self._LOGIN_URL, payload)
        request.add_header('Content-Type', 'application/x-www-form-urlencoded')
        login_page = self._download_webpage(
            request, None, False, 'Wrong login info')
        if not re.search(r'id="tubi-logout"', login_page):
            raise ExtractorError(
                'Login failed (invalid username/password)', expected=True)

    def _real_extract(self, url):

        video_id = self._match_id(url)

        url, smuggle_data = unsmuggle_url(url)

        series = None
        video_data = None

        if smuggle_data:
            # Use smuggled data for tv show
            series = smuggle_data.get('show_title')
            video_data = smuggle_data.get('show_data')
        else:
            # Get metadata from page
            # Note: This is done instead fo downloading the JSON directly because the result from
            #       the JSON request (https://tubitv.com/oz/videos/{video_id}/content) contains
            #       only the episode title and not the series title.
            webpage = self._download_webpage(f'https://tubitv.com/video/{video_id}/{video_id}', video_id)
            page_json = self._parse_page_data(webpage, video_id)
            video_data = traverse_obj(page_json, ('byId', video_id))
            series_id = video_data.get('series_id')
            if series_id:
                series = self._get_show_title(page_json, series_id)

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

        season_number = None

        # Check if this is a special episode from a show not belonging to a season
        episode_number, episode_title = self._search_regex(
            r'^Specials E(\d+) - (.+)', title, 'episode info', fatal=False, group=(1, 2), default=(None, None))

        if episode_number or episode_title:
            # Use season 0 for specials (common convention used by media servers)
            season_number = 0
        else:
            # Try standard season/episode parsing
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
            'series': series,
            'episode': episode_title,
        }


class TubiTvShowIE(TubiTvBaseIE):

    # Show URL format: tubitv.com/series/<show_id>/<slug>

    # Show ID is numeric and uniquely identifies show in Tubi API.
    # Slug is text provided by Tubi in URL for readability/SEO. Slug can be arbitrarily
    #    changed in URL and site will still load the correct video, so it is not necessarily
    #    guaranteed to always be the same for the same show, unlike the ID.

    _VALID_URL = r'https?://(?:www\.)?tubitv\.com/series/(?P<show_id>[0-9]+)/[^/?#]+'
    _TESTS = [{
        'url': 'https://tubitv.com/series/3936/the-joy-of-painting-with-bob-ross?start=true',
        'playlist_mincount': 389,
        'info_dict': {
            'id': '3936',
            'title': 'The Joy of Painting With Bob Ross',
        }
    }, {
        # (Tubi original series 'The Freak Brothers', lower likelihood of becoming unavailable)
        'url': 'https://tubitv.com/series/300007896/the-freak-brothers?start=true',
        'playlist_mincount': 8,
        'info_dict': {
            'id': '300007896',
            'title': 'The Freak Brothers',
        }
    }]

    def _entries(self, show_json, show_title):
        for episode_id in show_json['fullContentById'].keys():
            if traverse_obj(show_json, ('byId', episode_id, 'type')) == 's':
                continue
            yield self.url_result(smuggle_url(f'tubitv:{episode_id}', {'show_title': show_title, 'show_data': traverse_obj(show_json, ('byId', episode_id))}), ie=TubiTvIE.ie_key(), video_id=episode_id)

    def _real_extract(self, url):
        show_id = self._match_valid_url(url).group('show_id')
        show_webpage = self._download_webpage(url, show_id)
        show_json = self._parse_page_data(show_webpage, show_id)
        show_title = self._get_show_title(show_json, show_id)
        return self.playlist_result(self._entries(show_json, show_title), playlist_id=show_id, playlist_title=show_title)
