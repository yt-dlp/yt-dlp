# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor

from ..compat import compat_str
from ..utils import (
    parse_iso8601,
    ExtractorError,
    try_get
)


class FancodeVodIE(InfoExtractor):
    IE_NAME = 'fancode:vod'

    _VALID_URL = r'https?://(?:www\.)?fancode\.com/video/(?P<id>[0-9]+)\b'

    _TESTS = [{
        'url': 'https://fancode.com/video/15043/match-preview-pbks-vs-mi',
        'params': {
            'skip_download': True,
            'format': 'bestvideo'
        },
        'info_dict': {
            'id': '6249806281001',
            'ext': 'mp4',
            'title': 'Match Preview: PBKS vs MI',
            'thumbnail': r're:^https?://.*\.jpg$',
            "timestamp": 1619081590,
            'view_count': int,
            'like_count': int,
            'upload_date': '20210422',
            'uploader_id': '6008340455001'
        }
    }, {
        'url': 'https://fancode.com/video/15043',
        'only_matching': True,
    }]

    def _real_extract(self, url):

        BRIGHTCOVE_URL_TEMPLATE = 'https://players.brightcove.net/%s/default_default/index.html?videoId=%s'

        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        brightcove_user_id = self._html_search_regex(
            r'(?:https?://)?players\.brightcove\.net/(\d+)/default_default/index(?:\.min)?\.js',
            webpage, 'user id')

        data = '''{
            "query":"query Video($id: Int\\u0021, $filter: SegmentFilter) { media(id: $id, filter: $filter) { id contentId title contentId publishedTime totalViews totalUpvotes provider thumbnail { src } mediaSource {brightcove } duration isPremium isUserEntitled tags duration }}",
            "variables":{
                "id":%s,
                "filter":{
                    "contentDataType":"DEFAULT"
                }
            },
            "operationName":"Video"
            }''' % video_id

        metadata_json = self._download_json(
            'https://www.fancode.com/graphql', video_id, data=data.encode(), note='Downloading metadata',
            headers={
                'content-type': 'application/json',
                'origin': 'https://fancode.com',
                'referer': url,
            })

        media = try_get(metadata_json, lambda x: x['data']['media'], dict) or {}
        brightcove_video_id = try_get(media, lambda x: x['mediaSource']['brightcove'], compat_str)

        if brightcove_video_id is None:
            raise ExtractorError('Unable to extract brightcove Video ID')

        is_premium = media.get('isPremium')
        if is_premium:
            self.report_warning('this video requires a premium account', video_id)

        return {
            '_type': 'url_transparent',
            'url': BRIGHTCOVE_URL_TEMPLATE % (brightcove_user_id, brightcove_video_id),
            'ie_key': 'BrightcoveNew',
            'id': video_id,
            'title': media['title'],
            'like_count': media.get('totalUpvotes'),
            'view_count': media.get('totalViews'),
            'tags': media.get('tags'),
            'release_timestamp': parse_iso8601(media.get('publishedTime')),
            'availability': self._availability(needs_premium=is_premium),
        }
