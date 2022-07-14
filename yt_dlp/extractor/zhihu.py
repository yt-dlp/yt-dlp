from .common import InfoExtractor
from ..utils import format_field, float_or_none, int_or_none


class ZhihuIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?zhihu\.com/zvideo/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'https://www.zhihu.com/zvideo/1342930761977176064',
        'md5': 'c8d4c9cd72dd58e6f9bc9c2c84266464',
        'info_dict': {
            'id': '1342930761977176064',
            'ext': 'mp4',
            'title': '写春联也太难了吧！',
            'thumbnail': r're:^https?://.*\.jpg',
            'uploader': '桥半舫',
            'timestamp': 1612959715,
            'upload_date': '20210210',
            'uploader_id': '244ecb13b0fd7daf92235288c8ca3365',
            'duration': 146.333,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        zvideo = self._download_json(
            'https://www.zhihu.com/api/v4/zvideos/' + video_id, video_id)
        title = zvideo['title']
        video = zvideo.get('video') or {}

        formats = []
        for format_id, q in (video.get('playlist') or {}).items():
            play_url = q.get('url') or q.get('play_url')
            if not play_url:
                continue
            formats.append({
                'asr': int_or_none(q.get('sample_rate')),
                'filesize': int_or_none(q.get('size')),
                'format_id': format_id,
                'fps': int_or_none(q.get('fps')),
                'height': int_or_none(q.get('height')),
                'tbr': float_or_none(q.get('bitrate')),
                'url': play_url,
                'width': int_or_none(q.get('width')),
            })
        self._sort_formats(formats)

        author = zvideo.get('author') or {}
        url_token = author.get('url_token')

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': video.get('thumbnail') or zvideo.get('image_url'),
            'uploader': author.get('name'),
            'timestamp': int_or_none(zvideo.get('published_at')),
            'uploader_id': author.get('id'),
            'uploader_url': format_field(url_token, None, 'https://www.zhihu.com/people/%s'),
            'duration': float_or_none(video.get('duration')),
            'view_count': int_or_none(zvideo.get('play_count')),
            'like_count': int_or_none(zvideo.get('liked_count')),
            'comment_count': int_or_none(zvideo.get('comment_count')),
        }
