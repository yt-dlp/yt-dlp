import itertools
import uuid

from .common import InfoExtractor
from ..utils import unified_strdate


class FikfapBaseIE(InfoExtractor):
    _API_BASE = 'https://api.fikfap.com'

    def _call_api(self, path, video_id, note='Downloading Post Information'):
        return self._download_json(
            f'{self._API_BASE}/{path}',
            video_id,
            headers={
                'Origin': 'https://fikfap.com',
                'Referer': 'https://fikfap.com/',
                'Authorization-Anonymous': str(uuid.uuid4()),
            },
            note=note,
        )

    def _extract_post(self, post, video_id):
        stream = post.get('videoStreamUrl')
        if not stream:
            return []
        formats = self._extract_m3u8_formats(
            stream, video_id,
            ext='mp4',
            headers={
                'Origin': 'https://fikfap.com',
                'Referer': 'https://fikfap.com/',
            },
        )
        for fmt in formats:
            fmt.setdefault('http_headers', {}).update({
                'Origin': 'https://fikfap.com',
                'Referer': 'https://fikfap.com/',
            })
        yield {
            'id': video_id,
            'formats': formats,
            'title': post['label'],
            'thumbnail': post['thumbnailStreamUrl'],
            'likes_count': post['likesCount'],
            'upload_date': unified_strdate(post['publishedAt']),
            'view_count': post['viewsCount'],
            'comments_count': post['commentsCount'],
            'author': post['author'],
            'age_limit': 18,
        }


class FikfapIE(FikfapBaseIE):
    _VALID_URL = r'https?://(?:www\.)?fikfap\.com/(?:user/(?P<username>[^/]+)/post/|post/)(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://fikfap.com/post/503729',
        'info_dict': {
            'id': '503729',
        },
    }]
    IE_NAME = 'fikfap'

    def _real_extract(self, url):
        _, postid = self._match_valid_url(url).groups()
        data = self._call_api(f'/posts/{postid}', postid)
        return next(self._extract_post(data, postid))


class FikfapPlaylistBaseIE(FikfapBaseIE):
    def _parse_posts(self, video_id):
        _after_id = None

        for post in itertools.count(1):
            path = f'/{self._MIDDLE_NAME}/{video_id}/posts?amount=21'
            if _after_id:
                path += f'&afterId={_after_id}'
            post_data = self._call_api(path, video_id, f'Downloading Page - {post} information')
            if not post_data:
                break
            for pst in post_data:
                yield from self._extract_post(pst, video_id)
            _after_id = post_data[-1].get('postId')
            if len(post_data) < 21 and not _after_id:
                break

    def _real_extract(self, url):
        video_id = self._match_valid_url(url).group('id')
        return self.playlist_result(self._parse_posts(video_id), video_id, video_id)


class FikfapUserIE(FikfapPlaylistBaseIE):
    _VALID_URL = r'https?://(?:www\.)?fikfap\.com/user/(?P<id>[^/?#]+)'
    IE_NAME = 'fikfap:user'
    _TESTS = [{
        'url': 'https://fikfap.com/user/Mrmrscumzalot69',
        'info_dict': {
            'id': 'Mrmrscumzalot69',
        },
        'playlist_mincount': 43,
    }]

    _MIDDLE_NAME = 'profile/username'


class FikfapCollectionIE(FikfapPlaylistBaseIE):
    _VALID_URL = r'https?://(?:www\.)?fikfap\.com/collections/(?P<id>[^/?#]+)'
    IE_NAME = 'fikfap:collection'
    _TESTS = [{
        'url': 'https://fikfap.com/user/Mrmrscumzalot69',
        'info_dict': {
            'id': '6f731e69-4382-4c03-ae26-149243223ab6',
        },
        'playlist_count': 10,
    }]

    _MIDDLE_NAME = 'collections'
