# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor

from ..utils import (
    ExtractorError,
    urlencode_postdata,
    int_or_none,
    str_or_none,
    determine_ext,
)

from ..compat import compat_HTTPError


class AnimeLabBaseIE(InfoExtractor):
    _LOGIN_REQUIRED = True
    _LOGIN_URL = 'https://www.animelab.com/login'
    _NETRC_MACHINE = 'animelab'

    def _login(self):
        def is_logged_in(login_webpage):
            return 'Sign In' not in login_webpage

        login_page = self._download_webpage(
            self._LOGIN_URL, None, 'Downloading login page')

        # Check if already logged in
        if is_logged_in(login_page):
            return

        (username, password) = self._get_login_info()
        if username is None and self._LOGIN_REQUIRED:
            self.raise_login_required('Login is required to access any AnimeLab content')

        login_form = {
            'email': username,
            'password': password,
        }

        try:
            response = self._download_webpage(
                self._LOGIN_URL, None, 'Logging in', 'Wrong login info',
                data=urlencode_postdata(login_form),
                headers={'Content-Type': 'application/x-www-form-urlencoded'})
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 400:
                raise ExtractorError('Unable to log in (wrong credentials?)', expected=True)
            else:
                raise

        # if login was successful
        if is_logged_in(response):
            return

        raise ExtractorError('Unable to login (cannot verify if logged in)')

    def _real_initialize(self):
        self._login()


class AnimeLabIE(AnimeLabBaseIE):
    _VALID_URL = r'https?://(?:www\.)?animelab\.com/player/(?P<id>[^/]+)'

    # the following tests require authentication, but a free account will suffice
    # just set 'usenetrc' to true in test/local_parameters.json if you use a .netrc file
    # or you can set 'username' and 'password' there
    # the tests also select a specific format so that the same video is downloaded
    # regardless of whether the user is premium or not (needs testing on a premium account)
    _TEST = {
        'url': 'https://www.animelab.com/player/fullmetal-alchemist-brotherhood-episode-42',
        'md5': '05bde4b91a5d1ff46ef5b94df05b0f7f',
        'info_dict': {
            'id': '383',
            'ext': 'mp4',
            'display_id': 'fullmetal-alchemist-brotherhood-episode-42',
            'title': 'Fullmetal Alchemist: Brotherhood - Episode 42 - Signs of a Counteroffensive',
            'description': 'md5:103eb61dd0a56d3dfc5dbf748e5e83f4',
            'series': 'Fullmetal Alchemist: Brotherhood',
            'episode': 'Signs of a Counteroffensive',
            'episode_number': 42,
            'duration': 1469,
            'season': 'Season 1',
            'season_number': 1,
            'season_id': '38',
        },
        'params': {
            'format': '[format_id=21711_yeshardsubbed_ja-JP][height=480]',
        },
        'skip': 'All AnimeLab content requires authentication',
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)

        # unfortunately we can get different URLs for the same formats
        # e.g. if we are using a "free" account so no dubs available
        # (so _remove_duplicate_formats is not effective)
        # so we use a dictionary as a workaround
        formats = {}
        for language_option_url in ('https://www.animelab.com/player/%s/subtitles',
                                    'https://www.animelab.com/player/%s/dubbed'):
            actual_url = language_option_url % display_id
            webpage = self._download_webpage(actual_url, display_id, 'Downloading URL ' + actual_url)

            video_collection = self._parse_json(self._search_regex(r'new\s+?AnimeLabApp\.VideoCollection\s*?\((.*?)\);', webpage, 'AnimeLab VideoCollection'), display_id)
            position = int_or_none(self._search_regex(r'playlistPosition\s*?=\s*?(\d+)', webpage, 'Playlist Position'))

            raw_data = video_collection[position]['videoEntry']

            video_id = str_or_none(raw_data['id'])

            # create a title from many sources (while grabbing other info)
            # TODO use more fallback sources to get some of these
            series = raw_data.get('showTitle')
            video_type = raw_data.get('videoEntryType', {}).get('name')
            episode_number = raw_data.get('episodeNumber')
            episode_name = raw_data.get('name')

            title_parts = (series, video_type, episode_number, episode_name)
            if None not in title_parts:
                title = '%s - %s %s - %s' % title_parts
            else:
                title = episode_name

            description = raw_data.get('synopsis') or self._og_search_description(webpage, default=None)

            duration = int_or_none(raw_data.get('duration'))

            thumbnail_data = raw_data.get('images', [])
            thumbnails = []
            for thumbnail in thumbnail_data:
                for instance in thumbnail['imageInstances']:
                    image_data = instance.get('imageInfo', {})
                    thumbnails.append({
                        'id': str_or_none(image_data.get('id')),
                        'url': image_data.get('fullPath'),
                        'width': image_data.get('width'),
                        'height': image_data.get('height'),
                    })

            season_data = raw_data.get('season', {}) or {}
            season = str_or_none(season_data.get('name'))
            season_number = int_or_none(season_data.get('seasonNumber'))
            season_id = str_or_none(season_data.get('id'))

            for video_data in raw_data['videoList']:
                current_video_list = {}
                current_video_list['language'] = video_data.get('language', {}).get('languageCode')

                is_hardsubbed = video_data.get('hardSubbed')

                for video_instance in video_data['videoInstances']:
                    httpurl = video_instance.get('httpUrl')
                    url = httpurl if httpurl else video_instance.get('rtmpUrl')
                    if url is None:
                        # this video format is unavailable to the user (not premium etc.)
                        continue

                    current_format = current_video_list.copy()

                    format_id_parts = []

                    format_id_parts.append(str_or_none(video_instance.get('id')))

                    if is_hardsubbed is not None:
                        if is_hardsubbed:
                            format_id_parts.append('yeshardsubbed')
                        else:
                            format_id_parts.append('nothardsubbed')

                    format_id_parts.append(current_format['language'])

                    format_id = '_'.join([x for x in format_id_parts if x is not None])

                    ext = determine_ext(url)
                    if ext == 'm3u8':
                        for format_ in self._extract_m3u8_formats(
                                url, video_id, m3u8_id=format_id, fatal=False):
                            formats[format_['format_id']] = format_
                        continue
                    elif ext == 'mpd':
                        for format_ in self._extract_mpd_formats(
                                url, video_id, mpd_id=format_id, fatal=False):
                            formats[format_['format_id']] = format_
                        continue

                    current_format['url'] = url
                    quality_data = video_instance.get('videoQuality')
                    if quality_data:
                        quality = quality_data.get('name') or quality_data.get('description')
                    else:
                        quality = None

                    height = None
                    if quality:
                        height = int_or_none(self._search_regex(r'(\d+)p?$', quality, 'Video format height', default=None))

                    if height is None:
                        self.report_warning('Could not get height of video')
                    else:
                        current_format['height'] = height
                    current_format['format_id'] = format_id

                    formats[current_format['format_id']] = current_format

        formats = list(formats.values())
        self._sort_formats(formats)

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'series': series,
            'episode': episode_name,
            'episode_number': int_or_none(episode_number),
            'thumbnails': thumbnails,
            'duration': duration,
            'formats': formats,
            'season': season,
            'season_number': season_number,
            'season_id': season_id,
        }


class AnimeLabShowsIE(AnimeLabBaseIE):
    _VALID_URL = r'https?://(?:www\.)?animelab\.com/shows/(?P<id>[^/]+)'

    _TEST = {
        'url': 'https://www.animelab.com/shows/attack-on-titan',
        'info_dict': {
            'id': '45',
            'title': 'Attack on Titan',
            'description': 'md5:989d95a2677e9309368d5cf39ba91469',
        },
        'playlist_count': 59,
        'skip': 'All AnimeLab content requires authentication',
    }

    def _real_extract(self, url):
        _BASE_URL = 'http://www.animelab.com'
        _SHOWS_API_URL = '/api/videoentries/show/videos/'
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id, 'Downloading requested URL')

        show_data_str = self._search_regex(r'({"id":.*}),\svideoEntry', webpage, 'AnimeLab show data')
        show_data = self._parse_json(show_data_str, display_id)

        show_id = str_or_none(show_data.get('id'))
        title = show_data.get('name')
        description = show_data.get('shortSynopsis') or show_data.get('longSynopsis')

        entries = []
        for season in show_data['seasons']:
            season_id = season['id']
            get_data = urlencode_postdata({
                'seasonId': season_id,
                'limit': 1000,
            })
            # despite using urlencode_postdata, we are sending a GET request
            target_url = _BASE_URL + _SHOWS_API_URL + show_id + "?" + get_data.decode('utf-8')
            response = self._download_webpage(
                target_url,
                None, 'Season id %s' % season_id)

            season_data = self._parse_json(response, display_id)

            for video_data in season_data['list']:
                entries.append(self.url_result(
                    _BASE_URL + '/player/' + video_data['slug'], 'AnimeLab',
                    str_or_none(video_data.get('id')), video_data.get('name')
                ))

        return {
            '_type': 'playlist',
            'id': show_id,
            'title': title,
            'description': description,
            'entries': entries,
        }

# TODO implement myqueue
