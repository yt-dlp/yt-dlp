import json
import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
    str_or_none,
    url_or_none,
    urljoin,
)
from ..utils.traversal import traverse_obj


class SmotrimBaseIE(InfoExtractor):
    _BASE_URL = 'https://smotrim.ru'
    _GEO_BYPASS = False
    _GEO_COUNTRIES = ['RU']
    _PLAYER_API_URL = 'https://player-api.smotrim.ru/api/v1'

    def _call_player_api(self, resource, item_id):
        response = self._download_json(
            f'{self._PLAYER_API_URL}/{resource}/{item_id}', item_id,
            f'Downloading {resource} JSON metadata',
            expected_status=lambda status: 400 <= status < 500)

        status = response.get('status')
        data = response.get('data')
        if status == 'OK' and isinstance(data, dict):
            return data

        message = response.get('notice') or 'This content is unavailable'
        if status in ('GEO_RESTRICTED', 'GEO_BLOCKED'):
            self.raise_geo_restricted(message, countries=self._GEO_COUNTRIES)
        if status in ('AUTH_REQUIRED', 'LOGIN_REQUIRED'):
            self.raise_login_required(message)
        self.raise_no_formats(message, expected=True, video_id=item_id)

    @staticmethod
    def _first_url(data, *paths):
        for path in paths:
            if url := url_or_none(traverse_obj(data, path, get_all=False)):
                return url

    def _player_common(self, data, item_id):
        episode = data.get('episode') if isinstance(data.get('episode'), dict) else {}
        brand = data.get('brand') if isinstance(data.get('brand'), dict) else {}
        season = episode.get('season') if isinstance(episode.get('season'), dict) else {}

        return {
            'id': str_or_none(data.get('publicId') or data.get('id')) or str(item_id),
            'title': str_or_none(episode.get('title') or data.get('title')),
            'description': str_or_none(episode.get('description') or data.get('description')),
            'thumbnail': self._first_url(
                data,
                ('episode', 'splash', 'large'),
                ('episode', 'splash', 'medium'),
                ('episode', 'splash', 'small'),
                'image', 'splash',
                ('brand', 'poster', 'large'),
                ('brand', 'poster', 'medium'),
                ('brand', 'poster', 'small')),
            'duration': int_or_none(data.get('duration')),
            'timestamp': parse_iso8601(episode.get('airDate') or data.get('airDate')),
            'age_limit': int_or_none(data.get('ageRestriction')),
            'series': str_or_none(brand.get('title')),
            'series_id': str_or_none(brand.get('id')),
            'season': str_or_none(season.get('title')),
            'season_number': int_or_none(season.get('number')),
            'webpage_url': url_or_none(data.get('shareLink')),
        }

    def _channel_webpage_metadata(self, webpage, channel_id):
        if not webpage:
            return {}

        nuxt_data = self._search_nuxt_json(webpage, channel_id, fatal=False)
        for value in (nuxt_data.get('data') or {}).values():
            if not isinstance(value, dict) or str_or_none(value.get('id')) != str(channel_id):
                continue
            return {
                'title': str_or_none(value.get('title')),
                'description': str_or_none(value.get('description') or value.get('subtitle')),
                'thumbnail': self._first_url(
                    value,
                    ('pictures', ..., 'presets', ..., 'link'),
                    ('images', ..., 'presets', ..., 'link')),
            }
        return {}

    def _extract_from_player_api(self, resource, item_id, *, is_live=False, webpage=None):
        data = self._call_player_api(resource, item_id)
        info = self._player_common(data, item_id)

        if resource == 'channel':
            for key, value in self._channel_webpage_metadata(webpage, item_id).items():
                if not info.get(key):
                    info[key] = value

        if not info.get('title'):
            info['title'] = str_or_none(data.get('type')) or f'Smotrim {resource} {item_id}'

        if resource == 'audio':
            audio_url = url_or_none(traverse_obj(data, ('streams', 'mp3', {str})))
            if not audio_url:
                self.raise_no_formats('No audio stream found', expected=True, video_id=item_id)
            return {
                'url': audio_url,
                'ext': 'mp3',
                'vcodec': 'none',
                **info,
            }

        m3u8_url = url_or_none(traverse_obj(data, ('streams', 'm3u8', {str})))
        if not m3u8_url:
            self.raise_no_formats('No HLS stream found', expected=True, video_id=item_id)
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            m3u8_url, item_id, 'mp4', m3u8_id='hls', fatal=False)
        return {
            'formats': formats,
            'subtitles': subtitles,
            'is_live': is_live,
            **info,
        }


class SmotrimIE(SmotrimBaseIE):
    IE_NAME = 'smotrim'
    _VALID_URL = (
        r'(?:https?:)?//(?:(?:player|www)\.)?smotrim\.ru'
        r'(?:(?:/iframe)?/video(?:/id)?/|/brand/\d+/?#playing_video=)(?P<id>\d+)')
    _EMBED_REGEX = [fr'<iframe\b[^>]+\bsrc=["\'](?P<url>{_VALID_URL})']
    _TESTS = [{
        'url': 'https://smotrim.ru/video/1539617',
        'info_dict': {
            'id': '1539617',
            'ext': 'mp4',
            'title': 'Урок №16',
            'duration': 2631,
            'series': 'Полиглот. Китайский с нуля за 16 часов!',
            'series_id': '60562',
            'thumbnail': r're:https?://cdn\.smotrim\.ru/.+\.(?:jpg|png)',
            'timestamp': 1466771100,
            'upload_date': '20160624',
            'age_limit': 12,
            'season': 'Season 2016',
            'season_number': 2016,
        },
    }, {
        'url': 'https://player.smotrim.ru/iframe/video/id/2988590',
        'only_matching': True,
    }, {
        'url': 'https://smotrim.ru/brand/75541#playing_video=6017467',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        return self._extract_from_player_api('video', self._match_id(url))


class SmotrimAudioIE(SmotrimBaseIE):
    IE_NAME = 'smotrim:audio'
    _VALID_URL = r'https?://(?:(?:player|www)\.)?smotrim\.ru(?:/iframe)?/audio(?:/id)?/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://smotrim.ru/audio/2860468',
        'md5': '5a6bc1fa24c7142958be1ad9cfae58a8',
        'info_dict': {
            'id': '2860468',
            'ext': 'mp3',
            'title': 'Колобок и музыкальная игра "Терем-теремок"',
            'duration': 1501,
            'series': 'Весёлый колобок',
            'series_id': '68880',
            'timestamp': 1755925800,
            'upload_date': '20250823',
        },
    }]

    def _real_extract(self, url):
        return self._extract_from_player_api('audio', self._match_id(url))


class SmotrimLiveIE(SmotrimBaseIE):
    IE_NAME = 'smotrim:live'
    _VALID_URL = r'''(?x:
        (?:https?:)?//
            (?:(?:(?:test)?player|www)\.)?
            (?:smotrim\.ru|vgtrk\.com)
            (?:/iframe)?/
            (?P<type>channel|(?:audio-)?live)
            (?:/u?id)?/(?P<id>[\da-f-]+)
    )'''
    _EMBED_REGEX = [fr'<iframe\b[^>]+\bsrc=["\'](?P<url>{_VALID_URL})']
    _TESTS = [{
        'url': 'https://smotrim.ru/channel/76',
        'info_dict': {
            'id': '76',
            'ext': 'mp4',
            'title': 'Москва 24',
            'channel_id': '76',
            'display_id': '76',
            'live_status': 'is_live',
        },
        'params': {'skip_download': 'Livestream'},
    }, {
        'url': 'https://smotrim.ru/channel/81',
        'info_dict': {
            'id': '81',
            'ext': 'mp4',
            'title': 'Радио Маяк',
            'channel_id': '81',
            'display_id': '81',
            'live_status': 'is_live',
        },
        'params': {'skip_download': 'Livestream'},
    }, {
        'url': 'https://player.smotrim.ru/iframe/live/uid/381308c7-a066-4c4f-9656-83e2e792a7b4',
        'info_dict': {
            'id': '4',
            'ext': 'mp4',
            'channel_id': '4',
            'display_id': '381308c7-a066-4c4f-9656-83e2e792a7b4',
            'live_status': 'is_live',
        },
        'params': {'skip_download': 'Livestream'},
    }, {
        'url': 'https://smotrim.ru/live/19201',
        'only_matching': True,
    }, {
        'url': 'https://player.smotrim.ru/iframe/audio-live/id/81',
        'only_matching': True,
    }, {
        'url': 'https://testplayer.vgtrk.com/iframe/live/id/19201',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        typ, display_id = self._match_valid_url(url).group('type', 'id')
        if typ == 'live':
            if display_id.isdecimal():
                self.raise_no_formats(
                    'Legacy numeric live URLs are no longer supported', expected=True, video_id=display_id)
            uuid_map = self._download_json(
                'https://player.smotrim.ru/uuid_channel_map.json', display_id,
                'Downloading live channel map')
            channel_id = next((str(item['CHANNEL_ID']) for item in uuid_map
                               if str(item.get('UUID')).lower() == display_id.lower()), None)
            if not channel_id:
                self.raise_no_formats('Unable to resolve live channel', expected=True, video_id=display_id)
        else:
            channel_id = display_id

        webpage = self._download_webpage(
            f'{self._BASE_URL}/channel/{channel_id}', display_id, fatal=False)
        return {
            'display_id': display_id,
            'channel_id': str(channel_id),
            **self._extract_from_player_api('channel', channel_id, is_live=True, webpage=webpage),
        }


class SmotrimPlaylistIE(SmotrimBaseIE):
    IE_NAME = 'smotrim:playlist'
    _PAGE_SIZE = 26
    _VALID_URL = (
        r'https?://smotrim\.ru(?!/brand/\d+/?#playing_video=)'
        r'/brand/(?P<id>\d+)/?(?P<section>[\w-]+)?')
    _TESTS = [{
        'url': 'https://smotrim.ru/brand/64356',
        'info_dict': {
            'id': '64356',
            'title': 'Большие и маленькие',
        },
        'playlist_mincount': 1,
    }, {
        'url': 'https://smotrim.ru/brand/65293/season-3',
        'info_dict': {
            'id': '65293',
            'title': 'Спасская',
        },
        'playlist_mincount': 1,
    }, {
        'url': 'https://smotrim.ru/brand/68880',
        'info_dict': {
            'id': '68880',
            'title': 'Весёлый колобок',
        },
        'playlist_mincount': 1,
    }]

    @staticmethod
    def _episode_entries(episodes):
        for episode in episodes or []:
            video = episode.get('fullVideo') if isinstance(episode.get('fullVideo'), dict) else {}
            audio = episode.get('audio') if isinstance(episode.get('audio'), dict) else {}
            if video_id := video.get('publicId'):
                yield 'video', str(video_id)
            elif audio_id := audio.get('publicId'):
                yield 'audio', str(audio_id)

    def _find_brand(self, nuxt_data, playlist_id):
        for value in (nuxt_data.get('data') or {}).values():
            if isinstance(value, dict) and str_or_none(value.get('id')) == str(playlist_id) and 'episodesPublic' in value:
                return value
        self.raise_no_formats('Unable to find brand data', expected=True, video_id=playlist_id)

    def _playlist_page(self, webpage, playlist_id, page_url):
        nuxt_data = self._search_nuxt_json(webpage, playlist_id, fatal=False)
        brand = self._find_brand(nuxt_data, playlist_id)
        section_match = re.search(r'/(?:season|year)-(\d+)', page_url)
        season = None
        if section_match:
            season = next((item for item in brand.get('seasonsPublic') or []
                           if str(item.get('number')) == section_match.group(1)), None)
        episodes = (season or {}).get('episodesPublic') or brand.get('episodesPublic') or {}

        section_urls = []
        if not section_match:
            for value in (nuxt_data.get('data') or {}).values():
                if not isinstance(value, dict):
                    continue
                for item in value.get('list') or []:
                    section_url = item.get('link')
                    if re.fullmatch(rf'/brand/{re.escape(str(playlist_id))}/(?:season|year)-\d+', section_url or ''):
                        section_urls.append(urljoin(self._BASE_URL, section_url))
        return brand, season, episodes, section_urls

    def _graphql_entries(self, playlist_id, brand_id, season_id, episodes):
        if not episodes.get('hasMorePages'):
            return

        page_size = len(episodes.get('data') or []) or self._PAGE_SIZE
        order = str(episodes.get('order') or 'ASC').upper()
        query = '''
            query FilterEpisodes($brandId: Int, $seasonId: Int, $page: Int = 2, $first: Int! = 10, $order: SortOrder = ASC) {
                episodesFilter(brand_id: $brandId, season_id: $seasonId, first: $first, page: $page,
                    orderBy: {column: EPISODES_NUMBER, order: $order}) {
                    data { ... on Episode { audio { publicId } fullVideo { publicId } } }
                    paginatorInfo { lastPage }
                }
            }'''
        for page in range(2, 1000):
            response = self._download_json(
                'https://apis.smotrim.ru/graphql', playlist_id,
                f'Downloading episode page {page}', fatal=False,
                data=json.dumps({
                    'query': query,
                    'variables': {
                        'brandId': int_or_none(brand_id),
                        'seasonId': int_or_none(season_id),
                        'page': page,
                        'first': page_size,
                        'order': order,
                    },
                }).encode(), headers={'Content-Type': 'application/json'})
            page_data = traverse_obj(response, ('data', 'episodesFilter', {dict}))
            if not page_data:
                return
            yield from self._episode_entries(page_data.get('data'))
            last_page = int_or_none(traverse_obj(page_data, ('paginatorInfo', 'lastPage')))
            if not last_page or page >= last_page:
                return

    def _html_fallback_entries(self, webpage):
        for card in re.findall(
                r'(?s)<(?:article|div)\b[^>]*\bclass=["\'][^"\']*\bbrand-episodes__item\b[^"\']*["\'][^>]*>.*?</(?:article|div)>', webpage):
            yield from re.findall(r'href=["\']/(audio|video)/(\d+)', card)

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage, urlh = self._download_webpage_handle(url, playlist_id)
        brand, season, episodes, section_urls = self._playlist_page(webpage, playlist_id, urlh.url)

        def entries():
            seen = set()

            def add_entries(page_episodes, page_brand, page_season, page_webpage):
                page_entries = self._episode_entries(page_episodes.get('data'))
                if not page_episodes.get('data'):
                    page_entries = self._html_fallback_entries(page_webpage)
                for entry in (*page_entries, *self._graphql_entries(
                        playlist_id, page_brand.get('id'), (page_season or {}).get('id'), page_episodes)):
                    if entry in seen:
                        continue
                    seen.add(entry)
                    yield self.url_result(
                        f'{self._BASE_URL}/{entry[0]}/{entry[1]}', SmotrimIE.ie_key()
                        if entry[0] == 'video' else SmotrimAudioIE.ie_key())

            yield from add_entries(episodes, brand, season, webpage)
            for section_url in section_urls:
                section_webpage, section_urlh = self._download_webpage_handle(section_url, playlist_id)
                section_brand, section_season, section_episodes, _ = self._playlist_page(
                    section_webpage, playlist_id, section_urlh.url)
                yield from add_entries(section_episodes, section_brand, section_season, section_webpage)

        return self.playlist_result(
            entries(), playlist_id, brand.get('title'), brand.get('description'),
            thumbnail=self._first_url(brand, ('poster', 'picture'), ('poster', 'main')),
            season=(season or {}).get('nameSubtitle') or (season or {}).get('title'))
