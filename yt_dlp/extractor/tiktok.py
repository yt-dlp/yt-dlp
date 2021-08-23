# coding: utf-8
from __future__ import unicode_literals
from datetime import datetime

import itertools

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


class TikTokUserIE(InfoExtractor):
    IE_NAME = 'tiktok:user'
    _VALID_URL = r'(?!.*/video/)https?://www\.tiktok\.com/@(?P<id>[\w\._]+)'
    _TESTS = [{
        'url': 'https://www.tiktok.com/@corgibobaa?lang=en',
        'playlist_mincount': 45,
        'info_dict': {
            'id': '6935371178089399301',
        },
        'skip': 'Cookies (not necessarily logged in) are needed.'
    }, {
        'url': 'https://www.tiktok.com/@meme',
        'playlist_mincount': 593,
        'info_dict': {
            'id': '79005827461758976',
        },
        'skip': 'Cookies (not necessarily logged in) are needed.'
    }]

    def _entries(self, url, id):
        webpage = self._download_webpage(url, id)
        user_id = self._search_regex(r'\"id\":\"(?P<userid>\d+)', webpage, id, default=None)
        if not user_id:
            raise ExtractorError('Cookies (not necessarily logged in) are needed.', expected=True)
        secuid = self._search_regex(r'\"secUid\":\"(?P<secUid>[^\"]+)', webpage, id)
        verifyfp_cookie = self._get_cookies('https://www.tiktok.com').get('s_v_web_id')
        if not verifyfp_cookie:
            raise ExtractorError('Improper cookies (missing s_v_web_id).', expected=True)
        api_url = f'https://m.tiktok.com/api/post/item_list/?aid=1988&cookie_enabled=true&count=30&verifyFp={verifyfp_cookie.value}&secUid={secuid}&cursor='
        has_more = True
        cursor = '0'
        for page in itertools.count():
            data_json = self._download_json(api_url + cursor, user_id, note='Downloading Page %d' % page)
            cursor = data_json['cursor']
            has_more = data_json['hasMore']
            videos = data_json.get('itemList', [])
            for video in videos:
                video_id = video['id']
                video_url = f'https://www.tiktok.com/@{id}/video/{video_id}'
                thumbnail = try_get(video, lambda x: x['video']['originCover'])
                height = try_get(video, lambda x: x['video']['height'], int)
                width = try_get(video, lambda x: x['video']['width'], int)
                resolution = '%sx%s' % (width, height)
                timestamp = video.get('createTime')
                download_url = ''
                if not download_url:
                    download_url = try_get(video, lambda x: x['video']['playAddr'])
                if not download_url:
                    download_url = try_get(video, lambda x: x['video']['downloadAddr'])
                formats = [{
                    'url': download_url,
                    'ext': 'mp4',
                    'height': height,
                    'width': width
                }]
                tracker = self._get_cookies('https://www.tiktok.com').get('tt_webid').value
                yield {
                    'url': video_url,
                    'ie_key': TikTokIE.ie_key(),
                    'comment_count': int_or_none(try_get(video, lambda x: x['stats']['commentCount'], int)),
                    'duration': try_get(video, lambda x: x['video']['duration'], int),
                    'height': height,
                    'id': video_id,
                    'like_count': int_or_none(try_get(video, lambda x: x['stats']['diggCount'], int)),
                    'repost_count': int_or_none(try_get(video, lambda x: x['stats']['shareCount'], int)),
                    'thumbnail': thumbnail,
                    'timestamp': timestamp,
                    'width': width,
                    'title': str_or_none(video.get('desc')),
                    'creator': str_or_none(try_get(video, lambda x: x['author']['nickname'])),
                    'uploader': str_or_none(try_get(video, lambda x: x['author']['uniqueId'])),
                    'uploader_id': str_or_none(try_get(video, lambda x: x['author']['id'])),
                    'uploader_url': 'https://www.tiktok.com/@' + id,
                    'thumbnails': [{'url': thumbnail, 'height': height, 'width': width, 'id': '0', 'resolution': resolution}],
                    'upload_date': datetime.fromtimestamp(timestamp).strftime('%Y%m%d'),
                    'webpage_url': video_url,
                    'description': str_or_none(video.get('desc')),
                    'ext': 'mp4',
                    'formats': formats,
                    'http_headers': {
                        'Referer': video_url,
                        'Cookie': 'tt_webid=%s; tt_webid_v2=%s' % (tracker, tracker),
                    }
                }
            if not has_more:
                break

    def _real_extract(self, url):
        id = self._match_id(url)
        return {
            '_type': 'playlist',
            'entries': self._entries(url, id),
            'title': id,
        }
