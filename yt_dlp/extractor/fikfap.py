import uuid

from .common import InfoExtractor
from ..utils import OnDemandPagedList, unified_strdate


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

        return {
            'id': video_id,
            'formats': formats,
            'title': post.get('label'),
            'thumbnail': post.get('thumbnailStreamUrl'),
            'likes_count': post.get('likesCount'),
            'upload_date': unified_strdate(post.get('publishedAt')),
            'view_count': post.get('viewsCount'),
            'comments_count': post.get('commentsCount'),
            'author': post.get('author'),
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
        return self._extract_post(data, postid)


class FikfapPlaylistBaseIE(FikfapBaseIE):
    def _real_extract(self, url):
        video_id = self._match_valid_url(url).group('id')
        amount = 21
        after_state = ''

        def fetch_page(page):
            nonlocal after_state
            path = f'/{self._MIDDLE_NAME}/{video_id}/posts?amount={amount}&afterId={after_state}'

            data = self._call_api(path, video_id, f'Downloading Page {page}')
            if not data:
                return []

            after_state = data[-1].get('postId')

            return [self._extract_post(pst, video_id) for pst in data]

        return self.playlist_result(
            OnDemandPagedList(fetch_page, 21),
            playlist_id=video_id,
            playlist_title=video_id,
        )


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
        'url': 'https://fikfap.com/collections/6f731e69-4382-4c03-ae26-149243223ab6',
        'info_dict': {
            'id': '6f731e69-4382-4c03-ae26-149243223ab6',
        },
        'playlist_count': 10,
    }]

    _MIDDLE_NAME = 'collections'
