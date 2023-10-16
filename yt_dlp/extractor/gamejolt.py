import itertools
import json
import math

from .common import InfoExtractor
from ..compat import compat_urllib_parse_unquote
from ..utils import (
    determine_ext,
    format_field,
    int_or_none,
    str_or_none,
    traverse_obj,
    try_get
)


class GameJoltBaseIE(InfoExtractor):
    _API_BASE = 'https://gamejolt.com/site-api/'

    def _call_api(self, endpoint, *args, **kwargs):
        kwargs.setdefault('headers', {}).update({'Accept': 'image/webp,*/*'})
        return self._download_json(self._API_BASE + endpoint, *args, **kwargs)['payload']

    def _parse_content_as_text(self, content):
        outer_contents, joined_contents = content.get('content') or [], []
        for outer_content in outer_contents:
            if outer_content.get('type') != 'paragraph':
                joined_contents.append(self._parse_content_as_text(outer_content))
                continue
            inner_contents, inner_content_text = outer_content.get('content') or [], ''
            for inner_content in inner_contents:
                if inner_content.get('text'):
                    inner_content_text += inner_content['text']
                elif inner_content.get('type') == 'hardBreak':
                    inner_content_text += '\n'
            joined_contents.append(inner_content_text)

        return '\n'.join(joined_contents)

    def _get_comments(self, post_num_id, post_hash_id):
        sort_by, scroll_id = self._configuration_arg('comment_sort', ['hot'], ie_key=GameJoltIE.ie_key())[0], -1
        is_scrolled = sort_by in ('new', 'you')
        for page in itertools.count(1):
            comments_data = self._call_api(
                'comments/Fireside_Post/%s/%s?%s=%d' % (
                    post_num_id, sort_by,
                    'scroll_id' if is_scrolled else 'page', scroll_id if is_scrolled else page),
                post_hash_id, note='Downloading comments list page %d' % page)
            if not comments_data.get('comments'):
                break
            for comment in traverse_obj(comments_data, (('comments', 'childComments'), ...), expected_type=dict):
                yield {
                    'id': comment['id'],
                    'text': self._parse_content_as_text(
                        self._parse_json(comment['comment_content'], post_hash_id)),
                    'timestamp': int_or_none(comment.get('posted_on'), scale=1000),
                    'like_count': comment.get('votes'),
                    'author': traverse_obj(comment, ('user', ('display_name', 'name')), expected_type=str_or_none, get_all=False),
                    'author_id': traverse_obj(comment, ('user', 'username'), expected_type=str_or_none),
                    'author_thumbnail': traverse_obj(comment, ('user', 'image_avatar'), expected_type=str_or_none),
                    'parent': comment.get('parent_id') or None,
                }
            scroll_id = int_or_none(comments_data['comments'][-1].get('posted_on'))

    def _parse_post(self, post_data):
        post_id = post_data['hash']
        lead_content = self._parse_json(post_data.get('lead_content') or '{}', post_id, fatal=False) or {}
        description, full_description = post_data.get('leadStr') or self._parse_content_as_text(
            self._parse_json(post_data.get('lead_content'), post_id)), None
        if post_data.get('has_article'):
            article_content = self._parse_json(
                post_data.get('article_content')
                or self._call_api(f'web/posts/article/{post_data.get("id", post_id)}', post_id,
                                  note='Downloading article metadata', errnote='Unable to download article metadata', fatal=False).get('article'),
                post_id, fatal=False)
            full_description = self._parse_content_as_text(article_content)

        user_data = post_data.get('user') or {}
        info_dict = {
            'extractor_key': GameJoltIE.ie_key(),
            'extractor': 'GameJolt',
            'webpage_url': str_or_none(post_data.get('url')) or f'https://gamejolt.com/p/{post_id}',
            'id': post_id,
            'title': description,
            'description': full_description or description,
            'display_id': post_data.get('slug'),
            'uploader': user_data.get('display_name') or user_data.get('name'),
            'uploader_id': user_data.get('username'),
            'uploader_url': format_field(user_data, 'url', 'https://gamejolt.com%s'),
            'categories': [try_get(category, lambda x: '%s - %s' % (x['community']['name'], x['channel'].get('display_title') or x['channel']['title']))
                           for category in post_data.get('communities' or [])],
            'tags': traverse_obj(
                lead_content, ('content', ..., 'content', ..., 'marks', ..., 'attrs', 'tag'), expected_type=str_or_none),
            'like_count': int_or_none(post_data.get('like_count')),
            'comment_count': int_or_none(post_data.get('comment_count'), default=0),
            'timestamp': int_or_none(post_data.get('added_on'), scale=1000),
            'release_timestamp': int_or_none(post_data.get('published_on'), scale=1000),
            '__post_extractor': self.extract_comments(post_data.get('id'), post_id)
        }

        # TODO: Handle multiple videos/embeds?
        video_data = traverse_obj(post_data, ('videos', ...), expected_type=dict, get_all=False) or {}
        formats, subtitles, thumbnails = [], {}, []
        for media in video_data.get('media') or []:
            media_url, mimetype, ext, media_id = media['img_url'], media.get('filetype', ''), determine_ext(media['img_url']), media.get('type')
            if mimetype == 'application/vnd.apple.mpegurl' or ext == 'm3u8':
                hls_formats, hls_subs = self._extract_m3u8_formats_and_subtitles(media_url, post_id, 'mp4', m3u8_id=media_id)
                formats.extend(hls_formats)
                subtitles.update(hls_subs)
            elif mimetype == 'application/dash+xml' or ext == 'mpd':
                dash_formats, dash_subs = self._extract_mpd_formats_and_subtitles(media_url, post_id, mpd_id=media_id)
                formats.extend(dash_formats)
                subtitles.update(dash_subs)
            elif 'image' in mimetype:
                thumbnails.append({
                    'id': media_id,
                    'url': media_url,
                    'width': media.get('width'),
                    'height': media.get('height'),
                    'filesize': media.get('filesize'),
                })
            else:
                formats.append({
                    'format_id': media_id,
                    'url': media_url,
                    'width': media.get('width'),
                    'height': media.get('height'),
                    'filesize': media.get('filesize'),
                    'acodec': 'none' if 'video-card' in media_url else None,
                })

        if formats:
            return {
                **info_dict,
                'formats': formats,
                'subtitles': subtitles,
                'thumbnails': thumbnails,
                'view_count': int_or_none(video_data.get('view_count')),
            }

        gif_entries = []
        for media in post_data.get('media', []):
            if determine_ext(media['img_url']) != 'gif' or 'gif' not in media.get('filetype', ''):
                continue
            gif_entries.append({
                'id': media['hash'],
                'title': media['filename'].split('.')[0],
                'formats': [{
                    'format_id': url_key,
                    'url': media[url_key],
                    'width': media.get('width') if url_key == 'img_url' else None,
                    'height': media.get('height') if url_key == 'img_url' else None,
                    'filesize': media.get('filesize') if url_key == 'img_url' else None,
                    'acodec': 'none',
                } for url_key in ('img_url', 'mediaserver_url', 'mediaserver_url_mp4', 'mediaserver_url_webm') if media.get(url_key)]
            })
        if gif_entries:
            return {
                '_type': 'playlist',
                **info_dict,
                'entries': gif_entries,
            }

        embed_url = traverse_obj(post_data, ('embeds', ..., 'url'), expected_type=str_or_none, get_all=False)
        if embed_url:
            return self.url_result(embed_url)
        return info_dict


class GameJoltIE(GameJoltBaseIE):
    _VALID_URL = r'https?://(?:www\.)?gamejolt\.com/p/(?:[\w-]*-)?(?P<id>\w{8})'
    _TESTS = [{
        # No audio
        'url': 'https://gamejolt.com/p/introducing-ramses-jackson-some-fnf-himbo-i-ve-been-animating-fo-c6achnzu',
        'md5': 'cd5f733258f6678b0ce500dd88166d86',
        'info_dict': {
            'id': 'c6achnzu',
            'ext': 'mp4',
            'display_id': 'introducing-ramses-jackson-some-fnf-himbo-i-ve-been-animating-fo-c6achnzu',
            'title': 'Introducing Ramses Jackson, some FNF himbo I’ve been animating for the past few days, hehe.\n#fnfmod #fridaynightfunkin',
            'description': 'Introducing Ramses Jackson, some FNF himbo I’ve been animating for the past few days, hehe.\n#fnfmod #fridaynightfunkin',
            'uploader': 'Jakeneutron',
            'uploader_id': 'Jakeneutron',
            'uploader_url': 'https://gamejolt.com/@Jakeneutron',
            'categories': ['Friday Night Funkin\' - Videos'],
            'tags': ['fnfmod', 'fridaynightfunkin'],
            'timestamp': 1633499590,
            'upload_date': '20211006',
            'release_timestamp': 1633499655,
            'release_date': '20211006',
            'thumbnail': 're:^https?://.+wgch9mhq.png$',
            'like_count': int,
            'comment_count': int,
            'view_count': int,
        }
    }, {
        # YouTube embed
        'url': 'https://gamejolt.com/p/hey-hey-if-there-s-anyone-who-s-looking-to-get-into-learning-a-n6g4jzpq',
        'md5': '79a931ff500a5c783ef6c3bda3272e32',
        'info_dict': {
            'id': 'XsNA_mzC0q4',
            'title': 'Adobe Animate CC 2021 Tutorial || Part 1 - The Basics',
            'description': 'md5:9d1ab9e2625b3fe1f42b2a44c67fdd13',
            'uploader': 'Jakeneutron',
            'uploader_id': 'Jakeneutron',
            'uploader_url': 'http://www.youtube.com/user/Jakeneutron',
            'ext': 'mp4',
            'duration': 1749,
            'tags': ['Adobe Animate CC', 'Tutorial', 'Animation', 'The Basics', 'For Beginners'],
            'like_count': int,
            'playable_in_embed': True,
            'categories': ['Education'],
            'availability': 'public',
            'thumbnail': 'https://i.ytimg.com/vi_webp/XsNA_mzC0q4/maxresdefault.webp',
            'age_limit': 0,
            'live_status': 'not_live',
            'channel_url': 'https://www.youtube.com/channel/UC6_L7fnczNalFZyBthUE9oA',
            'channel': 'Jakeneutron',
            'channel_id': 'UC6_L7fnczNalFZyBthUE9oA',
            'upload_date': '20211015',
            'view_count': int,
            'chapters': 'count:18',
        }
    }, {
        # Article
        'url': 'https://gamejolt.com/p/i-fuckin-broke-chaos-d56h3eue',
        'md5': '786c1ccf98fde02c03a2768acb4258d0',
        'info_dict': {
            'id': 'd56h3eue',
            'ext': 'mp4',
            'display_id': 'i-fuckin-broke-chaos-d56h3eue',
            'title': 'I fuckin broke Chaos.',
            'description': 'I moved my tab durning the cutscene so now it\'s stuck like this.',
            'uploader': 'Jeff____________',
            'uploader_id': 'The_Nyesh_Man',
            'uploader_url': 'https://gamejolt.com/@The_Nyesh_Man',
            'categories': ['Friday Night Funkin\' - Videos'],
            'timestamp': 1639800264,
            'upload_date': '20211218',
            'release_timestamp': 1639800330,
            'release_date': '20211218',
            'thumbnail': 're:^https?://.+euksy8bd.png$',
            'like_count': int,
            'comment_count': int,
            'view_count': int,
        }
    }, {
        # Single GIF
        'url': 'https://gamejolt.com/p/hello-everyone-i-m-developing-a-pixel-art-style-mod-for-fnf-and-i-vs4gdrd8',
        'info_dict': {
            'id': 'vs4gdrd8',
            'display_id': 'hello-everyone-i-m-developing-a-pixel-art-style-mod-for-fnf-and-i-vs4gdrd8',
            'title': 'md5:cc3d8b031d9bc7ec2ec5a9ffc707e1f9',
            'description': 'md5:cc3d8b031d9bc7ec2ec5a9ffc707e1f9',
            'uploader': 'Quesoguy',
            'uploader_id': 'CheeseguyDev',
            'uploader_url': 'https://gamejolt.com/@CheeseguyDev',
            'categories': ['Game Dev - General', 'Arts n\' Crafts - Creations', 'Pixel Art - showcase',
                           'Friday Night Funkin\' - Mods', 'Newgrounds - Friday Night Funkin (13+)'],
            'timestamp': 1639517122,
            'release_timestamp': 1639519966,
            'like_count': int,
            'comment_count': int,
        },
        'playlist': [{
            'info_dict': {
                'id': 'dszyjnwi',
                'ext': 'webm',
                'title': 'gif-presentacion-mejorado-dszyjnwi',
                'n_entries': 1,
            }
        }]
    }, {
        # Multiple GIFs
        'url': 'https://gamejolt.com/p/gif-yhsqkumq',
        'playlist_count': 35,
        'info_dict': {
            'id': 'yhsqkumq',
            'display_id': 'gif-yhsqkumq',
            'title': 'GIF',
            'description': 'GIF',
            'uploader': 'DaniilTvman',
            'uploader_id': 'DaniilTvman',
            'uploader_url': 'https://gamejolt.com/@DaniilTvman',
            'categories': ['Five Nights At The AGK Studio Comunity - NEWS game'],
            'timestamp': 1638721559,
            'release_timestamp': 1638722276,
            'like_count': int,
            'comment_count': int,
        },
    }]

    def _real_extract(self, url):
        post_id = self._match_id(url)
        post_data = self._call_api(
            f'web/posts/view/{post_id}', post_id)['post']
        return self._parse_post(post_data)


class GameJoltPostListBaseIE(GameJoltBaseIE):
    def _entries(self, endpoint, list_id, note='Downloading post list', errnote='Unable to download post list', initial_items=[]):
        page_num, scroll_id = 1, None
        items = initial_items or self._call_api(endpoint, list_id, note=note, errnote=errnote)['items']
        while items:
            for item in items:
                yield self._parse_post(item['action_resource_model'])
            scroll_id = items[-1]['scroll_id']
            page_num += 1
            items = self._call_api(
                endpoint, list_id, note=f'{note} page {page_num}', errnote=errnote, data=json.dumps({
                    'scrollDirection': 'from',
                    'scrollId': scroll_id,
                }).encode('utf-8')).get('items')


class GameJoltUserIE(GameJoltPostListBaseIE):
    _VALID_URL = r'https?://(?:www\.)?gamejolt\.com/@(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://gamejolt.com/@BlazikenSuperStar',
        'playlist_mincount': 1,
        'info_dict': {
            'id': '6116784',
            'title': 'S. Blaze',
            'description': 'md5:5ba7fbbb549e8ea2545aafbfe22eb03a',
        },
        'params': {
            'ignore_no_formats_error': True,
        },
        'expected_warnings': ['skipping format', 'No video formats found', 'Requested format is not available'],
    }]

    def _real_extract(self, url):
        user_id = self._match_id(url)
        user_data = self._call_api(
            f'web/profile/@{user_id}', user_id, note='Downloading user info', errnote='Unable to download user info')['user']
        bio = self._parse_content_as_text(
            self._parse_json(user_data.get('bio_content', '{}'), user_id, fatal=False) or {})
        return self.playlist_result(
            self._entries(f'web/posts/fetch/user/@{user_id}?tab=active', user_id, 'Downloading user posts', 'Unable to download user posts'),
            str_or_none(user_data.get('id')), user_data.get('display_name') or user_data.get('name'), bio)


class GameJoltGameIE(GameJoltPostListBaseIE):
    _VALID_URL = r'https?://(?:www\.)?gamejolt\.com/games/[\w-]+/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://gamejolt.com/games/Friday4Fun/655124',
        'playlist_mincount': 2,
        'info_dict': {
            'id': '655124',
            'title': 'Friday Night Funkin\': Friday 4 Fun',
            'description': 'md5:576a7dd87912a2dcf33c50d2bd3966d3'
        },
        'params': {
            'ignore_no_formats_error': True,
        },
        'expected_warnings': ['skipping format', 'No video formats found', 'Requested format is not available'],
    }]

    def _real_extract(self, url):
        game_id = self._match_id(url)
        game_data = self._call_api(
            f'web/discover/games/{game_id}', game_id, note='Downloading game info', errnote='Unable to download game info')['game']
        description = self._parse_content_as_text(
            self._parse_json(game_data.get('description_content', '{}'), game_id, fatal=False) or {})
        return self.playlist_result(
            self._entries(f'web/posts/fetch/game/{game_id}', game_id, 'Downloading game posts', 'Unable to download game posts'),
            game_id, game_data.get('title'), description)


class GameJoltGameSoundtrackIE(GameJoltBaseIE):
    _VALID_URL = r'https?://(?:www\.)?gamejolt\.com/get/soundtrack(?:\?|\#!?)(?:.*?[&;])??game=(?P<id>(?:\d+)+)'
    _TESTS = [{
        'url': 'https://gamejolt.com/get/soundtrack?foo=bar&game=657899',
        'info_dict': {
            'id': '657899',
            'title': 'Friday Night Funkin\': Vs Oswald',
            'n_entries': None,
        },
        'playlist': [{
            'info_dict': {
                'id': '184434',
                'ext': 'mp3',
                'title': 'Gettin\' Lucky (Menu Music)',
                'url': r're:^https://.+vs-oswald-menu-music\.mp3$',
                'release_timestamp': 1635190816,
                'release_date': '20211025',
                'n_entries': 3,
            }
        }, {
            'info_dict': {
                'id': '184435',
                'ext': 'mp3',
                'title': 'Rabbit\'s Luck (Extended Version)',
                'url': r're:^https://.+rabbit-s-luck--full-version-\.mp3$',
                'release_timestamp': 1635190841,
                'release_date': '20211025',
                'n_entries': 3,
            }
        }, {
            'info_dict': {
                'id': '185228',
                'ext': 'mp3',
                'title': 'Last Straw',
                'url': r're:^https://.+last-straw\.mp3$',
                'release_timestamp': 1635881104,
                'release_date': '20211102',
                'n_entries': 3,
            }
        }]
    }]

    def _real_extract(self, url):
        game_id = self._match_id(url)
        game_overview = self._call_api(
            f'web/discover/games/overview/{game_id}', game_id, note='Downloading soundtrack info', errnote='Unable to download soundtrack info')
        return self.playlist_result([{
            'id': str_or_none(song.get('id')),
            'title': str_or_none(song.get('title')),
            'url': str_or_none(song.get('url')),
            'release_timestamp': int_or_none(song.get('posted_on'), scale=1000),
        } for song in game_overview.get('songs') or []], game_id, traverse_obj(
            game_overview, ('microdata', 'name'), (('twitter', 'fb'), 'title'), expected_type=str_or_none, get_all=False))


class GameJoltCommunityIE(GameJoltPostListBaseIE):
    _VALID_URL = r'https?://(?:www\.)?gamejolt\.com/c/(?P<id>(?P<community>[\w-]+)(?:/(?P<channel>[\w-]+))?)(?:(?:\?|\#!?)(?:.*?[&;])??sort=(?P<sort>\w+))?'
    _TESTS = [{
        'url': 'https://gamejolt.com/c/fnf/videos',
        'playlist_mincount': 50,
        'info_dict': {
            'id': 'fnf/videos',
            'title': 'Friday Night Funkin\' - Videos',
            'description': 'md5:6d8c06f27460f7d35c1554757ffe53c8'
        },
        'params': {
            'playlistend': 50,
            'ignore_no_formats_error': True,
        },
        'expected_warnings': ['skipping format', 'No video formats found', 'Requested format is not available'],
    }, {
        'url': 'https://gamejolt.com/c/youtubers',
        'playlist_mincount': 50,
        'info_dict': {
            'id': 'youtubers/featured',
            'title': 'Youtubers - featured',
            'description': 'md5:53e5582c93dcc467ab597bfca4db17d4'
        },
        'params': {
            'playlistend': 50,
            'ignore_no_formats_error': True,
        },
        'expected_warnings': ['skipping format', 'No video formats found', 'Requested format is not available'],
    }]

    def _real_extract(self, url):
        display_id, community_id, channel_id, sort_by = self._match_valid_url(url).group('id', 'community', 'channel', 'sort')
        channel_id, sort_by = channel_id or 'featured', sort_by or 'new'

        community_data = self._call_api(
            f'web/communities/view/{community_id}', display_id,
            note='Downloading community info', errnote='Unable to download community info')['community']
        channel_data = traverse_obj(self._call_api(
            f'web/communities/view-channel/{community_id}/{channel_id}', display_id,
            note='Downloading channel info', errnote='Unable to download channel info', fatal=False), 'channel') or {}

        title = f'{community_data.get("name") or community_id} - {channel_data.get("display_title") or channel_id}'
        description = self._parse_content_as_text(
            self._parse_json(community_data.get('description_content') or '{}', display_id, fatal=False) or {})
        return self.playlist_result(
            self._entries(
                f'web/posts/fetch/community/{community_id}?channels[]={sort_by}&channels[]={channel_id}',
                display_id, 'Downloading community posts', 'Unable to download community posts'),
            f'{community_id}/{channel_id}', title, description)


class GameJoltSearchIE(GameJoltPostListBaseIE):
    _VALID_URL = r'https?://(?:www\.)?gamejolt\.com/search(?:/(?P<filter>communities|users|games))?(?:\?|\#!?)(?:.*?[&;])??q=(?P<id>(?:[^&#]+)+)'
    _URL_FORMATS = {
        'users': 'https://gamejolt.com/@{username}',
        'communities': 'https://gamejolt.com/c/{path}',
        'games': 'https://gamejolt.com/games/{slug}/{id}',
    }
    _TESTS = [{
        'url': 'https://gamejolt.com/search?foo=bar&q=%23fnf',
        'playlist_mincount': 50,
        'info_dict': {
            'id': '#fnf',
            'title': '#fnf',
        },
        'params': {
            'playlistend': 50,
            'ignore_no_formats_error': True,
        },
        'expected_warnings': ['skipping format', 'No video formats found', 'Requested format is not available'],
    }, {
        'url': 'https://gamejolt.com/search/communities?q=cookie%20run',
        'playlist_mincount': 10,
        'info_dict': {
            'id': 'cookie run',
            'title': 'cookie run',
        },
    }, {
        'url': 'https://gamejolt.com/search/users?q=mlp',
        'playlist_mincount': 278,
        'info_dict': {
            'id': 'mlp',
            'title': 'mlp',
        },
    }, {
        'url': 'https://gamejolt.com/search/games?q=roblox',
        'playlist_mincount': 688,
        'info_dict': {
            'id': 'roblox',
            'title': 'roblox',
        },
    }]

    def _search_entries(self, query, filter_mode, display_query):
        initial_search_data = self._call_api(
            f'web/search/{filter_mode}?q={query}', display_query,
            note=f'Downloading {filter_mode} list', errnote=f'Unable to download {filter_mode} list')
        entries_num = traverse_obj(initial_search_data, 'count', f'{filter_mode}Count')
        if not entries_num:
            return
        for page in range(1, math.ceil(entries_num / initial_search_data['perPage']) + 1):
            search_results = self._call_api(
                f'web/search/{filter_mode}?q={query}&page={page}', display_query,
                note=f'Downloading {filter_mode} list page {page}', errnote=f'Unable to download {filter_mode} list')
            for result in search_results[filter_mode]:
                yield self.url_result(self._URL_FORMATS[filter_mode].format(**result))

    def _real_extract(self, url):
        filter_mode, query = self._match_valid_url(url).group('filter', 'id')
        display_query = compat_urllib_parse_unquote(query)
        return self.playlist_result(
            self._search_entries(query, filter_mode, display_query) if filter_mode else self._entries(
                f'web/posts/fetch/search/{query}', display_query, initial_items=self._call_api(
                    f'web/search?q={query}', display_query,
                    note='Downloading initial post list', errnote='Unable to download initial post list')['posts']),
            display_query, display_query)
