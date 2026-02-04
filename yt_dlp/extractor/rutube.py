import itertools

from .common import InfoExtractor
from ..utils import (
    UnsupportedError,
    bool_or_none,
    determine_ext,
    int_or_none,
    js_to_json,
    parse_qs,
    str_or_none,
    try_get,
    unified_timestamp,
    url_or_none,
)
from ..utils.traversal import (
    subs_list_to_dict,
    traverse_obj,
)


class RutubeBaseIE(InfoExtractor):
    def _download_api_info(self, video_id, query=None):
        if not query:
            query = {}
        query['format'] = 'json'
        return self._download_json(
            f'https://rutube.ru/api/video/{video_id}/',
            video_id, 'Downloading video JSON',
            'Unable to download video JSON', query=query)

    def _extract_info(self, video, video_id=None, require_title=True):
        title = video['title'] if require_title else video.get('title')

        age_limit = video.get('is_adult')
        if age_limit is not None:
            age_limit = 18 if age_limit is True else 0

        uploader_id = try_get(video, lambda x: x['author']['id'])
        category = try_get(video, lambda x: x['category']['name'])
        description = video.get('description')
        duration = int_or_none(video.get('duration'))

        return {
            'id': video.get('id') or video_id if video_id else video['id'],
            'title': title,
            'description': description,
            'thumbnail': video.get('thumbnail_url'),
            'duration': duration,
            'uploader': try_get(video, lambda x: x['author']['name']),
            'uploader_id': str(uploader_id) if uploader_id else None,
            'timestamp': unified_timestamp(video.get('created_ts')),
            'categories': [category] if category else None,
            'age_limit': age_limit,
            'view_count': int_or_none(video.get('hits')),
            'comment_count': int_or_none(video.get('comments_count')),
            'is_live': bool_or_none(video.get('is_livestream')),
            'chapters': self._extract_chapters_from_description(description, duration),
        }

    def _download_and_extract_info(self, video_id, query=None):
        return self._extract_info(
            self._download_api_info(video_id, query=query), video_id)

    def _download_api_options(self, video_id, query=None):
        if not query:
            query = {}
        query['format'] = 'json'
        return self._download_json(
            f'https://rutube.ru/api/play/options/{video_id}/',
            video_id, 'Downloading options JSON',
            'Unable to download options JSON',
            headers=self.geo_verification_headers(), query=query)

    def _extract_formats_and_subtitles(self, options, video_id):
        formats = []
        subtitles = {}
        for format_id, format_url in options['video_balancer'].items():
            ext = determine_ext(format_url)
            if ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    format_url, video_id, 'mp4', m3u8_id=format_id, fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            elif ext == 'f4m':
                formats.extend(self._extract_f4m_formats(
                    format_url, video_id, f4m_id=format_id, fatal=False))
            else:
                formats.append({
                    'url': format_url,
                    'format_id': format_id,
                })
        for hls_url in traverse_obj(options, ('live_streams', 'hls', ..., 'url', {url_or_none})):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                hls_url, video_id, 'mp4', fatal=False, m3u8_id='hls')
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)
        self._merge_subtitles(traverse_obj(options, ('captions', ..., {
            'id': 'code',
            'url': 'file',
            'name': ('langTitle', {str}),
        }, all, {subs_list_to_dict(lang='ru')})), target=subtitles)
        return formats, subtitles

    def _download_and_extract_formats_and_subtitles(self, video_id, query=None):
        return self._extract_formats_and_subtitles(
            self._download_api_options(video_id, query=query), video_id)


class RutubeIE(RutubeBaseIE):
    IE_NAME = 'rutube'
    IE_DESC = 'Rutube videos'
    _VALID_URL = r'https?://rutube\.ru/(?:(?:live/)?video(?:/private)?|(?:play/)?embed)/(?P<id>[\da-z]{32})'
    _EMBED_REGEX = [r'<iframe[^>]+?src=(["\'])(?P<url>(?:https?:)?//rutube\.ru/(?:play/)?embed/[\da-z]{32}.*?)\1']

    _TESTS = [{
        'url': 'https://rutube.ru/video/3eac3b4561676c17df9132a9a1e62e3e/',
        'info_dict': {
            'id': '3eac3b4561676c17df9132a9a1e62e3e',
            'ext': 'mp4',
            'title': 'Раненный кенгуру забежал в аптеку',
            'description': 'http://www.ntdtv.ru ',
            'duration': 81,
            'uploader': 'NTDRussian',
            'uploader_id': '29790',
            'timestamp': 1381943602,
            'upload_date': '20131016',
            'age_limit': 0,
            'view_count': int,
            'thumbnail': r're:https?://pic\.rutubelist\.ru/video/.+\.(?:jpg|png)',
            'categories': ['Новости и СМИ'],
            'chapters': [],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://rutube.ru/play/embed/a10e53b86e8f349080f718582ce4c661',
        'only_matching': True,
    }, {
        'url': 'https://rutube.ru/embed/a10e53b86e8f349080f718582ce4c661',
        'only_matching': True,
    }, {
        'url': 'https://rutube.ru/video/3eac3b4561676c17df9132a9a1e62e3e/?pl_id=4252',
        'only_matching': True,
    }, {
        'url': 'https://rutube.ru/video/10b3a03fc01d5bbcc632a2f3514e8aab/?pl_type=source',
        'only_matching': True,
    }, {
        'url': 'https://rutube.ru/video/private/884fb55f07a97ab673c7d654553e0f48/?p=x2QojCumHTS3rsKHWXN8Lg',
        'info_dict': {
            'id': '884fb55f07a97ab673c7d654553e0f48',
            'ext': 'mp4',
            'title': 'Яцуноками, Nioh2',
            'description': 'Nioh2: финал сражения с боссом Яцуноками',
            'duration': 15,
            'uploader': 'mexus',
            'uploader_id': '24222106',
            'timestamp': 1670646232,
            'upload_date': '20221210',
            'age_limit': 0,
            'view_count': int,
            'thumbnail': 'https://pic.rutubelist.ru/video/f2/d4/f2d42b54be0a6e69c1c22539e3152156.jpg',
            'categories': ['Видеоигры'],
            'chapters': [],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://rutube.ru/video/c65b465ad0c98c89f3b25cb03dcc87c6/',
        'info_dict': {
            'id': 'c65b465ad0c98c89f3b25cb03dcc87c6',
            'ext': 'mp4',
            'chapters': 'count:4',
            'categories': ['Бизнес и предпринимательство'],
            'description': 'md5:252feac1305257d8c1bab215cedde75d',
            'thumbnail': r're:https?://pic\.rutubelist\.ru/video/.+\.(?:jpg|png)',
            'duration': 782,
            'age_limit': 0,
            'uploader_id': '23491359',
            'timestamp': 1677153329,
            'view_count': int,
            'upload_date': '20230223',
            'title': 'Бизнес с нуля: найм сотрудников. Интервью с директором строительной компании #1',
            'uploader': 'Стас Быков',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://rutube.ru/live/video/c58f502c7bb34a8fcdd976b221fca292/',
        'info_dict': {
            'id': 'c58f502c7bb34a8fcdd976b221fca292',
            'ext': 'mp4',
            'categories': ['Телепередачи'],
            'description': '',
            'thumbnail': r're:https?://pic\.rutubelist\.ru/video/.+\.(?:jpg|png)',
            'live_status': 'is_live',
            'age_limit': 0,
            'uploader_id': '23460655',
            'timestamp': 1652972968,
            'view_count': int,
            'upload_date': '20220519',
            'title': str,
            'uploader': 'Первый канал',
        },
        'skip': 'Invalid URL',
    }, {
        'url': 'https://rutube.ru/play/embed/03a9cb54bac3376af4c5cb0f18444e01/',
        'info_dict': {
            'id': '03a9cb54bac3376af4c5cb0f18444e01',
            'ext': 'mp4',
            'age_limit': 0,
            'description': '',
            'title': 'Церемония начала торгов акциями ПАО «ЕвроТранс»',
            'chapters': [],
            'upload_date': '20240829',
            'duration': 293,
            'uploader': 'MOEX - Московская биржа',
            'timestamp': 1724946628,
            'thumbnail': r're:https?://pic\.rutubelist\.ru/video/.+\.(?:jpg|png)',
            'view_count': int,
            'uploader_id': '38420507',
            'categories': ['Интервью'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://rutube.ru/video/5ab908fccfac5bb43ef2b1e4182256b0/',
        'only_matching': True,
    }, {
        'url': 'https://rutube.ru/live/video/private/c58f502c7bb34a8fcdd976b221fca292/',
        'only_matching': True,
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://novate.ru/blogs/170625/73644/',
        'info_dict': {
            'id': 'b0c96c75a4e5b274721bbced6ed8fb64',
            'ext': 'mp4',
            'title': 'Где в России находится единственная в своем роде скальная торпедная батарея',
            'age_limit': 0,
            'categories': ['Наука'],
            'chapters': [],
            'description': 'md5:2ed82e6b81958a43da6fb4d56f949e1f',
            'duration': 182,
            'thumbnail': r're:https?://pic\.rutubelist\.ru/video/.+\.(?:jpg|png)',
            'timestamp': 1749950158,
            'upload_date': '20250615',
            'uploader': 'Novate',
            'uploader_id': '24044809',
            'view_count': int,
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        query = parse_qs(url)
        info = self._download_and_extract_info(video_id, query)
        formats, subtitles = self._download_and_extract_formats_and_subtitles(video_id, query)
        return {
            **info,
            'formats': formats,
            'subtitles': subtitles,
        }


class RutubeEmbedIE(RutubeBaseIE):
    IE_NAME = 'rutube:embed'
    IE_DESC = 'Rutube embedded videos'
    _VALID_URL = r'https?://rutube\.ru/(?:video|play)/embed/(?P<id>[0-9]+)(?:[?#/]|$)'

    _TESTS = [{
        'url': 'https://rutube.ru/video/embed/6722881?vk_puid37=&vk_puid38=',
        'info_dict': {
            'id': 'a10e53b86e8f349080f718582ce4c661',
            'ext': 'mp4',
            'timestamp': 1387830582,
            'upload_date': '20131223',
            'uploader_id': '297833',
            'uploader': 'subziro89 ILya',
            'title': 'Мистический городок Эйри в Индиан 5 серия озвучка subziro89',
            'age_limit': 0,
            'duration': 1395,
            'chapters': [],
            'description': 'md5:a5acea57bbc3ccdc3cacd1f11a014b5b',
            'view_count': int,
            'thumbnail': r're:https?://pic\.rutubelist\.ru/video/.+\.(?:jpg|png)',
            'categories': ['Сериалы'],
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://rutube.ru/play/embed/8083783',
        'only_matching': True,
    }, {
        # private video
        'url': 'https://rutube.ru/play/embed/10631925?p=IbAigKqWd1do4mjaM5XLIQ',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        embed_id = self._match_id(url)
        # Query may contain private videos token and should be passed to API
        # requests (see #19163)
        query = parse_qs(url)
        options = self._download_api_options(embed_id, query)
        video_id = options['effective_video']
        formats, subtitles = self._extract_formats_and_subtitles(options, video_id)
        info = self._download_and_extract_info(video_id, query)
        info.update({
            'extractor_key': 'Rutube',
            'formats': formats,
            'subtitles': subtitles,
        })
        return info


class RutubePlaylistBaseIE(RutubeBaseIE):
    def _next_page_url(self, page_num, playlist_id, *args, **kwargs):
        return self._PAGE_TEMPLATE % (playlist_id, page_num)

    def _entries(self, playlist_id, *args, **kwargs):
        next_page_url = None
        for pagenum in itertools.count(1):
            page = self._download_json(
                next_page_url or self._next_page_url(
                    pagenum, playlist_id, *args, **kwargs),
                playlist_id, f'Downloading page {pagenum}')

            results = page.get('results')
            if not results or not isinstance(results, list):
                break

            for result in results:
                video_url = url_or_none(result.get('video_url'))
                if not video_url:
                    continue
                entry = self._extract_info(result, require_title=False)
                entry.update({
                    '_type': 'url',
                    'url': video_url,
                    'ie_key': RutubeIE.ie_key(),
                })
                yield entry

            next_page_url = page.get('next')
            if not next_page_url or not page.get('has_next'):
                break

    def _extract_playlist(self, playlist_id, *args, **kwargs):
        return self.playlist_result(
            self._entries(playlist_id, *args, **kwargs),
            playlist_id, kwargs.get('playlist_name'))

    def _real_extract(self, url):
        return self._extract_playlist(self._match_id(url))


class RutubeTagsIE(RutubePlaylistBaseIE):
    IE_NAME = 'rutube:tags'
    IE_DESC = 'Rutube tags'
    _VALID_URL = r'https?://rutube\.ru/tags/video/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://rutube.ru/tags/video/1800/',
        'info_dict': {
            'id': '1800',
        },
        'playlist_mincount': 68,
    }]

    _PAGE_TEMPLATE = 'https://rutube.ru/api/tags/video/%s/?page=%s&format=json'


class RutubeMovieIE(RutubePlaylistBaseIE):
    IE_NAME = 'rutube:movie'
    IE_DESC = 'Rutube movies'
    _VALID_URL = r'https?://rutube\.ru/metainfo/tv/(?P<id>\d+)'

    _MOVIE_TEMPLATE = 'https://rutube.ru/api/metainfo/tv/%s/?format=json'
    _PAGE_TEMPLATE = 'https://rutube.ru/api/metainfo/tv/%s/video?page=%s&format=json'

    def _real_extract(self, url):
        movie_id = self._match_id(url)
        movie = self._download_json(
            self._MOVIE_TEMPLATE % movie_id, movie_id,
            'Downloading movie JSON')
        return self._extract_playlist(
            movie_id, playlist_name=movie.get('name'))


class RutubePersonIE(RutubePlaylistBaseIE):
    IE_NAME = 'rutube:person'
    IE_DESC = 'Rutube person videos'
    _VALID_URL = r'https?://rutube\.ru/video/person/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://rutube.ru/video/person/313878/',
        'info_dict': {
            'id': '313878',
        },
        'playlist_mincount': 36,
    }]

    _PAGE_TEMPLATE = 'https://rutube.ru/api/video/person/%s/?page=%s&format=json'


class RutubePlaylistIE(RutubePlaylistBaseIE):
    IE_NAME = 'rutube:playlist'
    IE_DESC = 'Rutube playlists'
    _VALID_URL = r'https?://rutube\.ru/plst/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://rutube.ru/plst/308547/',
        'info_dict': {
            'id': '308547',
        },
        'playlist_mincount': 22,
    }]
    _PAGE_TEMPLATE = 'https://rutube.ru/api/playlist/custom/%s/videos?page=%s&format=json'


class RutubeChannelIE(RutubePlaylistBaseIE):
    IE_NAME = 'rutube:channel'
    IE_DESC = 'Rutube channel'
    _VALID_URL = r'https?://rutube\.ru/(?:channel/(?P<id>\d+)|u/(?P<slug>\w+))(?:/(?P<section>videos|shorts|playlists))?'
    _TESTS = [{
        'url': 'https://rutube.ru/channel/639184/videos/',
        'info_dict': {
            'id': '639184_videos',
        },
        'playlist_mincount': 129,
    }, {
        'url': 'https://rutube.ru/channel/25902603/shorts/',
        'info_dict': {
            'id': '25902603_shorts',
        },
        'playlist_mincount': 277,
    }, {
        'url': 'https://rutube.ru/channel/25902603/',
        'info_dict': {
            'id': '25902603',
        },
        'playlist_mincount': 406,
    }, {
        'url': 'https://rutube.ru/u/rutube/videos/',
        'info_dict': {
            'id': '23704195_videos',
        },
        'playlist_mincount': 113,
    }]

    _PAGE_TEMPLATE = 'https://rutube.ru/api/video/person/%s/?page=%s&format=json&origin__type=%s'

    def _next_page_url(self, page_num, playlist_id, section):
        origin_type = {
            'videos': 'rtb,rst,ifrm,rspa',
            'shorts': 'rshorts',
            None: '',
        }.get(section)
        return self._PAGE_TEMPLATE % (playlist_id, page_num, origin_type)

    def _real_extract(self, url):
        playlist_id, slug, section = self._match_valid_url(url).group('id', 'slug', 'section')
        if section == 'playlists':
            raise UnsupportedError(url)
        if slug:
            webpage = self._download_webpage(url, slug)
            redux_state = self._search_json(
                r'window\.reduxState\s*=', webpage, 'redux state', slug, transform_source=js_to_json)
            playlist_id = traverse_obj(redux_state, (
                'api', 'queries', lambda k, _: k.startswith('channelIdBySlug'),
                'data', 'channel_id', {int}, {str_or_none}, any))
        playlist = self._extract_playlist(playlist_id, section=section)
        if section:
            playlist['id'] = f'{playlist_id}_{section}'
        return playlist
