from .common import InfoExtractor
from ..utils import (
    remove_end,
    strftime_or_none,
    strip_or_none,
)
from ..utils.traversal import traverse_obj


class ThreadsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?threads\.net/(?P<uploader>[^/]+)/post/(?P<id>[^/?#&]+)/?(?P<embed>embed.*?)?'

    _TESTS = [{
        'url': 'https://www.threads.net/@tntsportsbr/post/C6cqebdCfBi',
        'info_dict': {
            'id': 'C6cqebdCfBi',
            'ext': 'mp4',
            'title': 'md5:062673d04195aa2d99b8d7a11798cb9d',
            'description': 'md5:fe0c73f9a892fb92efcc67cc075561b0',
            'uploader': 'TNT Sports Brasil',
            'uploader_id': 'tntsportsbr',
            'uploader_url': 'https://www.threads.net/@tntsportsbr',
            'channel': 'tntsportsbr',
            'channel_url': 'https://www.threads.net/@tntsportsbr',
            'timestamp': 1714613811,
            'upload_date': '20240502',
            'like_count': int,
            'channel_is_verified': bool,
            'thumbnail': r're:^https?://.*\.jpg',
        },
    }, {
        'url': 'https://www.threads.net/@felipebecari/post/C6cM_yNPHCF',
        'info_dict': {
            'id': 'C6cM_yNPHCF',
            'ext': 'mp4',
            'title': '@felipebecari • Sobre o futuro dos dois últimos resgatados: tem muita notícia boa! 🐶❤️',
            'description': 'Sobre o futuro dos dois últimos resgatados: tem muita notícia boa! 🐶❤️',
            'uploader': 'Felipe Becari',
            'uploader_id': 'felipebecari',
            'uploader_url': 'https://www.threads.net/@felipebecari',
            'channel': 'felipebecari',
            'channel_url': 'https://www.threads.net/@felipebecari',
            'timestamp': 1714598318,
            'upload_date': '20240501',
            'like_count': int,
            'channel_is_verified': bool,
            'thumbnail': r're:^https?://.*\.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        metadata = {}

        # Try getting videos from json
        json_data = self._search_regex(
            rf'<script[^>]+>(.*"code":"{video_id}".*)</script>',
            webpage, 'main json', fatal=True)

        result = self._search_json(
            r'"result":', json_data,
            'result data', video_id, fatal=True)

        edges = traverse_obj(result, ('data', 'data', 'edges'))

        for node in edges:
            items = traverse_obj(node, ('node', 'thread_items'))

            for item in items:
                post = item.get('post')

                if post and post.get('code') == video_id:
                    formats = []
                    thumbnails = []

                    # Videos
                    if post.get('carousel_media') is not None:  # Handle multiple videos posts
                        media_list = post.get('carousel_media')
                    else:
                        media_list = [post]

                    for media in media_list:
                        videos = media.get('video_versions')

                        if videos:
                            for video in videos:
                                formats.append({
                                    'format_id': '{}-{}'.format(media.get('pk'), video['type']),  # id-type
                                    'url': video['url'],
                                    'width': media.get('original_width'),
                                    'height': media.get('original_height'),
                                })

                    # Thumbnails
                    thumbs = traverse_obj(post, ('image_versions2', 'candidates'))

                    for thumb in thumbs:
                        thumbnails.append({
                            'url': thumb['url'],
                            'width': thumb['width'],
                            'height': thumb['height'],
                        })

                    # Metadata
                    metadata.setdefault('uploader_id', traverse_obj(post, ('user', 'username')))
                    metadata.setdefault('channel_is_verified', traverse_obj(post, ('user', 'is_verified')))
                    metadata.setdefault('uploader_url', 'https://www.threads.net/@{}'.format(traverse_obj(post, ('user', 'username'))))
                    metadata.setdefault('timestamp', post.get('taken_at'))
                    metadata.setdefault('like_count', post.get('like_count'))

        # Try getting metadata
        metadata['id'] = video_id
        metadata['title'] = strip_or_none(remove_end(self._html_extract_title(webpage), '• Threads'))
        metadata['description'] = self._og_search_description(webpage)

        metadata['channel'] = metadata.get('uploader_id')
        metadata['channel_url'] = metadata.get('uploader_url')
        metadata['uploader'] = self._search_regex(r'(.*?) \(', self._og_search_title(webpage), 'uploader', metadata.get('uploader_id'))
        metadata['upload_date'] = strftime_or_none(metadata.get('timestamp'))

        return {
            **metadata,
            'formats': formats,
            'thumbnails': thumbnails,
        }


class ThreadsIOSIE(InfoExtractor):
    IE_DESC = 'IOS barcelona:// URL'
    _VALID_URL = r'barcelona://media\?shortcode=(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'barcelona://media?shortcode=C6fDehepo5D',
        'info_dict': {
            'id': 'C6fDehepo5D',
            'ext': 'mp4',
            'title': 'md5:dc92f960981b8b3a33eba9681e9fdfc6',
            'description': 'md5:0c36a7e67e1517459bc0334dba932164',
            'uploader': 'Sa\u0303o Paulo Futebol Clube',
            'uploader_id': 'saopaulofc',
            'uploader_url': 'https://www.threads.net/@saopaulofc',
            'channel': 'saopaulofc',
            'channel_url': 'https://www.threads.net/@saopaulofc',
            'timestamp': 1714694014,
            'upload_date': '20240502',
            'like_count': int,
            'channel_is_verified': bool,
            'thumbnail': r're:^https?://.*\.jpg',
        },
        'add_ie': ['Threads'],
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # Threads doesn't care about the user url, it redirects to the right one
        # So we use ** instead so that we don't need to find it
        return self.url_result(f'http://www.threads.net/**/post/{video_id}', ThreadsIE, video_id)
