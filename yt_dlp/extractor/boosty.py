from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import (
    ExtractorError,
    int_or_none,
    qualities,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class BoostyIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?boosty\.to/(?P<user>[^/#?]+)/posts/(?P<post_id>[^/#?]+)'
    _TESTS = [{
        # single ok_video
        'url': 'https://boosty.to/kuplinov/posts/e55d050c-e3bb-4873-a7db-ac7a49b40c38',
        'info_dict': {
            'id': 'd7473824-352e-48e2-ae53-d4aa39459968',
            'title': 'phasma_3',
            'channel': 'Kuplinov',
            'timestamp': 1655049000,
            'upload_date': '20220612',
            'modified_timestamp': 1668680993,
            'modified_date': '20221117',
            'tags': ['куплинов', 'phasmophobia'],
            'like_count': int,
            'ext': 'mp4',
            'duration': 105,
            'view_count': int,
            'thumbnail': r're:^https://i\.mycdn\.me/videoPreview\?',
        },
    }, {
        # multiple ok_video
        'url': 'https://boosty.to/maddyson/posts/0c652798-3b35-471f-8b48-a76a0b28736f',
        'info_dict': {
            'id': '0c652798-3b35-471f-8b48-a76a0b28736f',
            'title': 'то что не пропустил юта6',
            'channel': 'Илья Давыдов',
            'timestamp': 1694017040,
            'upload_date': '20230906',
            'modified_timestamp': 1694071178,
            'modified_date': '20230907',
            'tags': [],
            'like_count': int,
        },
        'playlist_count': 3,
        'playlist': [{
            'info_dict': {
                'id': 'cc325a9f-a563-41c6-bf47-516c1b506c9a',
                'title': 'то что не пропустил юта6',
                'ext': 'mp4',
                'duration': 31204,
                'view_count': int,
                'thumbnail': r're:^https://i\.mycdn\.me/videoPreview\?',
            },
        }, {
            'info_dict': {
                'id': 'd07b0a72-9493-4512-b54e-55ce468fd4b7',
                'title': 'то что не пропустил юта6',
                'ext': 'mp4',
                'duration': 25704,
                'view_count': int,
                'thumbnail': r're:^https://i\.mycdn\.me/videoPreview\?',
            },
        }, {
            'info_dict': {
                'id': '4a3bba32-78c8-422a-9432-2791aff60b42',
                'title': 'то что не пропустил юта6',
                'ext': 'mp4',
                'duration': 31867,
                'view_count': int,
                'thumbnail': r're:^https://i\.mycdn\.me/videoPreview\?',
            },
        }],
    }, {
        # single external video (youtube)
        'url': 'https://boosty.to/denischuzhoy/posts/6094a487-bcec-4cf8-a453-43313b463c38',
        'info_dict': {
            'id': 'EXelTnve5lY',
            'title': '4Класс',
            'channel': 'Денис Чужой',
            'timestamp': 1619380873,
            'upload_date': '20210425',
            'modified_timestamp': 1653321155,
            'modified_date': '20220523',
            'tags': [],
            'like_count': int,
            'ext': 'mp4',
            'duration': 816,
            'view_count': int,
            'thumbnail': r're:^https://i\.ytimg\.com/',
            # youtube fields
            'age_limit': 0,
            'availability': 'public',
            'categories': list,
            'channel_follower_count': int,
            'channel_id': 'UCCzVNbWZfYpBfyofCCUD_0w',
            'channel_is_verified': bool,
            'channel_url': r're:^https://www\.youtube\.com/',
            'comment_count': int,
            'description': str,
            'heatmap': 'count:100',
            'live_status': str,
            'playable_in_embed': bool,
            'uploader': str,
            'uploader_id': str,
            'uploader_url': r're:^https://www\.youtube\.com/',
        },
    }]

    def _real_extract(self, url):
        user, post_id = self._match_valid_url(url).group('user', 'post_id')
        post = self._download_json(
            f'https://api.boosty.to/v1/blog/{user}/post/{post_id}', post_id,
            note='Downloading post data', errnote='Unable to download post data')

        post_title = self._extract_title(post, post_id, url)
        entries = self._extract_entries(post, post_id, post_title)
        if not entries:
            raise ExtractorError(
                'no video found', video_id=post_id, expected=True)
        result = {
            'id': post_id,
            'title': post_title,
            'channel': traverse_obj(post, ('user', 'name')),
            'timestamp': dict_get(post, ('publishTime', 'createdAt')),
            'modified_timestamp': post.get('updatedAt'),
            'tags': [tag['title'] for tag in post.get('tags', [])],
            'like_count': traverse_obj(post, ('count', 'likes')),
        }
        if len(entries) == 1:
            result.update(entries[0])
        else:
            result['_type'] = 'playlist'
            result['entries'] = entries
        return result

    def _extract_title(self, post, post_id, url):
        title = post.get('title')
        if title:
            return title
        # falling back to parsing html page as a last resort
        webpage = self._download_webpage(url, video_id=post_id)
        return (
            self._og_search_title(webpage, fatal=False)
            or self._html_extract_title(webpage, fatal=True))

    def _extract_entries(self, post, post_id, post_title):
        entries = []
        for item in post['data']:
            url = None
            formats = None
            item_id = item.get('id', post_id)
            item_type = item.get('type')
            if item_type == 'video':
                url = item.get('url')
            elif item_type == 'ok_video':
                formats = self._extract_formats(
                    item.get('playerUrls', []), item_id)
            if not url and not formats:
                continue
            entry = {
                'id': item_id,
                'title': item.get('title', post_title),
                'duration': item.get('duration'),
                'view_count': item.get('viewsCounter'),
                'thumbnail': dict_get(item, ('preview', 'defaultPreview')),
            }
            if url:
                entry['_type'] = 'url_transparent'
                entry['url'] = url
            elif formats:
                entry['formats'] = formats
            entries.append(entry)
        return entries

    def _extract_formats(self, player_urls, post_id):
        formats = []
        for player_url in player_urls:
            url = player_url.get('url')
            if not url:
                continue
            _type = player_url.get('type')
            if 'hls' in _type:
                # 'hls', 'hls_live'
                formats.extend(self._extract_m3u8_formats(
                    url, video_id=post_id, fatal=False))
            elif 'dash' in _type:
                # 'dash', 'dash_live'
                formats.extend(self._extract_mpd_formats(
                    url, video_id=post_id, fatal=False))
            else:
                # one of: 'tiny', 'low', etc.; see _get_quality for full list
                formats.append({
                    'url': url,
                    'ext': 'mp4',
                    'format_id': _type,
                })
        for format in formats:
            # .../type/<d>/... or ...&type=<d>&...
            format_type = self._search_regex(
                r'\btype[/=](\d)([^\d]|$)', format['url'],
                'format type', default=None,
            )
            if format_type:
                format['quality'] = self._get_quality(format_type)
        return formats

    _get_quality = staticmethod(qualities((
        '4',  # tiny = 144p
        '0',  # lowest = 240p
        '1',  # low = 360p
        '2',  # medium = 480p
        '3',  # high = 720p
        '5',  # full_hd = 1080p
        '6',  # quad_hd = 1440p
        '7',  # ultra_hd = 2160p
    )))
