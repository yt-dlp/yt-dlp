import functools
import json
import re
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    OnDemandPagedList,
    clean_html,
    determine_ext,
    extract_attributes,
    int_or_none,
    parse_iso8601,
    str_or_none,
    unescapeHTML,
    url_or_none,
    urljoin,
)
from ..utils.traversal import (
    find_element,
    find_elements,
    require,
    traverse_obj,
)


class SmotrimBaseIE(InfoExtractor):
    _BASE_URL = 'https://smotrim.ru'
    _GEO_BYPASS = False
    _GEO_COUNTRIES = ['RU']

    def _extract_from_smotrim_api(self, typ, item_id):
        path = f'data{typ.replace("-", "")}/{"uid" if typ == "live" else "id"}'
        data = self._download_json(
            f'https://player.smotrim.ru/iframe/{path}/{item_id}/sid/smotrim', item_id)
        media = traverse_obj(data, ('data', 'playlist', 'medialist', -1, {dict}))
        if traverse_obj(media, ('locked', {bool})):
            self.raise_login_required()
        if error_msg := traverse_obj(media, ('errors', {clean_html})):
            self.raise_geo_restricted(error_msg, countries=self._GEO_COUNTRIES)

        webpage_url = traverse_obj(data, ('data', 'template', 'share_url', {url_or_none}))
        webpage = self._download_webpage(webpage_url, item_id)
        common = {
            'thumbnail': self._html_search_meta(['og:image', 'twitter:image'], webpage, default=None),
            **traverse_obj(media, {
                'id': ('id', {str_or_none}),
                'title': (('episodeTitle', 'title'), {clean_html}, filter, any),
                'channel_id': ('channelId', {str_or_none}),
                'description': ('anons', {clean_html}, filter),
                'season': ('season', {clean_html}, filter),
                'series': (('brand_title', 'brandTitle'), {clean_html}, filter, any),
                'series_id': ('brand_id', {str_or_none}),
            }),
        }

        if typ == 'audio':
            bookmark = self._search_json(
                r'class="bookmark"[^>]+value\s*=\s*"', webpage,
                'bookmark', item_id, default={}, transform_source=unescapeHTML)

            metadata = {
                'vcodec': 'none',
                **common,
                **traverse_obj(media, {
                    'ext': ('audio_url', {determine_ext(default_ext='mp3')}),
                    'duration': ('duration', {int_or_none}),
                    'url': ('audio_url', {url_or_none}),
                }),
                **traverse_obj(bookmark, {
                    'title': ('subtitle', {clean_html}),
                    'timestamp': ('published', {parse_iso8601}),
                }),
            }
        elif typ == 'audio-live':
            metadata = {
                'ext': 'mp3',
                'url': traverse_obj(media, ('source', 'auto', {url_or_none})),
                'vcodec': 'none',
                **common,
            }
        else:
            formats, subtitles = [], {}
            for m3u8_url in traverse_obj(media, (
                'sources', 'm3u8', {dict.values}, ..., {url_or_none},
            )):
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    m3u8_url, item_id, 'mp4', m3u8_id='hls', fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)

            metadata = {
                'formats': formats,
                'subtitles': subtitles,
                **self._search_json_ld(webpage, item_id),
                **common,
            }

        return {
            'age_limit': traverse_obj(data, ('data', 'age_restrictions', {int_or_none})),
            'is_live': typ in ('audio-live', 'live'),
            'tags': traverse_obj(webpage, (
                {find_elements(cls='tags-list__link')}, ..., {clean_html}, filter, all, filter)),
            'webpage_url': webpage_url,
            **metadata,
        }


class SmotrimIE(SmotrimBaseIE):
    IE_NAME = 'smotrim'
    _VALID_URL = r'(?:https?:)?//(?:(?:player|www)\.)?smotrim\.ru(?:/iframe)?/video(?:/id)?/(?P<id>\d+)'
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
            'tags': 'mincount:6',
            'thumbnail': r're:https?://cdn-st\d+\.smotrim\.ru/.+\.(?:jpg|png)',
            'timestamp': 1466771100,
            'upload_date': '20160624',
            'view_count': int,
        },
    }, {
        'url': 'https://player.smotrim.ru/iframe/video/id/2988590',
        'info_dict': {
            'id': '2988590',
            'ext': 'mp4',
            'title': 'Трейлер',
            'age_limit': 16,
            'description': 'md5:6af7e68ecf4ed7b8ff6720d20c4da47b',
            'duration': 30,
            'series': 'Мы в разводе',
            'series_id': '71624',
            'tags': 'mincount:5',
            'thumbnail': r're:https?://cdn-st\d+\.smotrim\.ru/.+\.(?:jpg|png)',
            'timestamp': 1750670040,
            'upload_date': '20250623',
            'view_count': int,
            'webpage_url': 'https://smotrim.ru/video/2988590',
        },
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://smotrim.ru/article/2813445',
        'info_dict': {
            'id': '2431846',
            'ext': 'mp4',
            'title': 'Съёмки первой программы "Большие и маленькие"',
            'description': 'md5:446c9a5d334b995152a813946353f447',
            'duration': 240,
            'series': 'Новости культуры',
            'series_id': '19725',
            'tags': 'mincount:6',
            'thumbnail': r're:https?://cdn-st\d+\.smotrim\.ru/.+\.(?:jpg|png)',
            'timestamp': 1656054443,
            'upload_date': '20220624',
            'view_count': int,
            'webpage_url': 'https://smotrim.ru/video/2431846',
        },
    }, {
        'url': 'https://www.vesti.ru/article/4642878',
        'info_dict': {
            'id': '3007209',
            'ext': 'mp4',
            'title': 'Иностранные мессенджеры используют не только мошенники, но и вербовщики',
            'description': 'md5:74ab625a0a89b87b2e0ed98d6391b182',
            'duration': 265,
            'series': 'Вести. Дежурная часть',
            'series_id': '5204',
            'tags': 'mincount:6',
            'thumbnail': r're:https?://cdn-st\d+\.smotrim\.ru/.+\.(?:jpg|png)',
            'timestamp': 1754756280,
            'upload_date': '20250809',
            'view_count': int,
            'webpage_url': 'https://smotrim.ru/video/3007209',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        return self._extract_from_smotrim_api('video', video_id)


class SmotrimAudioIE(SmotrimBaseIE):
    IE_NAME = 'smotrim:audio'
    _VALID_URL = r'https?://(?:(?:player|www)\.)?smotrim\.ru(?:/iframe)?/audio(?:/id)?/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://smotrim.ru/audio/2573986',
        'md5': 'e28d94c20da524e242b2d00caef41a8e',
        'info_dict': {
            'id': '2573986',
            'ext': 'mp3',
            'title': 'Радиоспектакль',
            'description': 'md5:4bcaaf7d532bc78f76e478fad944e388',
            'duration': 3072,
            'series': 'Морис Леблан. Арсен Люпен, джентльмен-грабитель',
            'series_id': '66461',
            'tags': 'mincount:7',
            'thumbnail': r're:https?://cdn-st\d+\.smotrim\.ru/.+\.(?:jpg|png)',
            'timestamp': 1624884358,
            'upload_date': '20210628',
        },
    }, {
        'url': 'https://player.smotrim.ru/iframe/audio/id/2860468',
        'md5': '5a6bc1fa24c7142958be1ad9cfae58a8',
        'info_dict': {
            'id': '2860468',
            'ext': 'mp3',
            'title': 'Колобок и музыкальная игра "Терем-теремок"',
            'duration': 1501,
            'series': 'Веселый колобок',
            'series_id': '68880',
            'tags': 'mincount:4',
            'thumbnail': r're:https?://cdn-st\d+\.smotrim\.ru/.+\.(?:jpg|png)',
            'timestamp': 1755925800,
            'upload_date': '20250823',
            'webpage_url': 'https://smotrim.ru/audio/2860468',
        },
    }]

    def _real_extract(self, url):
        audio_id = self._match_id(url)

        return self._extract_from_smotrim_api('audio', audio_id)


class SmotrimLiveIE(SmotrimBaseIE):
    IE_NAME = 'smotrim:live'
    _VALID_URL = r'''(?x:
        (?:https?:)?//
            (?:(?:(?:test)?player|www)\.)?
            (?:
                smotrim\.ru|
                vgtrk\.com
            )
            (?:/iframe)?/
            (?P<type>
                channel|
                (?:audio-)?live
            )
            (?:/u?id)?/(?P<id>[\da-f-]+)
    )'''
    _EMBED_REGEX = [fr'<iframe\b[^>]+\bsrc=["\'](?P<url>{_VALID_URL})']
    _TESTS = [{
        'url': 'https://smotrim.ru/channel/76',
        'info_dict': {
            'id': '1661',
            'ext': 'mp4',
            'title': str,
            'channel_id': '76',
            'description': 'Смотрим прямой эфир «Москва 24»',
            'display_id': '76',
            'live_status': 'is_live',
            'thumbnail': r're:https?://cdn-st\d+\.smotrim\.ru/.+\.(?:jpg|png)',
            'timestamp': int,
            'upload_date': str,
        },
        'params': {'skip_download': 'Livestream'},
    }, {
        # Radio
        'url': 'https://smotrim.ru/channel/81',
        'info_dict': {
            'id': '81',
            'ext': 'mp3',
            'title': str,
            'channel_id': '81',
            'live_status': 'is_live',
            'thumbnail': r're:https?://cdn-st\d+\.smotrim\.ru/.+\.(?:jpg|png)',
        },
        'params': {'skip_download': 'Livestream'},
    }, {
        # Sometimes geo-restricted to Russia
        'url': 'https://player.smotrim.ru/iframe/live/uid/381308c7-a066-4c4f-9656-83e2e792a7b4',
        'info_dict': {
            'id': '19201',
            'ext': 'mp4',
            'title': str,
            'channel_id': '4',
            'description': 'Смотрим прямой эфир «Россия К»',
            'display_id': '381308c7-a066-4c4f-9656-83e2e792a7b4',
            'live_status': 'is_live',
            'thumbnail': r're:https?://cdn-st\d+\.smotrim\.ru/.+\.(?:jpg|png)',
            'timestamp': int,
            'upload_date': str,
            'webpage_url': 'https://smotrim.ru/channel/4',
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

        if typ == 'live' and re.fullmatch(r'[0-9]+', display_id):
            url = self._request_webpage(url, display_id).url
            typ = self._match_valid_url(url).group('type')

        if typ == 'channel':
            webpage = self._download_webpage(url, display_id)
            src_url = traverse_obj(webpage, ((
                ({find_element(cls='main-player__frame', html=True)}, {extract_attributes}, 'src'),
                ({find_element(cls='audio-play-button', html=True)},
                    {extract_attributes}, 'value', {urllib.parse.unquote}, {json.loads}, 'source'),
            ), any, {self._proto_relative_url}, {url_or_none}, {require('src URL')}))
            typ, video_id = self._match_valid_url(src_url).group('type', 'id')
        else:
            video_id = display_id

        return {
            'display_id': display_id,
            **self._extract_from_smotrim_api(typ, video_id),
        }


class SmotrimPlaylistIE(SmotrimBaseIE):
    IE_NAME = 'smotrim:playlist'
    _PAGE_SIZE = 15
    _VALID_URL = r'https?://smotrim\.ru/(?P<type>brand|podcast)/(?P<id>\d+)/?(?P<season>[\w-]+)?'
    _TESTS = [{
        # Video
        'url': 'https://smotrim.ru/brand/64356',
        'info_dict': {
            'id': '64356',
            'title': 'Большие и маленькие',
        },
        'playlist_mincount': 55,
    }, {
        # Video, season
        'url': 'https://smotrim.ru/brand/65293/3-sezon',
        'info_dict': {
            'id': '65293',
            'title': 'Спасская',
            'season': '3 сезон',
        },
        'playlist_count': 16,
    }, {
        # Audio
        'url': 'https://smotrim.ru/brand/68880',
        'info_dict': {
            'id': '68880',
            'title': 'Веселый колобок',
        },
        'playlist_mincount': 156,
    }, {
        # Podcast
        'url': 'https://smotrim.ru/podcast/8021',
        'info_dict': {
            'id': '8021',
            'title': 'Сила звука',
        },
        'playlist_mincount': 27,
    }]

    def _fetch_page(self, endpoint, key, playlist_id, page):
        page += 1
        items = self._download_json(
            f'{self._BASE_URL}/api/{endpoint}', playlist_id,
            f'Downloading page {page}', query={
                key: playlist_id,
                'limit': self._PAGE_SIZE,
                'page': page,
            },
        )

        for link in traverse_obj(items, ('contents', -1, 'list', ..., 'link', {str})):
            yield self.url_result(urljoin(self._BASE_URL, link))

    def _real_extract(self, url):
        playlist_type, playlist_id, season = self._match_valid_url(url).group('type', 'id', 'season')
        key = 'rubricId' if playlist_type == 'podcast' else 'brandId'
        webpage = self._download_webpage(url, playlist_id)
        playlist_title = self._html_search_meta(['og:title', 'twitter:title'], webpage, default=None)

        if season:
            return self.playlist_from_matches(traverse_obj(webpage, (
                {find_elements(tag='a', attr='href', value=r'/video/\d+', html=True, regex=True)},
                ..., {extract_attributes}, 'href', {str},
            )), playlist_id, playlist_title, season=traverse_obj(webpage, (
                {find_element(cls='seasons__item seasons__item--selected')}, {clean_html},
            )), ie=SmotrimIE, getter=urljoin(self._BASE_URL))

        if traverse_obj(webpage, (
            {find_element(cls='brand-main-item__videos')}, {clean_html}, filter,
        )):
            endpoint = 'videos'
        else:
            endpoint = 'audios'

        return self.playlist_result(OnDemandPagedList(
            functools.partial(self._fetch_page, endpoint, key, playlist_id), self._PAGE_SIZE), playlist_id, playlist_title)
