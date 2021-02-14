# coding: utf-8
from __future__ import unicode_literals

import json
import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    determine_ext,
    float_or_none,
    int_or_none,
    try_get,
    unified_timestamp,
    url_or_none,
)


class PinterestBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://(?:[^/]+\.)?pinterest\.(?:com|fr|de|ch|jp|cl|ca|it|co\.uk|nz|ru|com\.au|at|pt|co\.kr|es|com\.mx|dk|ph|th|com\.uy|co|nl|info|kr|ie|vn|com\.vn|ec|mx|in|pe|co\.at|hu|co\.in|co\.nz|id|com\.ec|com\.py|tw|be|uk|com\.bo|com\.pe)'

    def _call_api(self, resource, video_id, options):
        return self._download_json(
            'https://www.pinterest.com/resource/%sResource/get/' % resource,
            video_id, 'Download %s JSON metadata' % resource, query={
                'data': json.dumps({'options': options})
            })['resource_response']

    def _extract_video(self, data, extract_formats=True):
        video_id = data['id']

        title = (data.get('title') or data.get('grid_title') or video_id).strip()

        formats = []
        duration = None
        if extract_formats:
            for format_id, format_dict in data['videos']['video_list'].items():
                if not isinstance(format_dict, dict):
                    continue
                format_url = url_or_none(format_dict.get('url'))
                if not format_url:
                    continue
                duration = float_or_none(format_dict.get('duration'), scale=1000)
                ext = determine_ext(format_url)
                if 'hls' in format_id.lower() or ext == 'm3u8':
                    formats.extend(self._extract_m3u8_formats(
                        format_url, video_id, 'mp4', entry_protocol='m3u8_native',
                        m3u8_id=format_id, fatal=False))
                else:
                    formats.append({
                        'url': format_url,
                        'format_id': format_id,
                        'width': int_or_none(format_dict.get('width')),
                        'height': int_or_none(format_dict.get('height')),
                        'duration': duration,
                    })
            self._sort_formats(
                formats, field_preference=('height', 'width', 'tbr', 'format_id'))

        description = data.get('description') or data.get('description_html') or data.get('seo_description')
        timestamp = unified_timestamp(data.get('created_at'))

        def _u(field):
            return try_get(data, lambda x: x['closeup_attribution'][field], compat_str)

        uploader = _u('full_name')
        uploader_id = _u('id')

        repost_count = int_or_none(data.get('repin_count'))
        comment_count = int_or_none(data.get('comment_count'))
        categories = try_get(data, lambda x: x['pin_join']['visual_annotation'], list)
        tags = data.get('hashtags')

        thumbnails = []
        images = data.get('images')
        if isinstance(images, dict):
            for thumbnail_id, thumbnail in images.items():
                if not isinstance(thumbnail, dict):
                    continue
                thumbnail_url = url_or_none(thumbnail.get('url'))
                if not thumbnail_url:
                    continue
                thumbnails.append({
                    'url': thumbnail_url,
                    'width': int_or_none(thumbnail.get('width')),
                    'height': int_or_none(thumbnail.get('height')),
                })

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'duration': duration,
            'timestamp': timestamp,
            'thumbnails': thumbnails,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'repost_count': repost_count,
            'comment_count': comment_count,
            'categories': categories,
            'tags': tags,
            'formats': formats,
            'extractor_key': PinterestIE.ie_key(),
        }


class PinterestIE(PinterestBaseIE):
    _VALID_URL = r'%s/pin/(?P<id>\d+)' % PinterestBaseIE._VALID_URL_BASE
    _TESTS = [{
        'url': 'https://www.pinterest.com/pin/664281013778109217/',
        'md5': '6550c2af85d6d9f3fe3b88954d1577fc',
        'info_dict': {
            'id': '664281013778109217',
            'ext': 'mp4',
            'title': 'Origami',
            'description': 'md5:b9d90ddf7848e897882de9e73344f7dd',
            'duration': 57.7,
            'timestamp': 1593073622,
            'upload_date': '20200625',
            'uploader': 'Love origami -I am Dafei',
            'uploader_id': '586523688879454212',
            'repost_count': 50,
            'comment_count': 0,
            'categories': list,
            'tags': list,
        },
    }, {
        'url': 'https://co.pinterest.com/pin/824721750502199491/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        data = self._call_api(
            'Pin', video_id, {
                'field_set_key': 'unauth_react_main_pin',
                'id': video_id,
            })['data']
        return self._extract_video(data)


class PinterestCollectionIE(PinterestBaseIE):
    _VALID_URL = r'%s/(?P<username>[^/]+)/(?P<id>[^/?#&]+)' % PinterestBaseIE._VALID_URL_BASE
    _TESTS = [{
        'url': 'https://www.pinterest.ca/mashal0407/cool-diys/',
        'info_dict': {
            'id': '585890301462791043',
            'title': 'cool diys',
        },
        'playlist_count': 8,
    }, {
        'url': 'https://www.pinterest.ca/fudohub/videos/',
        'info_dict': {
            'id': '682858430939307450',
            'title': 'VIDEOS',
        },
        'playlist_mincount': 365,
        'skip': 'Test with extract_formats=False',
    }]

    @classmethod
    def suitable(cls, url):
        return False if PinterestIE.suitable(url) else super(
            PinterestCollectionIE, cls).suitable(url)

    def _real_extract(self, url):
        username, slug = re.match(self._VALID_URL, url).groups()
        board = self._call_api(
            'Board', slug, {
                'slug': slug,
                'username': username
            })['data']
        board_id = board['id']
        options = {
            'board_id': board_id,
            'page_size': 250,
        }
        bookmark = None
        entries = []
        while True:
            if bookmark:
                options['bookmarks'] = [bookmark]
            board_feed = self._call_api('BoardFeed', board_id, options)
            for item in (board_feed.get('data') or []):
                if not isinstance(item, dict) or item.get('type') != 'pin':
                    continue
                video_id = item.get('id')
                if video_id:
                    # Some pins may not be available anonymously via pin URL
                    # video = self._extract_video(item, extract_formats=False)
                    # video.update({
                    #     '_type': 'url_transparent',
                    #     'url': 'https://www.pinterest.com/pin/%s/' % video_id,
                    # })
                    # entries.append(video)
                    entries.append(self._extract_video(item))
            bookmark = board_feed.get('bookmark')
            if not bookmark:
                break
        return self.playlist_result(
            entries, playlist_id=board_id, playlist_title=board.get('name'))
