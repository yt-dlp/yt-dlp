import itertools

from .common import InfoExtractor
from ..utils import (
    bool_or_none,
    determine_ext,
    int_or_none,
    parse_qs,
    try_get,
    unified_timestamp,
    url_or_none,
)


class RutubeBaseIE(InfoExtractor):
    def _download_api_info(self, video_id, query=None):
        if not query:
            query = {}
        query['format'] = 'json'
        return self._download_json(
            f'http://rutube.ru/api/video/{video_id}/',
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
            f'http://rutube.ru/api/play/options/{video_id}/',
            video_id, 'Downloading options JSON',
            'Unable to download options JSON',
            headers=self.geo_verification_headers(), query=query)

    def _extract_formats(self, options, video_id):
        formats = []
        for format_id, format_url in options['video_balancer'].items():
            ext = determine_ext(format_url)
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    format_url, video_id, 'mp4', m3u8_id=format_id, fatal=False))
            elif ext == 'f4m':
                formats.extend(self._extract_f4m_formats(
                    format_url, video_id, f4m_id=format_id, fatal=False))
            else:
                formats.append({
                    'url': format_url,
                    'format_id': format_id,
                })
        return formats

    def _download_and_extract_formats(self, video_id, query=None):
        return self._extract_formats(
            self._download_api_options(video_id, query=query), video_id)


class RutubeIE(RutubeBaseIE):
    IE_NAME = 'rutube'
    IE_DESC = 'Rutube videos'
    _VALID_URL = r'https?://rutube\.ru/(?:video(?:/private)?|(?:play/)?embed)/(?P<id>[\da-z]{32})'
    _EMBED_REGEX = [r'<iframe[^>]+?src=(["\'])(?P<url>(?:https?:)?//rutube\.ru/(?:play/)?embed/[\da-z]{32}.*?)\1']

    _TESTS = [{
        'url': 'http://rutube.ru/video/3eac3b4561676c17df9132a9a1e62e3e/',
        'md5': 'e33ac625efca66aba86cbec9851f2692',
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
            'thumbnail': 'http://pic.rutubelist.ru/video/d2/a0/d2a0aec998494a396deafc7ba2c82add.jpg',
            'categories': ['Новости и СМИ'],
            'chapters': [],
        },
        'expected_warnings': ['Unable to download f4m'],
    }, {
        'url': 'http://rutube.ru/play/embed/a10e53b86e8f349080f718582ce4c661',
        'only_matching': True,
    }, {
        'url': 'http://rutube.ru/embed/a10e53b86e8f349080f718582ce4c661',
        'only_matching': True,
    }, {
        'url': 'http://rutube.ru/video/3eac3b4561676c17df9132a9a1e62e3e/?pl_id=4252',
        'only_matching': True,
    }, {
        'url': 'https://rutube.ru/video/10b3a03fc01d5bbcc632a2f3514e8aab/?pl_type=source',
        'only_matching': True,
    }, {
        'url': 'https://rutube.ru/video/private/884fb55f07a97ab673c7d654553e0f48/?p=x2QojCumHTS3rsKHWXN8Lg',
        'md5': 'd106225f15d625538fe22971158e896f',
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
            'thumbnail': 'http://pic.rutubelist.ru/video/f2/d4/f2d42b54be0a6e69c1c22539e3152156.jpg',
            'categories': ['Видеоигры'],
            'chapters': [],
        },
        'expected_warnings': ['Unable to download f4m'],
    }, {
        'url': 'https://rutube.ru/video/c65b465ad0c98c89f3b25cb03dcc87c6/',
        'info_dict': {
            'id': 'c65b465ad0c98c89f3b25cb03dcc87c6',
            'ext': 'mp4',
            'chapters': 'count:4',
            'categories': ['Бизнес и предпринимательство'],
            'description': 'md5:252feac1305257d8c1bab215cedde75d',
            'thumbnail': 'http://pic.rutubelist.ru/video/71/8f/718f27425ea9706073eb80883dd3787b.png',
            'duration': 782,
            'age_limit': 0,
            'uploader_id': '23491359',
            'timestamp': 1677153329,
            'view_count': int,
            'upload_date': '20230223',
            'title': 'Бизнес с нуля: найм сотрудников. Интервью с директором строительной компании',
            'uploader': 'Стас Быков',
        },
        'expected_warnings': ['Unable to download f4m'],
    }]

    @classmethod
    def suitable(cls, url):
        return False if RutubePlaylistIE.suitable(url) else super().suitable(url)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        query = parse_qs(url)
        info = self._download_and_extract_info(video_id, query)
        info['formats'] = self._download_and_extract_formats(video_id, query)
        return info


class RutubeEmbedIE(RutubeBaseIE):
    IE_NAME = 'rutube:embed'
    IE_DESC = 'Rutube embedded videos'
    _VALID_URL = r'https?://rutube\.ru/(?:video|play)/embed/(?P<id>[0-9]+)'

    _TESTS = [{
        'url': 'http://rutube.ru/video/embed/6722881?vk_puid37=&vk_puid38=',
        'info_dict': {
            'id': 'a10e53b86e8f349080f718582ce4c661',
            'ext': 'mp4',
            'timestamp': 1387830582,
            'upload_date': '20131223',
            'uploader_id': '297833',
            'description': 'Видео группы ★http://vk.com/foxkidsreset★ музей Fox Kids и Jetix<br/><br/> восстановлено и сделано в шикоформате subziro89 http://vk.com/subziro89',
            'uploader': 'subziro89 ILya',
            'title': 'Мистический городок Эйри в Индиан 5 серия озвучка subziro89',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://rutube.ru/play/embed/8083783',
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
        formats = self._extract_formats(options, video_id)
        info = self._download_and_extract_info(video_id, query)
        info.update({
            'extractor_key': 'Rutube',
            'formats': formats,
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
        'url': 'http://rutube.ru/tags/video/1800/',
        'info_dict': {
            'id': '1800',
        },
        'playlist_mincount': 68,
    }]

    _PAGE_TEMPLATE = 'http://rutube.ru/api/tags/video/%s/?page=%s&format=json'


class RutubeMovieIE(RutubePlaylistBaseIE):
    IE_NAME = 'rutube:movie'
    IE_DESC = 'Rutube movies'
    _VALID_URL = r'https?://rutube\.ru/metainfo/tv/(?P<id>\d+)'

    _MOVIE_TEMPLATE = 'http://rutube.ru/api/metainfo/tv/%s/?format=json'
    _PAGE_TEMPLATE = 'http://rutube.ru/api/metainfo/tv/%s/video?page=%s&format=json'

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
        'url': 'http://rutube.ru/video/person/313878/',
        'info_dict': {
            'id': '313878',
        },
        'playlist_mincount': 37,
    }]

    _PAGE_TEMPLATE = 'http://rutube.ru/api/video/person/%s/?page=%s&format=json'


class RutubePlaylistIE(RutubePlaylistBaseIE):
    IE_NAME = 'rutube:playlist'
    IE_DESC = 'Rutube playlists'
    _VALID_URL = r'https?://rutube\.ru/(?:video|(?:play/)?embed)/[\da-z]{32}/\?.*?\bpl_id=(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://rutube.ru/video/cecd58ed7d531fc0f3d795d51cee9026/?pl_id=3097&pl_type=tag',
        'info_dict': {
            'id': '3097',
        },
        'playlist_count': 27,
    }, {
        'url': 'https://rutube.ru/video/10b3a03fc01d5bbcc632a2f3514e8aab/?pl_id=4252&pl_type=source',
        'only_matching': True,
    }]

    _PAGE_TEMPLATE = 'http://rutube.ru/api/playlist/%s/%s/?page=%s&format=json'

    @classmethod
    def suitable(cls, url):
        from ..utils import int_or_none, parse_qs

        if not super().suitable(url):
            return False
        params = parse_qs(url)
        return params.get('pl_type', [None])[0] and int_or_none(params.get('pl_id', [None])[0])

    def _next_page_url(self, page_num, playlist_id, item_kind):
        return self._PAGE_TEMPLATE % (item_kind, playlist_id, page_num)

    def _real_extract(self, url):
        qs = parse_qs(url)
        playlist_kind = qs['pl_type'][0]
        playlist_id = qs['pl_id'][0]
        return self._extract_playlist(playlist_id, item_kind=playlist_kind)


class RutubeChannelIE(RutubePlaylistBaseIE):
    IE_NAME = 'rutube:channel'
    IE_DESC = 'Rutube channel'
    _VALID_URL = r'https?://rutube\.ru/channel/(?P<id>\d+)/videos'
    _TESTS = [{
        'url': 'https://rutube.ru/channel/639184/videos/',
        'info_dict': {
            'id': '639184',
        },
        'playlist_mincount': 133,
    }]

    _PAGE_TEMPLATE = 'http://rutube.ru/api/video/person/%s/?page=%s&format=json'
