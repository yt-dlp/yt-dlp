# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
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


class GettrIE(InfoExtractor):
    _VALID_URL = r'https?://(www\.)?gettr\.com/post/(?P<id>[a-z0-9]+)'
    _MEDIA_BASE_URL = 'https://media.gettr.com/'

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

        api_data = self._download_json(
            'https://api.gettr.com/u/post/%s?incl="poststats|userinfo"' % post_id, post_id)

        post_data = try_get(api_data, lambda x: x['result']['data'])
        user_data = try_get(api_data, lambda x: x['result']['aux']['uinf'][post_data['uid']]) or {}

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
