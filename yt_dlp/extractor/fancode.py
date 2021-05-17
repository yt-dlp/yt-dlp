# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    parse_iso8601,
    random_user_agent,
    RegexNotFoundError
)


class FancodeVodIE(InfoExtractor):
    IE_NAME = 'fancode:vod'

    _VALID_URL = r'https?://(?:www\.)?fancode\.com/video/(?P<id>[0-9]+)/[-_\w]+/?'

    _TEST = {
        'url': 'https://fancode.com/video/15043/match-preview-pbks-vs-mi',
        'md5': '0cf97d19ce68c9765512f36fbb4447bd',
        'params':{
            'format':'bestvideo',
            'skip_download': True,
        },
        'info_dict': {
            'id': '6249806281001',
            'ext': 'mp4',
            'title': 'Match Preview: PBKS vs MI',
            'thumbnail': r're:^https?://.*\.jpg$',
            "timestamp": 1619081590,
            'view_count': int,
            'like_count': int,
            "upload_date": "20210422",
            "uploader_id": "6008340455001",
        }
        
    }

    def _real_extract(self, url):

        GQL_URL = "https://www.fancode.com/graphql"
        BRIGHTCOVE_URL_TEMPLATE = "https://players.brightcove.net/%s/default_default/index.html?videoId=%s"

        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        brightcove_user_id = self._html_search_regex(r'(?:https?://)?players\.brightcove\.net/(\d+)/default_default/index(?:\.min)?\.js', webpage, "user id")

        headers = {
            'user-agent': random_user_agent(),
            'content-type': 'application/json',  # has to be set otherwise api errors out
            'origin': 'https://fancode.com',
            'referer': 'https://fancode.com/',
        }

        data = '''{
            "query":"query Video($id: Int\\u0021, $filter: SegmentFilter) { media(id: $id, filter: $filter) { id contentId title contentId publishedTime totalViews totalUpvotes provider thumbnail { src } mediaSource {brightcove } duration isPremium isUserEntitled tags duration }}",
            "variables":{
                "id":%s,
                "filter":{
                    "contentDataType":"DEFAULT"
                }
            },
            "operationName":"Video"
            }'''

        metadata_json = self._download_json(GQL_URL, video_id, data=str.encode(data % video_id), headers=headers, note="Downloading metadata")
        brightcove_video_id = metadata_json.get('data').get('media').get('mediaSource').get('brightcove')

        if brightcove_video_id is None:
            raise RegexNotFoundError('Unable to extract brightcove Video ID')

        if metadata_json.get('data').get('media').get('isPremium') is True:
            self.report_warning("requires a premium account" % video_id, video_id)

        return {
            '_type': 'url_transparent',
            'url': BRIGHTCOVE_URL_TEMPLATE % (brightcove_user_id, brightcove_video_id),
            'ie_key': 'BrightcoveNew',
            'id': video_id,
            'title': metadata_json.get('data').get('media').get('title'),
            'like_count': metadata_json.get('data').get('media').get('totalUpvotes'),
            'view_count': metadata_json.get('data').get('media').get('totalViews'),
            'tags': metadata_json.get('data').get('media').get('tags'),
            'release_timestamp': parse_iso8601(metadata_json.get('data').get('media').get('publishedTime'))
        }
