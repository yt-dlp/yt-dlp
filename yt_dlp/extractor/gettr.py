# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    bool_or_none,
    ExtractorError,
    dict_get,
    float_or_none,
    int_or_none,
    remove_end,
    str_or_none,
    try_get,
    url_or_none,
    urljoin,
)


class GettrBaseIE(InfoExtractor):
    _BASE_REGEX = r'https?://(www\.)?gettr\.com/'
    _MEDIA_BASE_URL = 'https://media.gettr.com/'

    def _call_api(self, path, video_id, *args, **kwargs):
        return self._download_json(urljoin('https://api.gettr.com/u/', path), video_id, *args, **kwargs)['result']


class GettrIE(GettrBaseIE):
    _VALID_URL = GettrBaseIE._BASE_REGEX + r'post/(?P<id>[a-z0-9]+)'

    _TESTS = [{
        'url': 'https://www.gettr.com/post/pcf6uv838f',
        'info_dict': {
            'id': 'pcf6uv838f',
            'title': 'md5:9086a646bbd06c41c4fe8e52b3c93454',
            'description': 'md5:be0577f1e4caadc06de4a002da2bf287',
            'ext': 'mp4',
            'uploader': 'EpochTV',
            'uploader_id': 'epochtv',
            'thumbnail': r're:^https?://.+/out\.jpg',
            'timestamp': 1632782451058,
            'duration': 58.5585,
        }
    }, {
        'url': 'https://gettr.com/post/p4iahp',
        'info_dict': {
            'id': 'p4iahp',
            'title': 'md5:b03c07883db6fbc1aab88877a6c3b149',
            'description': 'md5:741b7419d991c403196ed2ea7749a39d',
            'ext': 'mp4',
            'uploader': 'Neues Forum Freiheit',
            'uploader_id': 'nf_freiheit',
            'thumbnail': r're:^https?://.+/out\.jpg',
            'timestamp': 1626594455017,
            'duration': 23,
        }
    }]

    def _real_extract(self, url):
        post_id = self._match_id(url)
        webpage = self._download_webpage(url, post_id)

        api_data = self._call_api('post/%s?incl="poststats|userinfo"' % post_id, post_id)

        post_data = api_data.get('data')
        user_data = try_get(api_data, lambda x: x['aux']['uinf'][post_data['uid']]) or {}

        if post_data.get('nfound'):
            raise ExtractorError(post_data.get('txt'), expected=True)

        title = description = str_or_none(
            post_data.get('txt') or self._og_search_description(webpage))

        uploader = str_or_none(
            user_data.get('nickname')
            or remove_end(self._og_search_title(webpage), ' on GETTR'))
        if uploader:
            title = '%s - %s' % (uploader, title)

        if not dict_get(post_data, ['vid', 'ovid']):
            raise ExtractorError('There\'s no video in this post.')

        vid = post_data.get('vid')
        ovid = post_data.get('ovid')

        formats = self._extract_m3u8_formats(
            urljoin(self._MEDIA_BASE_URL, vid), post_id, 'mp4',
            entry_protocol='m3u8_native', m3u8_id='hls') if vid else []

        if ovid:
            formats.append({
                'url': urljoin(self._MEDIA_BASE_URL, ovid),
                'format_id': 'ovid',
                'ext': 'mp4',
                'width': int_or_none(post_data.get('vid_wid')),
                'height': int_or_none(post_data.get('vid_hgt')),
                'source_preference': 1,
                'quality': 1,
            })

        self._sort_formats(formats)

        return {
            'id': post_id,
            'title': title,
            'description': description,
            'thumbnail': url_or_none(
                urljoin(self._MEDIA_BASE_URL, post_data.get('main'))
                or self._og_search_thumbnail(webpage)),
            'timestamp': int_or_none(post_data.get('cdate')),
            'uploader_id': str_or_none(
                dict_get(user_data, ['_id', 'username'])
                or post_data.get('uid')),
            'uploader': uploader,
            'formats': formats,
            'duration': float_or_none(post_data.get('vid_dur')),
            'tags': post_data.get('htgs'),
        }


class GettrStreamingIE(GettrBaseIE):
    _VALID_URL = GettrBaseIE._BASE_REGEX + r'streaming/(?P<id>[a-z0-9]+)'

    _TESTS = [{
        'url': 'https://gettr.com/streaming/psoiulc122',
        'info_dict': {
            'id': 'psoiulc122',
            'ext': 'mp4',
            'description': 'md5:56bca4b8f48f1743d9fd03d49c723017',
            'view_count': int,
            'uploader': 'Corona Investigative Committee',
            'uploader_id': 'coronacommittee',
            'duration': 5180.184,
            'thumbnail': r're:^https?://.+',
            'title': 'Day 1: Opening Session of the Grand Jury Proceeding',
            'timestamp': 1644080997.164,
            'upload_date': '20220205',
        }
    }, {
        'url': 'https://gettr.com/streaming/psfmeefcc1',
        'info_dict': {
            'id': 'psfmeefcc1',
            'ext': 'mp4',
            'title': 'Session 90: "The Virus Of Power"',
            'view_count': int,
            'uploader_id': 'coronacommittee',
            'description': 'md5:98986acdf656aa836bf36f9c9704c65b',
            'uploader': 'Corona Investigative Committee',
            'thumbnail': r're:^https?://.+',
            'duration': 21872.507,
            'timestamp': 1643976662.858,
            'upload_date': '20220204',
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_info = self._call_api('live/join/%s' % video_id, video_id, data={})

        live_info = video_info['broadcast']
        live_url = url_or_none(live_info.get('url'))

        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            live_url, video_id, ext='mp4',
            entry_protocol='m3u8_native', m3u8_id='hls', fatal=False) if live_url else ([], {})

        thumbnails = [{
            'url': urljoin(self._MEDIA_BASE_URL, thumbnail),
        } for thumbnail in try_get(video_info, lambda x: x['postData']['imgs']) or []]

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': try_get(video_info, lambda x: x['postData']['ttl']),
            'description': try_get(video_info, lambda x: x['postData']['dsc']),
            'formats': formats,
            'subtitles': subtitles,
            'thumbnails': thumbnails,
            'uploader': try_get(video_info, lambda x: x['liveHostInfo']['nickname']),
            'uploader_id': try_get(video_info, lambda x: x['liveHostInfo']['_id']),
            'view_count': int_or_none(live_info.get('viewsCount')),
            'timestamp': float_or_none(live_info.get('startAt'), scale=1000),
            'duration': float_or_none(live_info.get('duration'), scale=1000),
            'is_live': bool_or_none(live_info.get('isLive')),
        }
