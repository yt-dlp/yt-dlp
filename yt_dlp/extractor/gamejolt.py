# coding: utf-8
import itertools
import json

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    str_or_none,
    traverse_obj,
    try_get
)


class GameJoltBaseIE(InfoExtractor):
    _API_BASE = 'https://gamejolt.com/site-api/'

    def _call_api(self, endpoint, *args, **kwargs):
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
        sort_by, scroll_id = self._configuration_arg('comment_sort', ['hot'])[0], -1
        is_scrolled = sort_by in ('new', 'you')
        for page in itertools.count(1):
            comments_data = self._call_api(
                'comments/Fireside_Post/%s/%s?%s=%d' % (str(post_num_id), sort_by,
                                                        'scroll_id' if is_scrolled else 'page', scroll_id if is_scrolled else page),
                post_hash_id, note='Downloading comments list page %d' % page)
            if not comments_data.get('comments'):
                break
            for comment in traverse_obj(comments_data, (('comments', 'childComments'), ...), expected_type=dict, default=[]):
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
                or self._call_api('web/posts/article/%s' % str_or_none(post_data.get('id')), post_id,
                                  note='Downloading article metadata', errnote='Unable to download article metadata', fatal=False).get('article'),
                post_id, fatal=False)
            full_description = self._parse_content_as_text(article_content)

        user_data = post_data.get('user') or {}

        # TODO: Handle multiple videos/embeds?
        embed_url = traverse_obj(post_data, ('embeds', ..., 'url'), expected_type=str_or_none, get_all=False)
        if embed_url:
            return self.url_result(embed_url)

        video_data = traverse_obj(post_data, ('videos', ...), expected_type=dict, get_all=False) or {}
        formats, subtitles, thumbnails = [], {}, []
        for media in video_data.get('media', []):
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

        return {
            'ie_key': GameJoltIE.ie_key(),
            'extractor': 'GameJolt',
            'webpage_url': str_or_none(post_data.get('url')) or 'https://gamejolt.com/p/' + post_id,
            'id': post_id,
            'title': description,
            'description': full_description or description,
            'display_id': post_data.get('slug'),
            'uploader': user_data.get('display_name') or user_data.get('name'),
            'uploader_id': user_data.get('username'),
            'uploader_url': 'https://gamejolt.com' + user_data['url'] if user_data.get('url') else None,
            'categories': [try_get(category, lambda x: '%s - %s' % (x['community']['name'], x['channel']['display_title']))
                           for category in post_data.get('communities' or [])],
            'tags': traverse_obj(
                lead_content, ('content', ..., 'content', ..., 'marks', ..., 'attrs', 'tag'), expected_type=str_or_none),
            'like_count': post_data.get('like_count'),
            'comment_count': post_data.get('comment_count') or 0,
            'timestamp': int_or_none(post_data.get('added_on'), scale=1000),
            'release_timestamp': int_or_none(post_data.get('published_on'), scale=1000),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': thumbnails,
            'view_count': int_or_none(video_data.get('view_count')),
            '__post_extractor': self.extract_comments(post_data.get('id'), post_id)
        }


class GameJoltIE(GameJoltBaseIE):
    _VALID_URL = r'https?://(?:www\.)?gamejolt\.com/p/(?P<id>[\w-]+)'
    _TESTS = [{
        # No audio
        'url': 'https://gamejolt.com/p/introducing-ramses-jackson-some-fnf-himbo-i-ve-been-animating-fo-c6achnzu',
        'md5': 'cd5f733258f6678b0ce500dd88166d86',
        'info_dict': {
            'id': 'c6achnzu',
            'ie_key': 'GameJolt',
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
            'ie_key': 'GameJolt',
            'ext': 'mp4',
            'display_id': 'i-fuckin-broke-chaos-d56h3eue',
            'title': 'I fuckin broke Chaos.',
            'description': 'I moved my tab durning the cutscene so now it\'s stuck like this.',
            'uploader': 'The_Nyesh_femboy',
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
    }]

    def _real_extract(self, url):
        post_id = self._match_id(url).split('-')[-1]
        post_data = self._call_api(
            'web/posts/view/%s' % post_id, post_id)['post']
        return self._parse_post(post_data)


class GameJoltPostListBaseIE(GameJoltBaseIE):
    def _entries(self, endpoint, list_id, note='Downloading post list', errnote='Unable to download post list'):
        page_num, items, scroll_id = 1, self._call_api(endpoint, list_id, note=note, errnote=errnote)['items'], None
        while items:
            for item in items:
                yield self._parse_post(item['action_resource_model'])
            scroll_id = items[-1]['scroll_id']
            page_num += 1
            items = self._call_api(
                endpoint, list_id, note='%s page %d' % (note, page_num), errnote=errnote, data=json.dumps({
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
            'web/profile/@%s' % user_id, user_id, note='Downloading user info', errnote='Unable to download user info')['user']
        bio = self._parse_content_as_text(
            self._parse_json(user_data.get('bio_content', '{}'), user_id, fatal=False) or {})
        return self.playlist_result(
            self._entries('web/posts/fetch/user/@%s?tab=active' % user_id, user_id, 'Downloading user posts', 'Unable to download user posts'),
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
            'web/discover/games/%s' % game_id, game_id, note='Downloading game info', errnote='Unable to download game info')['game']
        description = self._parse_content_as_text(
            self._parse_json(game_data.get('description_content', '{}'), game_id, fatal=False) or {})
        return self.playlist_result(
            self._entries('web/posts/fetch/game/%s' % game_id, game_id, 'Downloading game posts', 'Unable to download game posts'),
            game_id, game_data.get('title'), description)


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
            'title': 'Youtubers',
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
        if not channel_id:
            channel_id = 'featured'
        if not sort_by:
            sort_by = 'new'

        community_data = self._call_api(
            'web/communities/view/%s' % community_id, display_id, note='Downloading community info', errnote='Unable to download community info')['community']
        channel_data = traverse_obj(self._call_api(
            'web/communities/view-channel/%s/%s' % (community_id, channel_id), display_id, note='Downloading channel info', errnote='Unable to download channel info', fatal=False), 'channel') or {}

        title = '%s - %s' % (community_data.get('name'), channel_data['display_title']) if channel_data.get('display_title') else community_data.get('name')
        description = self._parse_content_as_text(
            self._parse_json(community_data.get('description_content', '{}'), display_id, fatal=False) or {})
        return self.playlist_result(
            self._entries('web/posts/fetch/community/%s?channels[]=%s&channels[]=%s' % (community_id, sort_by, channel_id), display_id, 'Downloading community posts', 'Unable to download community posts'),
            '%s/%s' % (community_id, channel_id), title, description)
