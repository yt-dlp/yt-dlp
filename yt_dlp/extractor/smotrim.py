import hashlib
import itertools
import json
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    determine_ext,
    extract_attributes,
    int_or_none,
    str_or_none,
    url_or_none,
    urljoin,
)
from ..utils.traversal import (
    find_element,
    find_elements,
    traverse_obj,
)


class SmotrimBaseIE(InfoExtractor):
    _BASE_URL = 'https://smotrim.ru'
    _VALID_URL_BASE = r'https?://(?:(?:player|www)\.)?smotrim\.ru(?:(?:/iframe)?/{type}(?:/id)?/)?(?:(?:/[^#]+)?/?#playing_{type}=)?(?P<id>\d+)'
    _GEO_BYPASS = False
    _GEO_COUNTRIES = ['RU']

    def _extract_from_smotrim_api(self, url, typ, item_id, webpage_needed=True, **kwargs):
        data = self._download_json(f'https://player-api.smotrim.ru/api/v1/{typ}/{item_id}', item_id, **kwargs)
        notice = data.get('notice')
        status = data.get('status')
        if status != 'OK' and notice:
            if 'подписке' in notice:
                self.raise_login_required(notice)
            elif typ == 'channel' and status == 'CHANNEL_NOT_FOUND':
                raise ExtractorError(f'Channel {item_id} not found', expected=True)
            raise ExtractorError(notice)
        media = data.get('data')

        formats, subtitles = [], {}
        if fmt_url := traverse_obj(media, ('streams', 'm3u8', {url_or_none})):
            formats.extend(self._extract_m3u8_formats(fmt_url, item_id))

        for sub in traverse_obj(media, ('subtitles', lambda _, y: y.get('vtt') or y.get('srt')), default=[]):
            lang = sub.get('code')
            for styp in ('vtt', 'srt'):
                subtitles.setdefault(lang, []).append(
                    traverse_obj(sub, {
                        'url': (styp, {url_or_none}),
                        'ext': (styp, {determine_ext(default_ext=styp)}),
                        'name': ('title', {str_or_none}),
                    }),
                )

        thumbnails = []
        for thumb_id, thumb_url in traverse_obj(media, ('episode', 'splash', {dict.items}), default=[]):
            thumbnails.append({'id': thumb_id, 'url': thumb_url})

        return {
            'id': item_id,
            **traverse_obj(media, {
                'title': ((('episode', 'title'), ('title')), any, {str_or_none}),
                'series': ('brand', 'title', {str_or_none}),
                'series_id': ('brand', 'id', {str_or_none}),
                'duration': ('duration', {int_or_none}),
                'age_limit': ('ageRestriction', {int_or_none}),
            }),
            **(self._search_json_ld(self._download_webpage(url, item_id), item_id, fatal=False) if webpage_needed else {}),
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': subtitles,
            'is_live': typ in ('channel', 'audo-live', 'live'),
        }

    def _extract_from_iframe_api(self, typ, item_id, fatal=True):
        path = f'data{typ.replace("-", "")}/{"uid" if typ == "live" else "id"}'
        data = self._download_json(
            f'https://player.smotrim.ru/iframe/{path}/{item_id}', item_id)
        media = traverse_obj(data, ('data', 'playlist', 'medialist', -1, {dict}))
        if traverse_obj(media, ('locked', {bool})):
            if fatal is False:
                self.report_warning(self._login_hint())
                return {}
            self.raise_login_required()
        if error_msg := traverse_obj(data, ('errors', {str_or_none})):
            msg = f'Iframe api says: {error_msg}'
            if fatal is False:
                self.report_warning(msg)
                return {}
            raise ExtractorError(msg)
        common = {
            **traverse_obj(media, {
                'id': ('id', {str_or_none}),
                'title': (('episodeTitle', 'title'), {clean_html}, filter, any),
                'channel_id': ('channelId', {str_or_none}),
                'description': ('anons', {clean_html}, filter),
                'season': ('season', {clean_html}, filter),
                'series': (('brand_title', 'brandTitle'), {clean_html}, filter, any),
                'series_id': ('brand_id', {str_or_none}),
                'duration': ('duration', {int_or_none}),
                'chapters': ('chapters', {list}),
                'thumbnail': ('picture', {url_or_none}),
            }),
            'webpage_url': traverse_obj(data, ('data', (('playlist', 'def_share_url'), ('template', 'share_url')), any, {url_or_none})),
            'tags': traverse_obj(data, ('data', 'tags'), default='').split(':'),
        }

        if typ == 'audio':
            thumbnails = []
            for thumb_id, thumb_url in traverse_obj(media, ('brand_pictures', {dict.items}), default=[]):
                thumbnails.append({'id': thumb_id, 'url': thumb_url})
            metadata = {
                'vcodec': 'none',
                **common,
                **traverse_obj(media, {
                    'ext': ('audio_url', {determine_ext(default_ext='mp3')}),
                    'duration': ('duration', {int_or_none}),
                    'url': ('audio_url', {url_or_none}),
                    'title': ('title', {str_or_none}),
                }),
                'thumbnails': thumbnails,
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
                    m3u8_url, item_id, 'mp4', m3u8_id='hls', fatal=fatal)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)

            metadata = {
                'formats': formats,
                'subtitles': subtitles,
                **common,
            }

        return {
            'age_limit': traverse_obj(data, ('data', 'age_restrictions', {int_or_none})),
            'is_live': typ in ('audio-live', 'live'),
            **metadata,
        }


class SmotrimIE(SmotrimBaseIE):
    IE_NAME = 'smotrim'
    _VALID_URL = SmotrimBaseIE._VALID_URL_BASE.format(type='video')
    _EMBED_REGEX = [fr'<iframe\b[^>]+\bsrc=["\'](?P<url>{_VALID_URL})']
    _TESTS = [{
        'url': 'https://smotrim.ru/video/1539617',
        'info_dict': {
            'id': '1539617',
            'ext': 'mp4',
            'title': 'Урок №16',
            'duration': 2631,
            'thumbnail': 'https://cdn-st2.smotrim.ru/vh/pictures/b/107/733/5.jpg',
            'chapters': [],
            'tags': ['27163', '19225', '18902', '4677', '3720', '1164', '212699'],
            'series': 'Полиглот. Китайский с нуля за 16 часов!',
            'series_id': '60562',
        },
    }, {
        'url': 'https://player.smotrim.ru/iframe/video/id/3093252',
        'info_dict': {
            'id': '3093252',
            'ext': 'mp4',
            'title': 'Мария Шкапская',
            'description': 'md5:a2ee7b7a9c59bd83dbecf2d69fb083bc',
            'duration': 1573,
            'thumbnail': 'https://cdn-st2.smotrim.ru/vh/pictures/b/108/337/18.jpg',
            'chapters': [],
            'tags': 'count:21',
            'series': 'Невский ковчег. Теория невозможного',
            'series_id': '66925',
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
            'webpage_url': 'https://smotrim.ru/video/2431846',
        },
        'skip': 'iframe removed',
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
            'tags': ['107517', '158874', '98963', '4276', '1063', '3515'],
            'thumbnail': 'https://cdn-st2.smotrim.ru/vh/pictures/b/641/140/9.jpg',
            'chapters': [],
            'webpage_url': 'https://smotrim.ru/video/3007209',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        formats, subtitles = [], {}
        thumbnails = []

        def update_fmts_and_subs(*datas, target_fmts, target_subs):
            for data in datas:
                if subs := data.pop('subtitles', {}):
                    self._merge_subtitles(subs, target=target_subs)
                if fmts := data.pop('formats', []):
                    target_fmts.extend(fmts)

        def update_thumbnails(*datas, target):
            for data in datas:
                if thumb_url := data.pop('thumbnail', None):
                    target.append({
                        'url': thumb_url,
                        'height': data.get('height'),
                        'width': data.get('width'),
                    })

                if thumbs := data.pop('thumbnails', None):
                    target.extend(thumbs)

        smotrim_data = self._extract_from_smotrim_api(url, 'video', video_id)
        iframe_data = self._extract_from_iframe_api('video', video_id, fatal=False)
        update_fmts_and_subs(smotrim_data, iframe_data, target_fmts=formats, target_subs=subtitles)
        update_thumbnails(smotrim_data, iframe_data, target=thumbnails)

        return {
            **smotrim_data,
            **iframe_data,
            'thumbnails': thumbnails,
            'formats': formats,
            'subtitles': subtitles,
        }


class SmotrimAudioIE(SmotrimBaseIE):
    IE_NAME = 'smotrim:audio'
    _VALID_URL = SmotrimBaseIE._VALID_URL_BASE.format(type='audio')
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

        return self._extract_from_iframe_api('audio', audio_id)


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
            return self._extract_from_smotrim_api(url, 'channel', display_id, webpage_needed=False, expected_status=(404))
        else:
            video_id = display_id

        return {
            'display_id': display_id,
            **self._extract_from_iframe_api(typ, video_id),
        }


class SmotrimPlaylistIE(SmotrimBaseIE):
    IE_NAME = 'smotrim:playlist'
    _PAGE_SIZE = 30
    _VALID_URL = r'https?://smotrim\.ru/(?:brand|podcast)/(?P<id>\d+)/?(?P<season>[\w-]+)?'
    _TESTS = [{
        # Video
        'url': 'https://smotrim.ru/brand/64356',
        'info_dict': {
            'id': '64356',
            'title': 'Большие и маленькие культура смотреть онлайн',
        },
        'playlist_mincount': 55,
    }, {
        # Video, season
        'url': 'https://smotrim.ru/brand/65293/season-3',
        'info_dict': {
            'id': '65293',
            'title': 'Сериал Спасская (3 сезон): смотреть онлайн бесплатно в хорошем качестве',
            'season': 'сезон 3',
        },
        'playlist_count': 21,
    }, {
        # Audio
        'url': 'https://smotrim.ru/brand/68880',
        'info_dict': {
            'id': '68880',
            'title': 'Программа для малышей Веселый Колобок на Радио России - все выпуски онлайн',
        },
        'playlist_mincount': 175,
    }, {
        # Podcast
        'url': 'https://smotrim.ru/brand/73273',
        'info_dict': {
            'id': '73273',
            'title': 'Подкаст Мужчина. Руководство по эксплуатации - слушать и смотреть онлайн бесплатно без регистрации',
        },
        'playlist_mincount': 100,
    }, {
        # Audio, season
        # There are 46 entries in total, but currently we didn't use pagination, so it didn't fetch the next page and we don't get extra entries.
        # This can be fix in next commit.
        'url': 'https://smotrim.ru/brand/68880/year-2025',
        'info_dict': {
            'id': '68880',
            'title': 'Радиопрограмма Весёлый колобок: все выпуски за 2025 год - смотреть онлайн бесплатно на «СМОТРИМ»',
            'season': 'сезон 2025',
        },
        'playlist_count': 30,
    }]

    FILTER_EP_QUERY = '''
        query FilterEpisodes(
            $brandId: Int
            $seasonId: Int
            $page: Int = 2
            $first: Int! = 10
            $order: SortOrder = ASC
        ) {
            episodesFilter(
                brand_id: $brandId
                season_id: $seasonId
                first: $first
                page: $page
                orderBy: { column: EPISODES_NUMBER, order: $order }
            ) {
                data {
                    ... on Episode {
                        id
                        title
                        number
                        season { number }
                        audio { publicId }
                        fullVideo { publicId }
                    }
                }
                paginatorInfo {
                    lastPage
                }
            }
        }
    '''

    PODCAST_EP_QUERY = '''
        query BrandMorePodcastEpisodes(
            $brandId: Int!
            $page: Int = 10
            $first: Int = 10
        ) {
            brand(id: $brandId) {
                podcastMaterials(first: $first, page: $page) {
                    data {
                        ... on Episode {
                            id
                            title
                            description
                            number
                            season { number }
                            audio { publicId }
                            fullVideo {
                                ... on Video { publicId }
                            }
                        }
                    }
                    paginatorInfo {
                        hasMorePages
                    }
                }
            }
        }
    '''

    def _pages(self, playlist_id, webpage):
        if self._search_regex(fr'(brand-{playlist_id}-season-single)', webpage, 'is_podcast', default=None):
            all_seasons = (playlist_id,)
            operationName = 'BrandMorePodcastEpisodes'
            body = '611ad92ea2541c7b74674035a0f75c55'
            _QUERY = self.PODCAST_EP_QUERY
            is_podcast = True
        else:
            all_seasons = re.findall(fr'brand-{playlist_id}-season-(\d+)', webpage)
            operationName = 'FilterEpisodes'
            body = '99f8b33d0cb27ed775154699095edad2'
            _QUERY = self.FILTER_EP_QUERY
            is_podcast = False

        for season_id in all_seasons:
            for page_num in itertools.count(1):
                variables = {
                    'brandId': int(playlist_id),
                    'first': self._PAGE_SIZE,
                    'page': page_num,
                    **(
                        {} if is_podcast else {'seasonId': int(season_id)}
                    ),
                }
                # Source https://cdn.smotrim.ru/static/assets/_nuxt/DLtwXC_w.js Current function name 'qR'
                hash_variables = hashlib.md5(
                    json.dumps(dict(sorted(variables.items())), separators=(',', ':')).encode()).hexdigest()
                items = traverse_obj(self._download_json(
                    'https://apis.smotrim.ru/graphql/',
                    playlist_id,
                    f'Downloading page {page_num}',
                    query={
                        'page': operationName,
                        'body': body,
                        'vars': hash_variables,
                    },
                    data=json.dumps({
                        'operationName': operationName,
                        'query': _QUERY,
                        'variables': variables,
                    }).encode(),
                    headers={'Content-Type': 'application/json'},
                ), ('data', 'brand', 'podcastMaterials'), ('data', 'episodesFilter'))

                if not items:
                    break
                yield items

                pagination = items.get('paginatorInfo')
                if pagination.get('lastPage') == page_num or pagination.get('hasMorePages') is False:
                    break

    def entries(self, webpage, playlist_id):
        for item in self._pages(playlist_id, webpage):
            for item_id in traverse_obj(item, ('data', ..., ('audio', 'fullVideo'), 'publicId', {int_or_none})):
                typ = 'video' if '/video/' in webpage else 'audio'
                url = f'{self._BASE_URL}/{typ}/{item_id}'
                yield self.url_result(urljoin(self._BASE_URL, url))

    def _real_extract(self, url):
        playlist_id, season = self._match_valid_url(url).groups()
        webpage = self._download_webpage(url, playlist_id)
        playlist_title = self._html_search_meta(['og:title', 'twitter:title'], webpage, default=None)

        if season:
            return self.playlist_from_matches(traverse_obj(webpage, (
                # TODO: Use paginatipn because sometime this will ( give less entries ) or ( give extra entries because of regex ).
                {find_elements(tag='a', attr='href', value=r'/(?:video|audio)/\d+', html=True, regex=True)},
                ..., {extract_attributes}, 'href', {str},
            )), playlist_id, playlist_title, season=traverse_obj(webpage, (
                {find_element(cls='header__title_subtitle')}, {clean_html},
            )), getter=urljoin(self._BASE_URL))

        return self.playlist_result(self.entries(webpage, playlist_id), playlist_id, playlist_title)
