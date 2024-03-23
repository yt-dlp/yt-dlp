from .common import InfoExtractor
from ..utils import (
    clean_html,
    format_field,
    int_or_none,
    strip_or_none,
    traverse_obj,
    unified_timestamp,
)


class TruthIE(InfoExtractor):
    _VALID_URL = r'https?://truthsocial\.com/@[^/]+/posts/(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'https://truthsocial.com/@realDonaldTrump/posts/108779000807761862',
            'md5': '4a5fb1470c192e493d9efd6f19e514d3',
            'info_dict': {
                'id': '108779000807761862',
                'ext': 'qt',
                'title': 'Truth video #108779000807761862',
                'timestamp': 1659835827,
                'upload_date': '20220807',
                'uploader': 'Donald J. Trump',
                'uploader_id': 'realDonaldTrump',
                'uploader_url': 'https://truthsocial.com/@realDonaldTrump',
                'repost_count': int,
                'comment_count': int,
                'like_count': int,
            },
        },
        {
            'url': 'https://truthsocial.com/@ProjectVeritasAction/posts/108618228543962049',
            'md5': 'fd47ba68933f9dce27accc52275be9c3',
            'info_dict': {
                'id': '108618228543962049',
                'ext': 'mp4',
                'title': 'md5:debde7186cf83f60ff7b44dbb9444e35',
                'description': 'md5:de2fc49045bf92bb8dc97e56503b150f',
                'timestamp': 1657382637,
                'upload_date': '20220709',
                'uploader': 'Project Veritas Action',
                'uploader_id': 'ProjectVeritasAction',
                'uploader_url': 'https://truthsocial.com/@ProjectVeritasAction',
                'repost_count': int,
                'comment_count': int,
                'like_count': int,
            },
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        status = self._download_json(f'https://truthsocial.com/api/v1/statuses/{video_id}', video_id)
        uploader_id = strip_or_none(traverse_obj(status, ('account', 'username')))
        return {
            'id': video_id,
            'url': status['media_attachments'][0]['url'],
            'title': '',
            'description': strip_or_none(clean_html(status.get('content'))) or None,
            'timestamp': unified_timestamp(status.get('created_at')),
            'uploader': strip_or_none(traverse_obj(status, ('account', 'display_name'))),
            'uploader_id': uploader_id,
            'uploader_url': format_field(uploader_id, None, 'https://truthsocial.com/@%s'),
            'repost_count': int_or_none(status.get('reblogs_count')),
            'like_count': int_or_none(status.get('favourites_count')),
            'comment_count': int_or_none(status.get('replies_count')),
        }
