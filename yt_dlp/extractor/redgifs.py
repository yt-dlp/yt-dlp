# coding: utf-8
import functools

from .common import InfoExtractor
from ..compat import compat_parse_qs
from ..utils import (
    ExtractorError,
    int_or_none,
    qualities,
    try_get,
    OnDemandPagedList,
)


class RedGifsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www\.)?redgifs\.com/watch/|thumbs2\.redgifs\.com/)(?P<id>[^-/?#\.]+)'
    _FORMATS = {
        'gif': 250,
        'sd': 480,
        'hd': None,
    }
    _TESTS = [{
        'url': 'https://www.redgifs.com/watch/squeakyhelplesswisent',
        'info_dict': {
            'id': 'squeakyhelplesswisent',
            'ext': 'mp4',
            'title': 'Hotwife Legs Thick',
            'timestamp': 1636287915,
            'upload_date': '20211107',
            'uploader': 'ignored52',
            'duration': 16,
            'view_count': int,
            'like_count': int,
            'categories': list,
            'age_limit': 18,
        }
    }, {
        'url': 'https://thumbs2.redgifs.com/SqueakyHelplessWisent-mobile.mp4#t=0',
        'info_dict': {
            'id': 'squeakyhelplesswisent',
            'ext': 'mp4',
            'title': 'Hotwife Legs Thick',
            'timestamp': 1636287915,
            'upload_date': '20211107',
            'uploader': 'ignored52',
            'duration': 16,
            'view_count': int,
            'like_count': int,
            'categories': list,
            'age_limit': 18,
        }
    }]

    def _parse_gif_data(self, gif_data):
        video_id = gif_data.get("id")
        urls = gif_data['urls']

        quality = qualities(tuple(self._FORMATS.keys()))

        orig_height = int_or_none(gif_data.get('height'))
        aspect_ratio = try_get(gif_data, lambda x: orig_height / x['width'])

        formats = []
        for format_id, height in self._FORMATS.items():
            video_url = urls.get(format_id)
            if not video_url:
                continue
            height = min(orig_height, height or orig_height)
            formats.append({
                'url': video_url,
                'format_id': format_id,
                'width': height * aspect_ratio if aspect_ratio else None,
                'height': height,
                'quality': quality(format_id),
            })
        self._sort_formats(formats)

        webpage_url = f'https://redgifs.com/watch/{video_id}'

        return {
            'id': video_id,
            'title': ' '.join(gif_data.get('tags') or []) or 'RedGifs',
            'timestamp': int_or_none(gif_data.get('createDate')),
            'uploader': gif_data.get('userName'),
            'duration': int_or_none(gif_data.get('duration')),
            'view_count': int_or_none(gif_data.get('views')),
            'like_count': int_or_none(gif_data.get('likes')),
            'categories': gif_data.get('tags') or [],
            'webpage_url': webpage_url,
            'tags': gif_data.get('tags'),
            'age_limit': 18,
            'formats': formats,
        }

    def _real_extract(self, url):
        video_id = self._match_id(url).lower()

        video_info = self._download_json(
            'https://api.redgifs.com/v2/gifs/%s' % video_id,
            video_id, 'Downloading video info')
        if 'error' in video_info:
            raise ExtractorError(f'RedGifs said: {video_info["error"]}', expected=True)

        return self._parse_gif_data(video_info['gif'])


class RedGifsSearchIE(RedGifsIE):
    IE_DESC = 'Redgifs search'
    _VALID_URL = r'https?://(?:www\.)?redgifs\.com/browse\?(?P<query>.*)'
    _PAGE_SIZE = 80
    _TESTS = [
        {
            'url': 'https://www.redgifs.com/browse?tags=Lesbian',
            'info_dict': {
                'id': 'tags=Lesbian',
                'title': 'Lesbian',
                'description': 'RedGifs search for Lesbian, ordered by trending'
            },
            'playlist_mincount': 100,
        },
        {
            'url': 'https://www.redgifs.com/browse?type=g&order=latest&tags=Lesbian',
            'info_dict': {
                'id': 'type=g&order=latest&tags=Lesbian',
                'title': 'Lesbian',
                'description': 'RedGifs search for Lesbian, ordered by latest'
            },
            'playlist_mincount': 100,
        },
        {
            'url': 'https://www.redgifs.com/browse?type=g&order=latest&tags=Lesbian&page=2',
            'info_dict': {
                'id': 'type=g&order=latest&tags=Lesbian&page=2',
                'title': 'Lesbian',
                'description': 'RedGifs search for Lesbian, ordered by latest'
            },
            'playlist_count': 80,
        }
    ]

    def _fetch_page(self, video_id, api_query, page=1):
        api_query['page'] = page
        data = self._download_json(
            'https://api.redgifs.com/v2/gifs/search',
            video_id,
            query=api_query
        )
        if 'error' in data:
            raise ExtractorError(f'RedGifs said: {data["error"]}', expected=True)

        return [self._parse_gif_data(entry) for entry in data['gifs']]

    def _real_extract(self, url):
        query_str = self._match_valid_url(url).group('query')

        query = compat_parse_qs(query_str)
        if not query.get('tags'):
            raise ExtractorError('Invalid query tags', expected=True)

        tags = query.get('tags')[0]
        order = query.get('order', ('trending',))[0]
        api_query = {
            'search_text': tags,
            'order': order,
        }
        if query.get('type'):
            api_query['type'] = query.get('type')[0]

        if query.get('page'):
            page = query.get('page', (1,))[0]
            entries = self._fetch_page(query_str, api_query, page)
        else:
            entries = OnDemandPagedList(
                functools.partial(self._fetch_page, query_str, api_query),
                self._PAGE_SIZE)
        title = tags
        description = f'RedGifs search for {tags}, ordered by {order}'

        return self.playlist_result(
            entries,
            playlist_id=query_str,
            playlist_title=title,
            playlist_description=description
        )


class RedGifsUserIE(RedGifsIE):
    IE_DESC = 'Redgifs user'
    _VALID_URL = r'https?://(?:www\.)?redgifs\.com/users/(?P<username>[^/?#]+)(?:\?(?P<query>.*))?'
    _PAGE_SIZE = 30
    _TESTS = [
        {
            'url': 'https://www.redgifs.com/users/lamsinka89',
            'info_dict': {
                'id': 'lamsinka89',
                'title': 'lamsinka89',
                'description': 'RedGifs user lamsinka89'
            },
            'playlist_mincount': 100,
        },
        {
            'url': 'https://www.redgifs.com/users/lamsinka89?page=3',
            'info_dict': {
                'id': 'lamsinka89?page=3',
                'title': 'lamsinka89',
                'description': 'RedGifs user lamsinka89'
            },
            'playlist_count': 30,
        },
        {
            'url': 'https://www.redgifs.com/users/lamsinka89?order=best&type=g',
            'info_dict': {
                'id': 'lamsinka89?order=best&type=g',
                'title': 'lamsinka89',
                'description': 'RedGifs user lamsinka89'
            },
            'playlist_mincount': 100,
        }
    ]

    def _fetch_page(self, video_id, username, api_query, page=1):
        api_query['page'] = page
        data = self._download_json(
            f'https://api.redgifs.com/v2/users/{username}/search',
            video_id,
            query=api_query
        )
        if 'error' in data:
            raise ExtractorError(f'RedGifs said: {data["error"]}', expected=True)

        return [self._parse_gif_data(entry) for entry in data['gifs']]

    def _real_extract(self, url):
        match = self._match_valid_url(url)
        username = match.group('username')
        query_str = match.group('query')
        playlist_id = username
        if query_str:
            playlist_id = f'{username}?{query_str}'
        description = f'RedGifs user {username}'

        if not username:
            raise ExtractorError('Invalid username', expected=True)

        api_query = {
            'order': 'recent',
        }
        page = None
        if query_str:
            query = compat_parse_qs(query_str)
            if query.get('order'):
                api_query['order'] = query.get('order', ('recent',))[0]
                description += ", ordered by {order}"
            if query.get('type'):
                api_query['type'] = query.get('type')[0]
            page = query.get('page', (1,))[0]

        if page is not None:
            entries = self._fetch_page(playlist_id, username, api_query, page)
        else:
            entries = OnDemandPagedList(
                functools.partial(self._fetch_page, playlist_id, username, api_query),
                self._PAGE_SIZE)

        return self.playlist_result(
            entries,
            playlist_id=playlist_id,
            playlist_title=username,
            playlist_description=description
        )
