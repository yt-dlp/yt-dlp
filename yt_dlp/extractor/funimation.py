# coding: utf-8
from __future__ import unicode_literals

import random
import re
import string

from .common import InfoExtractor
from ..compat import compat_HTTPError, compat_str
from ..utils import (
    determine_ext,
    dict_get,
    int_or_none,
    js_to_json,
    try_get,
    urlencode_postdata,
    urljoin,
    ExtractorError,
)


class FunimationPageIE(InfoExtractor):
    IE_NAME = 'funimation:page'
    _VALID_URL = r'(?P<origin>https?://(?:www\.)?funimation(?:\.com|now\.uk))/(?P<lang>[^/]+/)?(?P<path>shows/(?P<id>[^/]+/[^/?#&]+).*$)'

    # TODO: Fix tests
    _TESTS = [{
        'url': 'https://www.funimation.com/shows/hacksign/role-play/',
        'info_dict': {
            'id': '91144',
            'display_id': 'role-play',
            'ext': 'mp4',
            'title': '.hack//SIGN - Role Play',
            'description': 'md5:b602bdc15eef4c9bbb201bb6e6a4a2dd',
            'thumbnail': r're:https?://.*\.jpg',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'https://www.funimation.com/shows/attack-on-titan-junior-high/broadcast-dub-preview/',
        'info_dict': {
            'id': '210051',
            'display_id': 'broadcast-dub-preview',
            'ext': 'mp4',
            'title': 'Attack on Titan: Junior High - Broadcast Dub Preview',
            'thumbnail': r're:https?://.*\.(?:jpg|png)',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'https://www.funimationnow.uk/shows/puzzle-dragons-x/drop-impact/simulcast/',
        'only_matching': True,
    }, {
        # with lang code
        'url': 'https://www.funimation.com/en/shows/hacksign/role-play/',
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

    # TODO: Fix test
    _TESTS = [{
        'url': 'https://www.funimation.com/player/210051',
        'info_dict': {
            'id': '210051',
            'display_id': 'attack-on-titan-junior-high_broadcast-dub-preview',
            'ext': 'mp4',
            'title': 'Attack on Titan: Junior High - Broadcast Dub Preview',
            'thumbnail': r're:https?://.*\.(?:jpg|png)',
        },
        'params': {
            'skip_download': 'm3u8',
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

    def _get_episode(self, webpage, experience_id):
        show = self._parse_json(
            self._search_regex(
                r'show\s*=\s*({.+?})\s*;', webpage, 'show data'),
            experience_id, transform_source=js_to_json)
        for season in show['seasons']:
            for episode in season.get('episodes'):
                for lang_data in episode['languages'].values():
                    for video_data in lang_data.values():
                        for f in video_data.values():
                            if f.get('experienceId') == experience_id:
                                return episode, season, show
        raise ExtractorError('Unable to find episode information')

    def _real_extract(self, url):
        experience_id = self._match_id(url)
        webpage = self._download_webpage(url, experience_id)
        episode, season, show = self._get_episode(webpage, int(experience_id))
        display_id = '%s_%s' % (show.get('showSlug'), episode.get('slug'))

        available_formats, thumbnails, duration, subtitles = [], [], 0, {}
        for lang, lang_data in episode['languages'].items():
            for video_data in lang_data.values():
                for uncut_type, f in video_data.items():
                    thumbnails.append({'url': f.get('poster')})
                    duration = max(duration, f.get('duration', 0))
                    # TODO: Subtitles can be extracted here
                    available_formats.append({
                        'id': f['experienceId'],
                        'lang': lang,
                        'uncut': uncut_type,
                    })

        formats = []
        for fmt in available_formats:
            subtitles = self.extract_subtitles(url, fmt['id'], fmt['id'])

            headers = {}
            if self._TOKEN:
                headers['Authorization'] = 'Token %s' % self._TOKEN
            page = self._download_json(
                'https://www.funimation.com/api/showexperience/%s/' % fmt['id'],
                display_id, headers=headers, expected_status=403, query={
                    'pinst_id': ''.join([random.choice(string.digits + string.ascii_letters) for _ in range(8)]),
                }, note='Downloading %s %s (%s) JSON' % (fmt['uncut'], fmt['lang'], fmt['id']))
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
                        source_url, display_id, 'mp4', m3u8_id='%s-%s' % (fmt['id'], 'hls'), fatal=False,
                        note='Downloading %s %s (%s) m3u8 information' % (fmt['uncut'], fmt['lang'], fmt['id'])))
                else:
                    current_formats.append({
                        'format_id': '%s-%s' % (fmt['id'], source_type),
                        'url': source_url,
                    })
                for f in current_formats:
                    # TODO: Convert language to code
                    f.update({'language': fmt['lang'], 'format_note': fmt['uncut']})
                formats.extend(current_formats)
        self._remove_duplicate_formats(formats)
        self._sort_formats(formats)

        return {
            'id': compat_str(episode['episodePk']),
            'display_id': display_id,
            'title': episode['episodeTitle'],
            'description': episode.get('episodeSummary'),
            'episode': episode.get('episodeTitle'),
            'episode_number': int_or_none(episode.get('episodeId')),
            'episode_id': episode.get('slug'),
            'season': season.get('seasonTitle'),
            'season_number': int_or_none(season.get('seasonId')),
            'season_id': compat_str(season.get('seasonPk')),
            'series': show.get('showTitle'),
            'thumbnails': thumbnails,
            'formats': formats,
        }

    def _get_subtitles(self, url, video_id, display_id):
        player_url = urljoin(url, '/player/' + video_id)
        player_page = self._download_webpage(player_url, display_id)
        text_tracks_json_string = self._search_regex(
            r'"textTracks": (\[{.+?}\])',
            player_page, 'subtitles data', default='')
        text_tracks = self._parse_json(
            text_tracks_json_string, display_id, js_to_json, fatal=False) or []
        subtitles = {}
        for text_track in text_tracks:
            url_element = {'url': text_track.get('src')}
            language = text_track.get('language')
            if text_track.get('type') == 'CC':
                language += '_CC'
            subtitles.setdefault(language, []).append(url_element)
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
