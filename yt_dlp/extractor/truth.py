from .common import InfoExtractor

from ..utils import (
    clean_html,
    int_or_none,
    unified_timestamp,
    strip_or_none
)


class TruthIE(InfoExtractor):
    """Extract videos from posts on Donald Trump's truthsocial.com."""

    _VALID_URL = r'https://truthsocial\.com/@[^/]+/posts/(?P<id>[\d]+)'
    _TESTS = [
        {
            'url': 'https://truthsocial.com/@realDonaldTrump/posts/108779000807761862',
            'md5': '4a5fb1470c192e493d9efd6f19e514d3',
            'info_dict': {
                'id': '108779000807761862',
                'ext': 'qt',
                'title': '0d8691160c73d663',
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
                'title': 'md5:de2fc49045bf92bb8dc97e56503b150f',
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
    _GEO_COUNTRIES = ['US']  # The site is only available in the US

    def _real_extract(self, url):
        # Get data from API
        video_id = self._match_id(url)
        status = self._download_json(
            'https://truthsocial.com/api/v1/statuses/' + video_id,
            video_id
        )

        # Pull out video
        url = status['media_attachments'][0]['url']

        # Return the staff
        account = status.get('account') or {}
        uploader_id = strip_or_none(account.get('username'))
        return {
            'id': video_id,
            'url': url,
            'title': strip_or_none(clean_html(status.get('content'))) or self._generic_title(url),
            'timestamp': unified_timestamp(status.get('created_at')),
            'uploader': strip_or_none(account.get('display_name')),
            'uploader_id': uploader_id,
            'uploader_url': ('https://truthsocial.com/@' + uploader_id) if uploader_id else None,
            'repost_count': int_or_none(status.get('reblogs_count')),
            'like_count': int_or_none(status.get('favourites_count')),
            'comment_count': int_or_none(status.get('replies_count')),
        }
