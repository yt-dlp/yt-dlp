import itertools
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    UnsupportedError,
    clean_html,
    determine_ext,
    float_or_none,
    int_or_none,
    join_nonempty,
    orderedSet,
    parse_iso8601,
    str_or_none,
    url_or_none,
    urljoin,
)
from ..utils.traversal import find_element, traverse_obj


class MxplayerBaseIE(InfoExtractor):
    _BASE_URL = 'https://www.mxplayer.in'
    _GEO_BYPASS = False
    _GEO_COUNTRIES = ['IN']

    def _extract_mxs(self, url, item_id):
        webpage = self._download_webpage(url, item_id)
        if error_msg := traverse_obj(webpage, (
            {find_element(cls='sub-message')}, {clean_html}, filter,
        )):
            self.raise_geo_restricted(error_msg, countries=self._GEO_COUNTRIES)

        return self._search_json(r'window\.__mxs__\s*=', webpage, 'mxs', item_id)


class MxplayerIE(MxplayerBaseIE):
    IE_NAME = 'mxplayer'
    IE_DESC = 'Amazon MX Player'

    _VALID_URL = r'''(?x)
        https?://(?:www\.)?mxplayer\.in/
        (?:movie|shorts|show/[\w-]+/(?!seasons/)[\w-]+)/
        (?P<display_id>[\w-]+)-(?P<id>[0-9a-f]{32})(?:[/?#]|$)
    '''
    _TESTS = [{
        # show, mxplay
        'url': 'https://www.mxplayer.in/show/watch-my-girlfriend-is-an-alien/season-1/episode-1-online-9d2013d31d5835bb8400e3b3c5e7bb72',
        'info_dict': {
            'id': '9d2013d31d5835bb8400e3b3c5e7bb72',
            'ext': 'mp4',
            'title': 'Episode 1',
            'age_limit': 16,
            'cast': 'count:10',
            'creators': 'count:2',
            'description': 'md5:e90dc55a393f557049284eb36efdb773',
            'display_id': 'episode-1-online',
            'episode': 'Episode 1',
            'episode_number': 1,
            'duration': 2451,
            'genres': 'count:8',
            'release_date': '20241201',
            'release_timestamp': 1733077800,
            'season': 'Season 1',
            'season_number': 1,
            'series': 'My Girlfriend Is An Alien',
            'tags': 'count:31',
            'thumbnail': r're:https?://.+',
            'timestamp': 1732435849,
            'upload_date': '20241124',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        # show, mxplay, NFSW
        'url': 'https://www.mxplayer.in/show/watch-miya-biwi-aur-murder/season-1/episode-1-online-ca17972f052449de6633129ddd7db90b',
        'info_dict': {
            'id': 'ca17972f052449de6633129ddd7db90b',
            'ext': 'mp4',
            'title': 'Episode 1',
            'age_limit': 18,
            'cast': 'count:10',
            'creators': 'count:1',
            'description': 'md5:bd8e55b81094e55026eb0c4f702c32cc',
            'display_id': 'episode-1-online',
            'episode': 'Episode 1',
            'episode_number': 1,
            'duration': 1348,
            'genres': 'count:4',
            'release_date': '20220630',
            'release_timestamp': 1656613800,
            'season': 'Season 1',
            'season_number': 1,
            'series': 'Miya Biwi Aur Murder',
            'tags': 'count:12',
            'thumbnail': r're:https?://.+',
            'timestamp': 1656581738,
            'upload_date': '20220630',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        # shorts, mxplay
        'url': 'https://www.mxplayer.in/shorts/watch-official-trailer-made-in-india-a-titan-story-online-c36b0ad18e56f1da0743ad826fe9e14b',
        'info_dict': {
            'id': 'c36b0ad18e56f1da0743ad826fe9e14b',
            'ext': 'mp4',
            'title': 'Official Trailer | Made In India: A Titan Story',
            'age_limit': 13,
            'description': 'md5:37924586e54d6e86a6e991048aec5442',
            'display_id': 'watch-official-trailer-made-in-india-a-titan-story-online',
            'episode': 'Episode 0',
            'episode_number': 0,
            'duration': 125,
            'genres': 'count:2',
            'release_date': '20260525',
            'release_timestamp': 1779733800,
            'tags': 'count:3',
            'thumbnail': r're:https?://.+',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        # movie, mxplay
        'url': 'https://www.mxplayer.in/movie/watch-thiruchitrambalam-movie-online-fbba39c1fdf8b14cffcea05f0635da84',
        'info_dict': {
            'id': 'fbba39c1fdf8b14cffcea05f0635da84',
            'ext': 'mp4',
            'title': 'Thiruchitrambalam',
            'age_limit': 13,
            'cast': 'count:7',
            'creators': 'count:1',
            'description': 'md5:66c24674756099adbecd1e56cfa9d6e6',
            'display_id': 'watch-thiruchitrambalam-movie-online',
            'episode': 'Episode 0',
            'episode_number': 0,
            'duration': 7894,
            'genres': 'count:3',
            'release_date': '20220817',
            'release_timestamp': 1660761000,
            'tags': 'count:8',
            'thumbnail': r're:https?://.+',
            'timestamp': 1759808876,
            'upload_date': '20251007',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        # movie, thirdParty
        'url': 'https://www.mxplayer.in/movie/watch-drishyam-2-hindi-movie-online-2c580670b2104d156e2d9a3fd42a413e',
        'info_dict': {
            'id': '2c580670b2104d156e2d9a3fd42a413e',
            'ext': 'mp4',
            'title': 'Drishyam 2 (Hindi)',
            'age_limit': 13,
            'cast': 'count:10',
            'creators': 'count:1',
            'description': 'md5:b4f803532ea357b78ca183d0829eca2a',
            'display_id': 'watch-drishyam-2-hindi-movie-online',
            'episode': 'Episode 0',
            'episode_number': 0,
            'duration': 8399,
            'genres': 'count:3',
            'release_date': '20221117',
            'release_timestamp': 1668709800,
            'tags': 'count:4',
            'thumbnail': r're:https?://.+',
            'timestamp': 1736823124,
            'upload_date': '20250114',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        display_id, video_id = self._match_valid_url(url).group('display_id', 'id')
        mxs = self._extract_mxs(url, video_id)

        config = traverse_obj(mxs, ('config', {dict}))
        cdn_base = traverse_obj(config, (
            'videoCdnBaseUrl', {url_or_none}, {lambda x: f'{x.rstrip("/")}/'}))
        img_base = traverse_obj(config, (
            'imageBaseUrl', {url_or_none}, {lambda x: f'{x.rstrip("/")}/'}))

        entities = traverse_obj(mxs, ('entities', video_id, {dict}))
        stream = traverse_obj(entities, ('stream', {dict}))
        if traverse_obj(stream, ('drmProtect', {bool})):
            self.report_drm(video_id)

        formats, subtitles = [], {}
        for manifest_url in traverse_obj(stream, ((
            ('thirdParty', ..., {url_or_none}),
            ((None, 'mxplay'), ('hls', 'dash'), 'high', {urljoin(cdn_base)}),
        ), all, {orderedSet})):
            ext = determine_ext(manifest_url)
            if ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    manifest_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
            elif ext == 'mpd':
                fmts, subs = self._extract_mpd_formats_and_subtitles(
                    manifest_url, video_id, mpd_id='dash', fatal=False)
                for fmt in fmts:
                    if tbr := traverse_obj(fmt, ('tbr', {float_or_none})):
                        fmt['tbr'] = tbr / 4.2
            else:
                self.report_warning(f'Unsupported stream type: {ext}')
                continue

            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)
        self._remove_duplicate_formats(formats)

        return {
            'id': video_id,
            'display_id': display_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(entities, {
                'title': ('title', {clean_html}, filter),
                'age_limit': ('rating', {int_or_none}),
                'description': ('description', {clean_html}, filter),
                'duration': ('duration', {int_or_none}),
                'episode_number': ('sequence', {int_or_none}),
                'genres': ('genres', ..., {clean_html}, filter, all, filter),
                'release_timestamp': ('releaseDate', {parse_iso8601}),
                'tags': ('tags', ..., 'name', {clean_html}, filter, all, filter),
                'thumbnails': (('imageInfo', 'titleContentImageInfo'), ..., {
                    'id': ('type', {str_or_none}),
                    'height': ('height', {int_or_none}),
                    'url': ('url', {urljoin(img_base)}),
                    'width': ('width', {int_or_none}),
                }),
                'timestamp': ('publishTime', {parse_iso8601}),
                'view_count': ('viewCount', {int_or_none}),
            }),
            **traverse_obj(entities, ('container', {
                'season': ('title', {clean_html}, filter),
                'season_number': ('sequence', {int_or_none}),
                'series': ('container', 'title', {clean_html}, filter),
            })),
            **traverse_obj(entities, ('contributors', {
                'cast': (lambda _, v: v['type'] == 'actor', 'name', {clean_html}, filter, all, filter),
                'creators': (lambda _, v: v['type'] == 'director', 'name', {clean_html}, filter, all, filter),
            })),
        }


class MxplayerSeasonIE(MxplayerBaseIE):
    IE_NAME = 'mxplayer:season'

    _PAGE_SIZE = 10
    _VALID_URL = r'https?://(?:www\.)?mxplayer\.in/show/[\w-]+/seasons/[\w-]+-(?P<id>[0-9a-f]{32})(?:[/?#]|$)'
    _TESTS = [{
        'url': 'https://www.mxplayer.in/show/watch-campus-beats/seasons/season-4-925794ae840c597b3c36f2d8f2f138b8',
        'info_dict': {
            'id': '925794ae840c597b3c36f2d8f2f138b8',
            'title': 'Campus Beats - Season 4',
        },
        'playlist_mincount': 15,
    }]

    def _entries(self, entities, season_id):
        query = None
        api_url = traverse_obj(entities, (
            'tabs', ..., 'api', {urljoin('https://api.mxplayer.in/v1/web/')}, any))

        for page in itertools.count(1):
            season_data = self._download_json(
                api_url, season_id, f'Downloading Page {page}', query=query)

            share_urls = traverse_obj(season_data, (
                'items', ..., 'shareUrl', {urljoin(f'{self._BASE_URL}/')}))
            for share_url in share_urls:
                yield self.url_result(share_url, MxplayerRedirectIE)
            if len(share_urls) < self._PAGE_SIZE:
                break

            query = traverse_obj(season_data, ('next', {urllib.parse.parse_qs}))
            if not query:
                break

    def _real_extract(self, url):
        season_id = self._match_id(url)
        mxs = self._extract_mxs(url, season_id)

        entities = traverse_obj(mxs, ('entities', season_id, {dict}))
        series_title = traverse_obj(entities, ('container', 'title', {clean_html}))
        season_title = traverse_obj(entities, ('title', {clean_html}))

        return self.playlist_result(
            self._entries(entities, season_id),
            season_id, join_nonempty(series_title, season_title, delim=' - '))


class MxplayerShowIE(MxplayerBaseIE):
    IE_NAME = 'mxplayer:show'

    _VALID_URL = r'https?://(?:www\.)?mxplayer\.in/show/[\w-]+-(?P<id>[0-9a-f]{32})(?:[/?#]|$)'
    _TESTS = [{
        'url': 'https://www.mxplayer.in/show/watch-bhaukaal-series-online-775ad3b682fde6a608559a60986b230d',
        'info_dict': {
            'id': '775ad3b682fde6a608559a60986b230d',
            'title': 'Bhaukaal',
        },
        'playlist_mincount': 2,
    }]

    def _entries(self, entities):
        for season_id in traverse_obj(entities, (
            'tabs', ..., 'containers', ..., 'id', {str_or_none},
        )):
            yield self.url_result(
                f'{self._BASE_URL}/detail/season/{season_id}', MxplayerRedirectIE)

    def _real_extract(self, url):
        show_id = self._match_id(url)
        mxs = self._extract_mxs(url, show_id)

        entities = traverse_obj(mxs, ('entities', show_id, {dict}))

        return self.playlist_result(
            self._entries(entities), show_id,
            traverse_obj(entities, ('title', {clean_html}, filter)))


class MxplayerRedirectIE(MxplayerBaseIE):
    IE_NAME = 'mxplayer:redirect'
    IE_DESC = False

    _IE_MAP = {
        'episode': MxplayerIE,
        'movie': MxplayerIE,
        'season': MxplayerSeasonIE,
        'shorts': MxplayerIE,
        'tvshow': MxplayerShowIE,
    }
    _VALID_URL = rf'https?://(?:www\.)?mxplayer\.in/detail/(?P<type>{"|".join(_IE_MAP)})/(?P<id>[0-9a-f]{{32}})(?:[/?#]|$)'
    _TESTS = [{
        # episode
        # https://www.mxplayer.in/show/watch-that-time-i-got-reincarnated-as-a-slime/season-2/megiddo-online-3eda0b3baf27f2892d3fca2fd650fb95
        'url': 'https://www.mxplayer.in/detail/episode/3eda0b3baf27f2892d3fca2fd650fb95',
        'info_dict': {
            'id': '3eda0b3baf27f2892d3fca2fd650fb95',
            'ext': 'mp4',
            'title': 'Megiddo',
            'age_limit': 16,
            'cast': 'count:6',
            'creators': 'count:11',
            'description': 'md5:f4ac8210c2e7bdcaab3b34636cf754b4',
            'display_id': 'megiddo-online',
            'episode': 'Episode 10',
            'episode_number': 10,
            'duration': 1427,
            'genres': 'count:6',
            'release_date': '20210315',
            'release_timestamp': 1615833000,
            'season': 'Season 2',
            'season_number': 2,
            'series': 'That Time I Got Reincarnated As A Slime',
            'tags': 'count:21',
            'thumbnail': r're:https?://.+',
            'timestamp': 1774843170,
            'upload_date': '20260330',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        # movie
        # https://www.mxplayer.in/movie/watch-sardar-udham-movie-online-0c586053d7ac563ca911ddfe08cf922f
        'url': 'https://www.mxplayer.in/detail/movie/0c586053d7ac563ca911ddfe08cf922f',
        'info_dict': {
            'id': '0c586053d7ac563ca911ddfe08cf922f',
            'ext': 'mp4',
            'title': 'Sardar Udham',
            'age_limit': 13,
            'cast': 'count:6',
            'creators': 'count:1',
            'description': 'md5:58f0d90f802898aaf328ac2942e878e5',
            'display_id': 'watch-sardar-udham-movie-online',
            'episode': 'Episode 0',
            'episode_number': 0,
            'duration': 9770,
            'genres': 'count:3',
            'release_date': '20211015',
            'release_timestamp': 1634322600,
            'tags': 'count:4',
            'thumbnail': r're:https?://.+',
            'timestamp': 1739952608,
            'upload_date': '20250219',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        # shorts
        # https://www.mxplayer.in/shorts/watch-official-trailer-lafangey-sapne-dosti-duniya-online-55c77863e406c7b71f6bab28f7fbbe85
        'url': 'https://www.mxplayer.in/detail/shorts/55c77863e406c7b71f6bab28f7fbbe85',
        'info_dict': {
            'id': '55c77863e406c7b71f6bab28f7fbbe85',
            'ext': 'mp4',
            'title': 'Official Trailer| Lafangey - Sapne, Dosti, Duniya',
            'age_limit': 18,
            'description': 'md5:623d53e4543155dd732e96587711481c',
            'display_id': 'watch-official-trailer-lafangey-sapne-dosti-duniya-online',
            'episode': 'Episode 0',
            'episode_number': 0,
            'duration': 118,
            'genres': 'count:2',
            'release_date': '20250601',
            'release_timestamp': 1748802600,
            'tags': 'count:3',
            'thumbnail': r're:https?://.+',
            'view_count': int,
        },
        'params': {'skip_download': True},
    }, {
        # season
        # https://www.mxplayer.in/show/watch-demon-slayer/seasons/season-3-41a6d7432bea96f2f0d06a625b39d9b1
        'url': 'https://www.mxplayer.in/detail/season/41a6d7432bea96f2f0d06a625b39d9b1',
        'info_dict': {
            'id': '41a6d7432bea96f2f0d06a625b39d9b1',
            'title': 'Demon Slayer - Season 3',
        },
        'playlist_mincount': 11,
    }, {
        # tvshow
        # https://www.mxplayer.in/show/watch-my-hero-academia-series-online-e7c68fb3951e61986af073a719c2ee4f
        'url': 'https://www.mxplayer.in/detail/tvshow/e7c68fb3951e61986af073a719c2ee4f',
        'info_dict': {
            'id': 'e7c68fb3951e61986af073a719c2ee4f',
            'title': 'My Hero Academia',
        },
        'playlist_mincount': 4,
    }]

    def _real_extract(self, url):
        redirect_type, redirect_id = self._match_valid_url(url).group('type', 'id')
        ie = self._IE_MAP[redirect_type]

        detail = self._download_json(
            'https://seo.mxplayer.in/v1/api/seo/get-url-details',
            redirect_id, query={'url': urllib.parse.urlsplit(url).path})

        if redirect_url := traverse_obj(detail, (
            'data', 'redirect', {urljoin(f'{self._BASE_URL}/')},
        )):
            if self.suitable(redirect_url):
                raise UnsupportedError(redirect_url)
            return self.url_result(redirect_url, ie)

        raise ExtractorError('Unable to resolve redirect URL')
