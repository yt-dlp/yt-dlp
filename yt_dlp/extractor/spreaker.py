import itertools

from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    parse_qs,
    str_or_none,
    try_get,
    unified_timestamp,
    update_url_query,
    url_or_none,
)
from ..utils.traversal import traverse_obj


def _extract_episode(data, episode_id=None):
    title = data['title']
    download_url = data['download_url']

    series = try_get(data, lambda x: x['show']['title'], str)
    uploader = try_get(data, lambda x: x['author']['fullname'], str)

    thumbnails = []
    for image in ('image_original', 'image_medium', 'image'):
        image_url = url_or_none(data.get(f'{image}_url'))
        if image_url:
            thumbnails.append({'url': image_url})

    def stats(key):
        return int_or_none(try_get(
            data,
            (lambda x: x[f'{key}s_count'],
             lambda x: x['stats'][f'{key}s'])))

    def duration(key):
        return float_or_none(data.get(key), scale=1000)

    return {
        'id': str(episode_id or data['episode_id']),
        'url': download_url,
        'display_id': data.get('permalink'),
        'title': title,
        'description': data.get('description'),
        'timestamp': unified_timestamp(data.get('published_at')),
        'uploader': uploader,
        'uploader_id': str_or_none(data.get('author_id')),
        'creator': uploader,
        'duration': duration('duration') or duration('length'),
        'view_count': stats('play'),
        'like_count': stats('like'),
        'comment_count': stats('message'),
        'format': 'MPEG Layer 3',
        'format_id': 'mp3',
        'container': 'mp3',
        'ext': 'mp3',
        'thumbnails': thumbnails,
        'series': series,
        'extractor_key': SpreakerIE.ie_key(),
    }


class SpreakerIE(InfoExtractor):
    _VALID_URL = [
        r'https?://api\.spreaker\.com/(?:(?:download/)?episode|v2/episodes)/(?P<id>\d+)',
        r'https?://(?:www\.)?spreaker\.com/episode/[^#?/]*?(?P<id>\d+)/?(?:[?#]|$)',
    ]
    _TESTS = [{
        'url': 'https://api.spreaker.com/episode/12534508',
        'info_dict': {
            'id': '12534508',
            'display_id': 'swm-ep15-how-to-market-your-music-part-2',
            'ext': 'mp3',
            'title': 'EP:15 | Music Marketing (Likes) - Part 2',
            'description': 'md5:0588c43e27be46423e183076fa071177',
            'timestamp': 1502250336,
            'upload_date': '20170809',
            'uploader': 'SWM',
            'uploader_id': '9780658',
            'duration': 1063.42,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'series': 'Success With Music | SWM',
            'thumbnail': 'https://d3wo5wojvuv7l.cloudfront.net/t_square_limited_160/images.spreaker.com/original/777ce4f96b71b0e1b7c09a5e625210e3.jpg',
            'creators': ['SWM'],
        },
    }, {
        'url': 'https://api.spreaker.com/download/episode/12534508/swm_ep15_how_to_market_your_music_part_2.mp3',
        'only_matching': True,
    }, {
        'url': 'https://api.spreaker.com/v2/episodes/12534508?export=episode_segments',
        'only_matching': True,
    }, {
        'note': 'episode',
        'url': 'https://www.spreaker.com/episode/grunge-music-origins-the-raw-sound-that-defined-a-generation--60269615',
        'info_dict': {
            'id': '60269615',
            'display_id': 'grunge-music-origins-the-raw-sound-that-',
            'ext': 'mp3',
            'title': 'Grunge Music Origins - The Raw Sound that Defined a Generation',
            'description': str,
            'timestamp': 1717468905,
            'upload_date': '20240604',
            'uploader': 'Katie Brown 2',
            'uploader_id': '17733249',
            'duration': 818.83,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'series': '90s Grunge',
            'thumbnail': 'https://d3wo5wojvuv7l.cloudfront.net/t_square_limited_160/images.spreaker.com/original/bb0d4178f7cf57cc8786dedbd9c5d969.jpg',
            'creators': ['Katie Brown 2'],
        },
    }, {
        'url': 'https://www.spreaker.com/episode/60269615',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        episode_id = self._match_id(url)
        data = self._download_json(
            f'https://api.spreaker.com/v2/episodes/{episode_id}', episode_id,
            query=traverse_obj(parse_qs(url), {'key': ('key', 0)}))['response']['episode']
        return _extract_episode(data, episode_id)


class SpreakerShowIE(InfoExtractor):
    _VALID_URL = [
        r'https?://api\.spreaker\.com/(?:v2/)shows?/(?P<id>\d+)',
        r'https?://(?:www\.)?spreaker\.com/podcast/[\w-]+--(?P<id>[\d]+)',
        r'https?://(?:www\.)?spreaker\.com/show/(?P<id>\d+)/episodes/feed',
    ]
    _TESTS = [{
        'url': 'https://api.spreaker.com/v2/shows/4652058',
        'info_dict': {
            'id': 4652058,
            'display_id': '3-ninjas-podcast',
            'title': 'The Dojo w/ Domino & Hesh Jones',
            'description': 'md5:d3277d9d3264b85a56f34de37820af95',
            'uploader': 'The Dojo w/ Domino & Hesh Jone',
            'uploader_id': 13414919,
            'uploader_url': 'https://www.spreaker.com/user/the-dojo-w-domino-hesh-jone--13414919',
            'thumbnail': 'https://d3wo5wojvuv7l.cloudfront.net/images.spreaker.com/original/2808a2bb63a36549ca25b9a72492c70a.jpg',
            'categories': ['Comedy', 'Animation & Manga', 'Video Games'],
        },
        'playlist_mincount': 118,
    }, {
        'url': 'https://www.spreaker.com/podcast/health-wealth--5918323',
        'info_dict': {
            'id': 5918323,
            'display_id': 'itpodradio-health-wealth',
            'title': 'Health Wealth',
            'description': 'md5:99e7a46c0c39b7b9f5aee92452216864',
            'uploader': 'India Today Podcast',
            'uploader_id': 15714861,
            'uploader_url': 'https://www.spreaker.com/user/india-today-podcast--15714861',
            'thumbnail': 'https://d3wo5wojvuv7l.cloudfront.net/images.spreaker.com/original/cb96e6b9a211c1a004e4a027f696f8c2.jpg',
            'categories': ['Health & Fitness'],
        },
        'playlist_mincount': 60,
    }, {
        'url': 'https://www.spreaker.com/show/5887186/episodes/feed',
        'info_dict': {
            'id': 5887186,
            'display_id': 'orbinea',
            'title': 'Orbinéa Le Monde des Odyssées| Documentaire Podcast Histoire pour dormir Livre Audio Enfant & Adulte',
            'description': 'md5:79101727388ece4114ae4fabc8861bb5',
            'uploader': 'Orbinea Studio',
            'uploader_id': 17206155,
            'uploader_url': 'https://www.spreaker.com/user/orbinea-studio--17206155',
            'thumbnail': 'https://d3wo5wojvuv7l.cloudfront.net/images.spreaker.com/original/0d755be30d97fb65f8a8f2803a5edb57.jpg',
            'categories': ['Science', 'Documentary', 'Education'],
        },
        'playlist_mincount': 290,
    }]

    def _real_extract(self, url):
        show_id = self._match_id(url)
        additional_api_query = traverse_obj(parse_qs(url), {
            'key': ('key', 0),
        }) or {}
        show_data = self._download_json(
            f'https://api.spreaker.com/v2/shows/{show_id}', show_id,
            note='Downloading JSON show metadata', query=additional_api_query)
        episodes = []
        episodes_api_url = f'https://api.spreaker.com/v2/shows/{show_id}/episodes?limit=100'

        for page_num in itertools.count(1):
            episodes_api = self._download_json(episodes_api_url, show_id,
                                               note=f'Downloading JSON episodes metadata page {page_num}', query=additional_api_query)
            episodes_in_page = traverse_obj(episodes_api, ('response', 'items', ..., {
                'url': 'site_url',
                'id': 'episode_id',
                'title': 'title',
            }))

            for i in episodes_in_page:
                episodes.append(self.url_result(update_url_query(i['url'], additional_api_query), ie=SpreakerIE.ie_key(), video_id=i.get('id'), video_title=i.get('title')))

            episodes_api_url = traverse_obj(episodes_api, ('response', 'next_url'), default=None)
            if episodes_api_url is None:
                break

        return {
            '_type': 'playlist',
            'id': int_or_none(show_id),
            'display_id': traverse_obj(show_data, ('response', 'show', 'permalink')),
            'title': traverse_obj(show_data, ('response', 'show', 'title')),
            'description': traverse_obj(show_data, ('response', 'show', 'description')),
            'thumbnail': traverse_obj(show_data, ('response', 'show', 'image_original_url')),
            'uploader': traverse_obj(show_data, ('response', 'show', 'author', 'fullname')),
            'uploader_id': traverse_obj(show_data, ('response', 'show', 'author', 'user_id')),
            'uploader_url': traverse_obj(show_data, ('response', 'show', 'author', 'site_url')),
            'webpage_url': traverse_obj(show_data, ('response', 'show', 'site_url')),
            'categories': traverse_obj(show_data, ('response', 'show', ('category', 'category_2', 'category_3'), 'name')),
            'entries': episodes,
        }
