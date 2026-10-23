import json
import urllib.parse

from .common import InfoExtractor
from .youtube import YoutubeIE
from ..utils import (
    ExtractorError,
    bug_reports_message,
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
            'title': 'Бан? А! Бан! (Phasmophobia)',
            'alt_title': 'Бан? А! Бан! (Phasmophobia)',
            'channel': 'Kuplinov',
            'channel_id': '7958701',
            'timestamp': 1655031975,
            'upload_date': '20220612',
            'release_timestamp': 1655049000,
            'release_date': '20220612',
            'modified_timestamp': 1743328648,
            'modified_date': '20250330',
            'tags': ['куплинов', 'phasmophobia'],
            'like_count': int,
            'ext': 'mp4',
            'duration': 105,
            'view_count': int,
            'thumbnail': r're:^https://iv\.okcdn\.ru/videoPreview\?',
        },
    }, {
        # single ok_video with truncated title
        'url': 'https://boosty.to/kuplinov/posts/cc09b7f9-121e-40b8-9392-4a075ef2ce53',
        'info_dict': {
            'id': 'fb5ea762-6303-4557-9a17-157947326810',
            'title': 'Какая там активность была? Не слышу! Повтори еще пару раз! (Phas',
            'alt_title': 'Какая там активность была? Не слышу! Повтори еще пару раз! (Phasmophobia)',
            'channel': 'Kuplinov',
            'channel_id': '7958701',
            'timestamp': 1655031930,
            'upload_date': '20220612',
            'release_timestamp': 1655048400,
            'release_date': '20220612',
            'modified_timestamp': 1743328616,
            'modified_date': '20250330',
            'tags': ['куплинов', 'phasmophobia'],
            'like_count': int,
            'ext': 'mp4',
            'duration': 39,
            'view_count': int,
            'thumbnail': r're:^https://iv\.okcdn\.ru/videoPreview\?',
        },
    }, {
        # multiple ok_video
        'url': 'https://boosty.to/maddyson/posts/0c652798-3b35-471f-8b48-a76a0b28736f',
        'info_dict': {
            'id': '0c652798-3b35-471f-8b48-a76a0b28736f',
            'title': 'то что не пропустил юта6',
            'channel': 'Илья Давыдов',
            'channel_id': '6808257',
            'timestamp': 1694017040,
            'upload_date': '20230906',
            'release_timestamp': 1694017040,
            'release_date': '20230906',
            'modified_timestamp': 1694071178,
            'modified_date': '20230907',
            'like_count': int,
        },
        'playlist_count': 3,
        'playlist': [{
            'info_dict': {
                'id': 'cc325a9f-a563-41c6-bf47-516c1b506c9a',
                'title': 'то что не пропустил юта6',
                'channel': 'Илья Давыдов',
                'channel_id': '6808257',
                'timestamp': 1694017040,
                'upload_date': '20230906',
                'release_timestamp': 1694017040,
                'release_date': '20230906',
                'modified_timestamp': 1694071178,
                'modified_date': '20230907',
                'like_count': int,
                'ext': 'mp4',
                'duration': 31204,
                'view_count': int,
                'thumbnail': r're:^https://i\.mycdn\.me/videoPreview\?',
            },
        }, {
            'info_dict': {
                'id': 'd07b0a72-9493-4512-b54e-55ce468fd4b7',
                'title': 'то что не пропустил юта6',
                'channel': 'Илья Давыдов',
                'channel_id': '6808257',
                'timestamp': 1694017040,
                'upload_date': '20230906',
                'release_timestamp': 1694017040,
                'release_date': '20230906',
                'modified_timestamp': 1694071178,
                'modified_date': '20230907',
                'like_count': int,
                'ext': 'mp4',
                'duration': 25704,
                'view_count': int,
                'thumbnail': r're:^https://i\.mycdn\.me/videoPreview\?',
            },
        }, {
            'info_dict': {
                'id': '4a3bba32-78c8-422a-9432-2791aff60b42',
                'title': 'то что не пропустил юта6',
                'channel': 'Илья Давыдов',
                'channel_id': '6808257',
                'timestamp': 1694017040,
                'upload_date': '20230906',
                'release_timestamp': 1694017040,
                'release_date': '20230906',
                'modified_timestamp': 1694071178,
                'modified_date': '20230907',
                'like_count': int,
                'ext': 'mp4',
                'duration': 31867,
                'view_count': int,
                'thumbnail': r're:^https://i\.mycdn\.me/videoPreview\?',
            },
        }],
        'skip': 'post has been deleted',
    }, {
        # single external video (youtube)
        'url': 'https://boosty.to/futuremusicproduction/posts/32a8cae2-3252-49da-b285-0e014bc6e565',
        'info_dict': {
            'id': '-37FW_YQ3B4',
            'title': 'Afro | Deep House FREE FLP',
            'media_type': 'video',
            'upload_date': '20250829',
            'timestamp': 1756466005,
            'channel': 'Future Music Production',
            'tags': 'count:0',
            'like_count': int,
            'ext': 'm4a',
            'duration': 170,
            'view_count': int,
            'thumbnail': r're:^https://i\.ytimg\.com/',
            'age_limit': 0,
            'availability': 'public',
            'categories': list,
            'channel_follower_count': int,
            'channel_id': 'UCKVYrFBYmci1e-T8NeHw2qg',
            'channel_url': r're:^https://www\.youtube\.com/',
            'comment_count': int,
            'description': str,
            'live_status': str,
            'playable_in_embed': bool,
            'uploader': str,
            'uploader_id': str,
            'uploader_url': r're:^https://www\.youtube\.com/',
        },
        'expected_warnings': [
            'Remote components challenge solver script',
            'n challenge solving failed',
        ],
    }]

    _MP4_TYPES = ('tiny', 'lowest', 'low', 'medium', 'high', 'full_hd', 'quad_hd', 'ultra_hd')

    def _extract_formats(self, player_urls, video_id):
        formats = []
        quality = qualities(self._MP4_TYPES)
        for player_url in traverse_obj(player_urls, lambda _, v: url_or_none(v['url'])):
            url = player_url['url']
            format_type = player_url.get('type')
            if format_type in ('hls', 'hls_live', 'live_ondemand_hls', 'live_playback_hls'):
                formats.extend(self._extract_m3u8_formats(url, video_id, m3u8_id='hls', fatal=False))
            elif format_type in ('dash', 'dash_live', 'live_playback_dash'):
                formats.extend(self._extract_mpd_formats(url, video_id, mpd_id='dash', fatal=False))
            elif format_type in self._MP4_TYPES:
                formats.append({
                    'url': url,
                    'ext': 'mp4',
                    'format_id': format_type,
                    'quality': quality(format_type),
                })
            else:
                self.report_warning(f'Unknown format type: {format_type!r}')
        return formats

    def _real_extract(self, url):
        user, post_id = self._match_valid_url(url).group('user', 'post_id')

        auth_headers = {}
        auth_cookie = self._get_cookies('https://boosty.to/').get('auth')
        if auth_cookie is not None:
            try:
                auth_data = json.loads(urllib.parse.unquote(auth_cookie.value))
                auth_headers['Authorization'] = f'Bearer {auth_data["accessToken"]}'
            except (json.JSONDecodeError, KeyError):
                self.report_warning(f'Failed to extract token from auth cookie{bug_reports_message()}')

        post = self._download_json(
            f'https://api.boosty.to/v1/blog/{user}/post/{post_id}', post_id,
            note='Downloading post data', errnote='Unable to download post data', headers=auth_headers)

        post_title = post.get('title')
        if not post_title:
            self.report_warning('Unable to extract post title. Falling back to parsing html page')
            webpage = self._download_webpage(url, video_id=post_id)
            post_title = self._og_search_title(webpage, default=None) or self._html_extract_title(webpage)

        common_metadata = {
            'title': post_title,
            **traverse_obj(post, {
                'channel': ('user', 'name', {str}),
                'channel_id': ('user', 'id', {str_or_none}),
                'timestamp': ('createdAt', {int_or_none}),
                'release_timestamp': ('publishTime', {int_or_none}),
                'modified_timestamp': ('updatedAt', {int_or_none}),
                'tags': ('tags', ..., 'title', {str}),
                'like_count': ('count', 'likes', {int_or_none}),
            }),
        }
        entries = []
        for item in traverse_obj(post, ('data', ..., {dict})):
            item_type = item.get('type')
            if item_type == 'video' and url_or_none(item.get('url')):
                entries.append(self.url_result(item['url'], YoutubeIE))
            elif item_type == 'ok_video':
                video_id = item.get('id') or post_id
                entries.append({
                    'id': video_id,
                    'alt_title': post_title,
                    'formats': self._extract_formats(item.get('playerUrls'), video_id),
                    **common_metadata,
                    **traverse_obj(item, {
                        'title': ('title', {str}),
                        'duration': ('duration', {int_or_none}),
                        'view_count': ('viewsCounter', {int_or_none}),
                        'thumbnail': (('preview', 'defaultPreview'), {url_or_none}),
                    }, get_all=False)})

        if not entries and not post.get('hasAccess'):
            self.raise_login_required('This post requires a subscription', metadata_available=True)
        elif not entries:
            raise ExtractorError('No videos found', expected=True)
        if len(entries) == 1:
            return entries[0]
        return self.playlist_result(entries, post_id, post_title, **common_metadata)
