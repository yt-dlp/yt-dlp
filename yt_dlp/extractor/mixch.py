from .common import InfoExtractor
from ..networking.exceptions import HTTPError
from ..utils import (
    ExtractorError,
    UserNotLive,
    bool_or_none,
    int_or_none,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class MixchIE(InfoExtractor):
    IE_NAME = 'mixch'
    _VALID_URL = r'https?://(?:www\.)?mixch\.tv/u/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://mixch.tv/u/16943797/live',
        'skip': 'don\'t know if this live persists',
        'info_dict': {
            'id': '16943797',
            'ext': 'mp4',
            'title': '#EntView #カリナ #セブチ 2024-05-05 06:58',
            'comment_count': int,
            'view_count': int,
            'timestamp': 1714726805,
            'uploader': 'Ent.View K-news🎶💕',
            'uploader_id': '16943797',
            'live_status': 'is_live',
            'upload_date': '20240503',
        },
    }, {
        'url': 'https://mixch.tv/u/16137876/live',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._download_json(f'https://mixch.tv/api-web/users/{video_id}/live', video_id)
        if not traverse_obj(data, ('liveInfo', {dict})):
            raise UserNotLive(video_id=video_id)

        return {
            'id': video_id,
            'uploader_id': video_id,
            **traverse_obj(data, {
                'title': ('liveInfo', 'title', {str}),
                'comment_count': ('liveInfo', 'comments', {int_or_none}),
                'view_count': ('liveInfo', 'visitor', {int_or_none}),
                'timestamp': ('liveInfo', 'created', {int_or_none}),
                'uploader': ('broadcasterInfo', 'name', {str}),
            }),
            'formats': [{
                'format_id': 'hls',
                'url': data['liveInfo']['hls'],
                'ext': 'mp4',
                'protocol': 'm3u8',
            }],
            'is_live': True,
            '__post_extractor': self.extract_comments(video_id),
        }

    def _get_comments(self, video_id):
        yield from traverse_obj(self._download_json(
            f'https://mixch.tv/api-web/lives/{video_id}/messages', video_id,
            note='Downloading comments', errnote='Failed to download comments'), (..., {
                'author': ('name', {str}),
                'author_id': ('user_id', {str_or_none}),
                'id': ('message_id', {str}, {lambda x: x or None}),
                'text': ('body', {str}),
                'timestamp': ('created', {int}),
            }))


class MixchArchiveIE(InfoExtractor):
    IE_NAME = 'mixch:archive'
    _VALID_URL = r'https?://(?:www\.)?mixch\.tv/archive/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://mixch.tv/archive/421',
        'skip': 'paid video, no DRM. expires at Jan 23',
        'info_dict': {
            'id': '421',
            'ext': 'mp4',
            'title': '96NEKO SHOW TIME',
        },
    }, {
        'url': 'https://mixch.tv/archive/1213',
        'skip': 'paid video, no DRM. expires at Dec 31, 2023',
        'info_dict': {
            'id': '1213',
            'ext': 'mp4',
            'title': '【特別トーク番組アーカイブス】Merm4id×燐舞曲 2nd LIVE「VERSUS」',
            'release_date': '20231201',
            'thumbnail': str,
        },
    }, {
        'url': 'https://mixch.tv/archive/1214',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        try:
            info_json = self._download_json(
                f'https://mixch.tv/api-web/archive/{video_id}', video_id)['archive']
        except ExtractorError as e:
            if isinstance(e.cause, HTTPError) and e.cause.status == 401:
                self.raise_login_required()
            raise

        return {
            'id': video_id,
            'title': traverse_obj(info_json, ('title', {str})),
            'formats': self._extract_m3u8_formats(info_json['archiveURL'], video_id),
            'thumbnail': traverse_obj(info_json, ('thumbnailURL', {url_or_none})),
        }


class MixchMovieIE(InfoExtractor):
    IE_NAME = 'mixch:movie'
    _VALID_URL = r'https?://(?:www\.)?mixch\.tv/m/(?P<id>\w+)'

    _TESTS = [{
        'url': 'https://mixch.tv/m/Ve8KNkJ5',
        'info_dict': {
            'id': 'Ve8KNkJ5',
            'title': '夏☀️\nムービーへのポイントは本イベントに加算されないので配信にてお願い致します🙇🏻\u200d♀️\n#TGCCAMPUS #ミス東大 #ミス東大2024 ',
            'ext': 'mp4',
            'uploader': 'ミス東大No.5 松藤百香🍑💫',
            'uploader_id': 12299174,
            'channel_follower_count': int,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'timestamp': int,
            'uploader_url': 'https://mixch.tv/u/12299174',
            'live_status': 'not_live',
            'upload_date': '20240819',
        },
    }, {
        'url': 'https://mixch.tv/m/61DzpIKE',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._download_json(
            f'https://mixch.tv/api-web/movies/{video_id}', video_id)
        return {
            'id': video_id,
            'formats': [{
                'format_id': 'mp4',
                'url': data['movie']['file'],
                'ext': 'mp4',
            }],
            **traverse_obj(data, {
                'title': ('movie', 'title', {str}),
                'thumbnail': ('movie', 'thumbnailURL', {url_or_none}),
                'uploader': ('ownerInfo', 'name', {str}),
                'uploader_id': ('ownerInfo', 'id', {int_or_none}),
                'channel_follower_count': ('ownerInfo', 'fan', {int_or_none}),
                'view_count': ('ownerInfo', 'view', {int_or_none}),
                'like_count': ('movie', 'favCount', {int_or_none}),
                'comment_count': ('movie', 'commentCount', {int_or_none}),
                'timestamp': ('movie', 'published', {int_or_none}),
                'uploader_url': ('ownerInfo', 'id', {lambda x: x and f'https://mixch.tv/u/{x}'}),
            }),
            'live_status': 'not_live',
            '__post_extractor': self.extract_comments(video_id),
        }

    def _get_comments(self, video_id):
        # Comments are organized in a json chain, connected with 'nextCursor' property.
        # There are up to 20 comments in one json file.
        COMMENTS_LIMIT = 20
        # If json files are downloaded too frequently, the server might ban all the access from your IP.
        comments_left = int_or_none(self._configuration_arg('max_comments', [''])[0]) or 120
        fetch_interval_sec = int_or_none(self._configuration_arg('fetch_interval_sec', [''])[0])

        base_url = f'https://mixch.tv/api-web/movies/{video_id}/comments'
        has_next = True
        next_cursor = ''
        fragment = 1

        while has_next and (comments_left > 0):
            data = self._download_json(
                base_url, video_id,
                note=f'Downloading comments, fragment {fragment}', errnote='Failed to download comments',
                query={'cursor': next_cursor, 'limit': COMMENTS_LIMIT})
            fragment += 1
            comments_left -= COMMENTS_LIMIT

            # Some of the 'comments' are not real comments but gifts.
            # Only real comments are extracted here.
            yield from traverse_obj(data, ('comments', lambda _, v: v['comment'], {
                'author': ('user_name', {str}),
                'author_id': ('user_id', {int_or_none}),
                'author_thumbnail': ('profile_image_url', {url_or_none}),
                'id': ('id', {int_or_none}),
                'text': ('comment', {str_or_none}),
                'timestamp': ('created', {int_or_none}),
            }))

            if fetch_interval_sec:
                self._sleep(fetch_interval_sec, video_id)

            has_next = traverse_obj(data, ('hasNext'), {bool_or_none})
            next_cursor = traverse_obj(data, ('nextCursor'), {str_or_none})
