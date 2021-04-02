# coding: utf-8
from __future__ import unicode_literals
from datetime import datetime

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    str_or_none,
    try_get
)


class TikTokBaseIE(InfoExtractor):
    def _extract_aweme(self, props_data, webpage, url):
        video_data = try_get(props_data, lambda x: x['pageProps'], expected_type=dict)
        video_info = try_get(
            video_data, lambda x: x['itemInfo']['itemStruct'], dict)
        author_info = try_get(
            video_data, lambda x: x['itemInfo']['itemStruct']['author'], dict) or {}
        share_info = try_get(video_data, lambda x: x['itemInfo']['shareMeta'], dict) or {}

        unique_id = str_or_none(author_info.get('uniqueId'))
        timestamp = try_get(video_info, lambda x: int(x['createTime']), int)
        date = datetime.fromtimestamp(timestamp).strftime('%Y%m%d')

        height = try_get(video_info, lambda x: x['video']['height'], int)
        width = try_get(video_info, lambda x: x['video']['width'], int)
        thumbnails = []
        thumbnails.append({
            'url': video_info.get('thumbnail') or self._og_search_thumbnail(webpage),
            'width': width,
            'height': height
        })

        url = ''
        if not url:
            url = try_get(video_info, lambda x: x['video']['playAddr'])
        if not url:
            url = try_get(video_info, lambda x: x['video']['downloadAddr'])
        formats = []
        formats.append({
            'url': url,
            'ext': 'mp4',
            'height': height,
            'width': width
        })

        tracker = try_get(props_data, lambda x: x['initialProps']['$wid'])
        return {
            'comment_count': int_or_none(video_info.get('commentCount')),
            'duration': try_get(video_info, lambda x: x['video']['videoMeta']['duration'], int),
            'height': height,
            'id': str_or_none(video_info.get('id')),
            'like_count': int_or_none(video_info.get('diggCount')),
            'repost_count': int_or_none(video_info.get('shareCount')),
            'thumbnail': try_get(video_info, lambda x: x['covers'][0]),
            'timestamp': timestamp,
            'width': width,
            'title': str_or_none(share_info.get('title')) or self._og_search_title(webpage),
            'creator': str_or_none(author_info.get('nickName')),
            'uploader': unique_id,
            'uploader_id': str_or_none(author_info.get('userId')),
            'uploader_url': 'https://www.tiktok.com/@' + unique_id,
            'thumbnails': thumbnails,
            'upload_date': date,
            'webpage_url': self._og_search_url(webpage),
            'description': str_or_none(video_info.get('text')) or str_or_none(share_info.get('desc')),
            'ext': 'mp4',
            'formats': formats,
            'http_headers': {
                'Referer': url,
                'Cookie': 'tt_webid=%s; tt_webid_v2=%s' % (tracker, tracker),
            }
        }


class TikTokIE(TikTokBaseIE):
    _VALID_URL = r'https?://www\.tiktok\.com/@[\w\._]+/video/(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://www.tiktok.com/@leenabhushan/video/6748451240264420610',
        'md5': '34a7543afd5a151b0840ba6736fb633b',
        'info_dict': {
            'comment_count': int,
            'creator': 'facestoriesbyleenabh',
            'description': 'md5:a9f6c0c44a1ff2249cae610372d0ae95',
            'duration': 13,
            'ext': 'mp4',
            'formats': list,
            'height': 1280,
            'id': '6748451240264420610',
            'like_count': int,
            'repost_count': int,
            'thumbnail': r're:^https?://[\w\/\.\-]+(~[\w\-]+\.image)?',
            'thumbnails': list,
            'timestamp': 1571246252,
            'title': 'facestoriesbyleenabh on TikTok',
            'upload_date': '20191016',
            'uploader': 'leenabhushan',
            'uploader_id': '6691488002098119685',
            'uploader_url': r're:https://www.tiktok.com/@leenabhushan',
            'webpage_url': r're:https://www.tiktok.com/@leenabhushan/(video/)?6748451240264420610',
            'width': 720,
        }
    }, {
        'url': 'https://www.tiktok.com/@patroxofficial/video/6742501081818877190?langCountry=en',
        'md5': '06b9800d47d5fe51a19e322dd86e61c9',
        'info_dict': {
            'comment_count': int,
            'creator': 'patroX',
            'description': 'md5:5e2a23877420bb85ce6521dbee39ba94',
            'duration': 27,
            'ext': 'mp4',
            'formats': list,
            'height': 960,
            'id': '6742501081818877190',
            'like_count': int,
            'repost_count': int,
            'thumbnail': r're:^https?://[\w\/\.\-]+(~[\w\-]+\.image)?',
            'thumbnails': list,
            'timestamp': 1569860870,
            'title': 'patroX on TikTok',
            'upload_date': '20190930',
            'uploader': 'patroxofficial',
            'uploader_id': '18702747',
            'uploader_url': r're:https://www.tiktok.com/@patroxofficial',
            'webpage_url': r're:https://www.tiktok.com/@patroxofficial/(video/)?6742501081818877190',
            'width': 540,
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # If we only call once, we get a 403 when downlaoding the video.
        self._download_webpage(url, video_id)
        webpage = self._download_webpage(url, video_id, note='Downloading video webpage')
        json_string = self._search_regex(
            r'id=\"__NEXT_DATA__\"\s+type=\"application\/json\"\s*[^>]+>\s*(?P<json_string_ld>[^<]+)',
            webpage, 'json_string', group='json_string_ld')
        json_data = self._parse_json(json_string, video_id)
        props_data = try_get(json_data, lambda x: x['props'], expected_type=dict)

        # Chech statusCode for success
        status = props_data.get('pageProps').get('statusCode')
        if status == 0:
            return self._extract_aweme(props_data, webpage, url)
        elif status == 10216:
            raise ExtractorError('This video is private', expected=True)

        raise ExtractorError('Video not available', video_id=video_id)
