# coding: utf-8
from __future__ import unicode_literals

import random
import re
import string

from .common import InfoExtractor
from ..compat import compat_HTTPError
from ..utils import (
    determine_ext,
    dict_get,
    int_or_none,
    js_to_json,
    str_or_none,
    try_get,
    urlencode_postdata,
    ExtractorError,
)


class FunimationPageIE(InfoExtractor):
    IE_NAME = 'funimation:page'
    _VALID_URL = r'(?P<origin>https?://(?:www\.)?funimation(?:\.com|now\.uk))/(?P<lang>[^/]+/)?(?P<path>shows/(?P<id>[^/]+/[^/?#&]+).*$)'

    _TESTS = [{
        'url': 'https://www.funimation.com/shows/attack-on-titan-junior-high/broadcast-dub-preview/',
        'info_dict': {
            'id': '210050',
            'ext': 'mp4',
            'title': 'Broadcast Dub Preview',
            # Other metadata is tested in FunimationIE
        },
        'params': {
            'skip_download': 'm3u8',
        },
        'add_ie': ['Funimation'],
    }, {
        # Not available in US
        'url': 'https://www.funimation.com/shows/hacksign/role-play/',
        'only_matching': True,
    }, {
        # with lang code
        'url': 'https://www.funimation.com/en/shows/hacksign/role-play/',
        'only_matching': True,
    }, {
        'url': 'https://www.funimationnow.uk/shows/puzzle-dragons-x/drop-impact/simulcast/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        display_id = mobj.group('id').replace('/', '_')
        if not mobj.group('lang'):
            url = '%s/en/%s' % (mobj.group('origin'), mobj.group('path'))

        webpage = self._download_webpage(url, display_id)
        title_data = self._parse_json(self._search_regex(
            r'TITLE_DATA\s*=\s*({[^}]+})',
            webpage, 'title data', default=''),
            display_id, js_to_json, fatal=False) or {}

        video_id = (
            title_data.get('id')
            or self._search_regex(
                (r"KANE_customdimensions.videoID\s*=\s*'(\d+)';", r'<iframe[^>]+src="/player/(\d+)'),
                webpage, 'video_id', default=None)
            or self._search_regex(
                r'/player/(\d+)',
                self._html_search_meta(['al:web:url', 'og:video:url', 'og:video:secure_url'], webpage, fatal=True),
                'video id'))
        return self.url_result(f'https://www.funimation.com/player/{video_id}', FunimationIE.ie_key(), video_id)


class FunimationIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?funimation\.com/player/(?P<id>\d+)'

    _NETRC_MACHINE = 'funimation'
    _TOKEN = None

    _TESTS = [{
        'url': 'https://www.funimation.com/player/210051',
        'info_dict': {
            'id': '210050',
            'display_id': 'broadcast-dub-preview',
            'ext': 'mp4',
            'title': 'Broadcast Dub Preview',
            'thumbnail': r're:https?://.*\.(?:jpg|png)',
            'episode': 'Broadcast Dub Preview',
            'episode_id': '210050',
            'season': 'Extras',
            'season_id': '166038',
            'season_number': 99,
            'series': 'Attack on Titan: Junior High',
            'description': '',
            'duration': 154,
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }, {
        'note': 'player_id should be extracted with the relevent compat-opt',
        'url': 'https://www.funimation.com/player/210051',
        'info_dict': {
            'id': '210051',
            'display_id': 'broadcast-dub-preview',
            'ext': 'mp4',
            'title': 'Broadcast Dub Preview',
            'thumbnail': r're:https?://.*\.(?:jpg|png)',
            'episode': 'Broadcast Dub Preview',
            'episode_id': '210050',
            'season': 'Extras',
            'season_id': '166038',
            'season_number': 99,
            'series': 'Attack on Titan: Junior High',
            'description': '',
            'duration': 154,
        },
        'params': {
            'skip_download': 'm3u8',
            'compat_opts': ['seperate-video-versions'],
        },
    }]

    def _login(self):
        username, password = self._get_login_info()
        if username is None:
            return
        try:
            data = self._download_json(
                'https://prod-api-funimationnow.dadcdigital.com/api/auth/login/',
                None, 'Logging in', data=urlencode_postdata({
                    'username': username,
                    'password': password,
                }))
            self._TOKEN = data['token']
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 401:
                error = self._parse_json(e.cause.read().decode(), None)['error']
                raise ExtractorError(error, expected=True)
            raise

    def _real_initialize(self):
        self._login()

    @staticmethod
    def _get_experiences(episode):
        for lang, lang_data in episode.get('languages', {}).items():
            for video_data in lang_data.values():
                for version, f in video_data.items():
                    yield lang, version.title(), f

    def _get_episode(self, webpage, experience_id=None, episode_id=None, fatal=True):
        ''' Extract the episode, season and show objects given either episode/experience id '''
        show = self._parse_json(
            self._search_regex(
                r'show\s*=\s*({.+?})\s*;', webpage, 'show data', fatal=fatal),
            experience_id, transform_source=js_to_json, fatal=fatal) or []
        for season in show.get('seasons', []):
            for episode in season.get('episodes', []):
                if episode_id is not None:
                    if str(episode.get('episodePk')) == episode_id:
                        return episode, season, show
                    continue
                for _, _, f in self._get_experiences(episode):
                    if f.get('experienceId') == experience_id:
                        return episode, season, show
        if fatal:
            raise ExtractorError('Unable to find episode information')
        else:
            self.report_warning('Unable to find episode information')
        return {}, {}, {}

    def _real_extract(self, url):
        initial_experience_id = self._match_id(url)
        webpage = self._download_webpage(
            url, initial_experience_id, note=f'Downloading player webpage for {initial_experience_id}')
        episode, season, show = self._get_episode(webpage, experience_id=int(initial_experience_id))
        episode_id = str(episode['episodePk'])
        display_id = episode.get('slug') or episode_id

        formats, subtitles, thumbnails, duration = [], {}, [], 0
        requested_languages, requested_versions = self._configuration_arg('language'), self._configuration_arg('version')
        only_initial_experience = 'seperate-video-versions' in self.get_param('compat_opts', [])

        for lang, version, fmt in self._get_experiences(episode):
            experience_id = str(fmt['experienceId'])
            if (only_initial_experience and experience_id != initial_experience_id
                    or requested_languages and lang.lower() not in requested_languages
                    or requested_versions and version.lower() not in requested_versions):
                continue
            thumbnails.append({'url': fmt.get('poster')})
            duration = max(duration, fmt.get('duration', 0))
            format_name = '%s %s (%s)' % (version, lang, experience_id)
            self.extract_subtitles(
                subtitles, experience_id, display_id=display_id, format_name=format_name,
                episode=episode if experience_id == initial_experience_id else episode_id)

            headers = {}
            if self._TOKEN:
                headers['Authorization'] = 'Token %s' % self._TOKEN
            page = self._download_json(
                'https://www.funimation.com/api/showexperience/%s/' % experience_id,
                display_id, headers=headers, expected_status=403, query={
                    'pinst_id': ''.join([random.choice(string.digits + string.ascii_letters) for _ in range(8)]),
                }, note=f'Downloading {format_name} JSON')
            sources = page.get('items') or []
            if not sources:
                error = try_get(page, lambda x: x['errors'][0], dict)
                if error:
                    self.report_warning('%s said: Error %s - %s' % (
                        self.IE_NAME, error.get('code'), error.get('detail') or error.get('title')))
                else:
                    self.report_warning('No sources found for format')

            current_formats = []
            for source in sources:
                source_url = source.get('src')
                source_type = source.get('videoType') or determine_ext(source_url)
                if source_type == 'm3u8':
                    current_formats.extend(self._extract_m3u8_formats(
                        source_url, display_id, 'mp4', m3u8_id='%s-%s' % (experience_id, 'hls'), fatal=False,
                        note=f'Downloading {format_name} m3u8 information'))
                else:
                    current_formats.append({
                        'format_id': '%s-%s' % (experience_id, source_type),
                        'url': source_url,
                    })
                for f in current_formats:
                    # TODO: Convert language to code
                    f.update({'language': lang, 'format_note': version})
                formats.extend(current_formats)
        self._remove_duplicate_formats(formats)
        self._sort_formats(formats)

        return {
            'id': initial_experience_id if only_initial_experience else episode_id,
            'display_id': display_id,
            'duration': duration,
            'title': episode['episodeTitle'],
            'description': episode.get('episodeSummary'),
            'episode': episode.get('episodeTitle'),
            'episode_number': int_or_none(episode.get('episodeId')),
            'episode_id': episode_id,
            'season': season.get('seasonTitle'),
            'season_number': int_or_none(season.get('seasonId')),
            'season_id': str_or_none(season.get('seasonPk')),
            'series': show.get('showTitle'),
            'formats': formats,
            'thumbnails': thumbnails,
            'subtitles': subtitles,
        }

    def _get_subtitles(self, subtitles, experience_id, episode, display_id, format_name):
        if isinstance(episode, str):
            webpage = self._download_webpage(
                f'https://www.funimation.com/player/{experience_id}', display_id,
                fatal=False, note=f'Downloading player webpage for {format_name}')
            episode, _, _ = self._get_episode(webpage, episode_id=episode, fatal=False)

        for _, version, f in self._get_experiences(episode):
            for source in f.get('sources'):
                for text_track in source.get('textTracks'):
                    if not text_track.get('src'):
                        continue
                    sub_type = text_track.get('type').upper()
                    sub_type = sub_type if sub_type != 'FULL' else None
                    current_sub = {
                        'url': text_track['src'],
                        'name': ' '.join(filter(None, (version, text_track.get('label'), sub_type)))
                    }
                    lang = '_'.join(filter(None, (
                        text_track.get('language', 'und'), version if version != 'Simulcast' else None, sub_type)))
                    if current_sub not in subtitles.get(lang, []):
                        subtitles.setdefault(lang, []).append(current_sub)
        return subtitles


class FunimationShowIE(FunimationIE):
    IE_NAME = 'funimation:show'
    _VALID_URL = r'(?P<url>https?://(?:www\.)?funimation(?:\.com|now\.uk)/(?P<locale>[^/]+)?/?shows/(?P<id>[^/?#&]+))/?(?:[?#]|$)'

    _TESTS = [{
        'url': 'https://www.funimation.com/en/shows/sk8-the-infinity',
        'info_dict': {
            'id': 1315000,
            'title': 'SK8 the Infinity'
        },
        'playlist_count': 13,
        'params': {
            'skip_download': True,
        },
    }, {
        # without lang code
        'url': 'https://www.funimation.com/shows/ouran-high-school-host-club/',
        'info_dict': {
            'id': 39643,
            'title': 'Ouran High School Host Club'
        },
        'playlist_count': 26,
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        base_url, locale, display_id = re.match(self._VALID_URL, url).groups()

        show_info = self._download_json(
            'https://title-api.prd.funimationsvc.com/v2/shows/%s?region=US&deviceType=web&locale=%s'
            % (display_id, locale or 'en'), display_id)
        items = self._download_json(
            'https://prod-api-funimationnow.dadcdigital.com/api/funimation/episodes/?limit=99999&title_id=%s'
            % show_info.get('id'), display_id).get('items')
        vod_items = map(lambda k: dict_get(k, ('mostRecentSvod', 'mostRecentAvod')).get('item'), items)

        return {
            '_type': 'playlist',
            'id': show_info['id'],
            'title': show_info['name'],
            'entries': [
                self.url_result(
                    '%s/%s' % (base_url, vod_item.get('episodeSlug')), FunimationPageIE.ie_key(),
                    vod_item.get('episodeId'), vod_item.get('episodeName'))
                for vod_item in sorted(vod_items, key=lambda x: x.get('episodeOrder'))],
        }
