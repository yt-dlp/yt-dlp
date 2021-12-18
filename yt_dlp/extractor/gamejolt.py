# coding: utf-8
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
    _API_BASE = 'https://gamejolt.com/site-api/web/'

    def _call_api(self, endpoint, *args, **kwargs):
        return self._download_json(self._API_BASE + endpoint, *args, **kwargs)['payload']

    def _parse_content_as_text(self, content):
        contents, full_text = traverse_obj(content, ('content', ..., 'content', ...), expected_type=dict, default=[]), ''
        for content in contents:
            if content.get('text'):
                full_text += content['text']
            elif content.get('type') == 'hardBreak':
                full_text += '\n'
        return full_text

    def _parse_post(self, post_data):
        post_id = post_data['hash']
        lead_content = self._parse_json(post_data.get('lead_content') or '{}', post_id, fatal=False) or {}
        description, full_description = post_data.get('leadStr'), None
        if post_data.get('has_article'):
            article_content = self._parse_json(
                post_data.get('article_content')
                or self._call_api('posts/article/%s' % str_or_none(post_data.get('id')), post_id,
                                  note='Downloading article metadata', errnote='Unable to download article metadata', fatal=False).get('article'),
                post_id, fatal=False)
            full_description = self._parse_content_as_text(article_content)

        user_data = post_data.get('user') or {}

        # TODO: Handle multiple videos/embeds?
        embed_url = traverse_obj(post_data, ('embeds', ..., 'url'), expected_type=str_or_none, get_all=False)
        if embed_url:
            return self.url_result(embed_url)

        video_data = traverse_obj(post_data, ('videos', ...), expected_type=dict, get_all=False, default={})
        formats, thumbnails = [], []
        for media in video_data.get('media', []):
            media_url, mimetype, ext, media_id = media['img_url'], media.get('filetype', ''), determine_ext(media['img_url']), media.get('type')
            if mimetype == 'application/vnd.apple.mpegurl' or ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(media_url, post_id, 'mp4', m3u8_id=media_id))
            elif mimetype == 'application/dash+xml' or ext == 'mpd':
                formats.extend(self._extract_mpd_formats(media_url, post_id, mpd_id=media_id))
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
            'thumbnails': thumbnails,
            'view_count': int_or_none(video_data.get('view_count')),
        }


class GameJoltIE(GameJoltBaseIE):
    _VALID_URL = r'https?://gamejolt\.com/p/(?P<id>[\w-]+)'
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
            'uploader': str,
            'uploader_id': str,
            'uploader_url': str,
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
            'posts/view/%s' % post_id, post_id)['post']
        return self._parse_post(post_data)


class GameJoltPostListBaseIE(GameJoltBaseIE):
    def _entries(self, endpoint, list_id, note='Downloading post list', errnote='Unable to download post list'):
        page_num, items, scroll_id = 1, self._call_api(endpoint, list_id, note=note, errnote=errnote)['items'], None
        while items:
            for item in items:
                yield self._parse_post(item['action_resource_model'])
                scroll_id = item['scroll_id']
            page_num += 1
            items = self._call_api(
                endpoint, list_id, note='%s page %d' % (note, page_num), errnote=errnote, data=json.dumps({
                    'scrollDirection': 'from',
                    'scrollId': scroll_id,
                }).encode('utf-8')).get('items')


class GameJoltUserIE(GameJoltPostListBaseIE):
    _VALID_URL = r'https?://gamejolt\.com/@(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://gamejolt.com/@BlazikenSuperStar',
        'playlist_mincount': 1,
        'info_dict': {
            'id': '6116784',
            'title': 'S. Blaze',
            'description': 'md5:1771f92a045d81004ce8450512c6d32a',
        },
        'params': {
            'ignore_no_formats_error': True,
        },
        'expected_warnings': ['skipping format'],
    }]

    def _real_extract(self, url):
        user_id = self._match_id(url)
        user_data = self._call_api(
            'profile/@%s' % user_id, user_id, note='Downloading user info', errnote='Unable to download user info')['user']
        bio = self._parse_content_as_text(
            self._parse_json(user_data.get('bio_content', '{}'), user_id, fatal=False) or {})
        return self.playlist_result(
            self._entries('posts/fetch/user/@%s?tab=active' % user_id, user_id, 'Downloading user posts', 'Unable to download user posts'),
            str_or_none(user_data.get('id')), user_data.get('display_name') or user_data.get('name'), bio)


class GameJoltGameIE(GameJoltPostListBaseIE):
    _VALID_URL = r'https?://gamejolt\.com/games/[\w-]+/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://gamejolt.com/games/Friday4Fun/655124',
        'playlist_mincount': 2,
        'info_dict': {
            'id': '655124',
            'title': 'Friday Night Funkin\': Friday 4 Fun',
            'description': 'md5:4c53110368536a353229b72cc1fb2f5c'
        },
        'params': {
            'ignore_no_formats_error': True,
        },
        'expected_warnings': ['skipping format'],
    }]

    def _real_extract(self, url):
        game_id = self._match_id(url)
        game_data = self._call_api(
            'discover/games/%s' % game_id, game_id, note='Downloading game info', errnote='Unable to download game info')['game']
        description = self._parse_content_as_text(
            self._parse_json(game_data.get('description_content', '{}'), game_id, fatal=False) or {})
        return self.playlist_result(
            self._entries('posts/fetch/game/%s' % game_id, game_id, 'Downloading game posts', 'Unable to download game posts'),
            game_id, game_data.get('title'), description)


class GameJoltCommunityIE(GameJoltPostListBaseIE):
    _VALID_URL = r'https?://gamejolt\.com/c/(?P<id>(?P<community>[\w-]+)(?:/(?P<channel>[\w-]+))?)(?:(?:\?|\#!?)(?:.*?[&;])??sort=(?P<sort>\w+))?'
    _TESTS = [{
        'url': 'https://gamejolt.com/c/fnf/videos',
        'playlist_mincount': 50,
        'info_dict': {
            'id': 'fnf/videos',
            'title': 'Friday Night Funkin\' - Videos',
            'description': 'md5:aa'
        },
        'params': {
            'playlistend': 50,
            'ignore_no_formats_error': True,
        },
        'expected_warnings': ['skipping format'],
    }]

    def _real_extract(self, url):
        display_id, community_id, channel_id, sort_by = self._match_valid_url(url).group('id', 'community', 'channel', 'sort')
        if not channel_id:
            channel_id = 'featured'
        if not sort_by:
            sort_by = 'new'

        community_data = self._call_api(
            'communities/view/%s' % community_id, display_id, note='Downloading community info', errnote='Unable to download community info')['community']
        channel_data = traverse_obj(self._call_api(
            'communities/view-channel/%s/%s' % (community_id, channel_id), display_id, note='Downloading channel info', errnote='Unable to download channel info', fatal=False), 'channel') or {}

        title = '%s - %s' % (community_data.get('title'), channel_data['display_name']) if channel_data.get('display_name') else community_data.get('title')
        description = self._parse_content_as_text(
            self._parse_json(community_data.get('description_content', '{}'), display_id, fatal=False) or {})
        return self.playlist_result(
            self._entries('posts/fetch/community/%s?channels[]=%s&channels[]=%s' % (community_id, sort_by, channel_id), display_id, 'Downloading community posts', 'Unable to download community posts'),
            '%s/%s' % (community_id, channel_id), title, description)
