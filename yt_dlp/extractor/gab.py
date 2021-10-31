# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    unified_timestamp,
    parse_duration,
    parse_codecs,
    parse_bitrate,
    int_or_none,
    str_to_int,
    clean_html,
)


class GabTVIE(InfoExtractor):
    _VALID_URL = r'(?:https?://)tv.gab.com/channel/[^/]+/view/(?P<id>[a-z0-9-]+)'
    _TESTS = [{
        'url': 'https://tv.gab.com/channel/wurzelroot/view/why-was-america-in-afghanistan-61217eacea5665de450d0488',
        'info_dict': {
            'id': '61217eacea5665de450d0488',
            'ext': 'mp4',
            'title': 'WHY WAS AMERICA IN AFGHANISTAN - AMERICA FIRST AGAINST AMERICAN OLIGARCHY',
            'description': None,
            'uploader': 'Wurzelroot',
            'uploader_id': '608fb0a85738fd1974984f7d',
            'thumbnail': 'https://tv.gab.com/image/61217eacea5665de450d0488',
        }
    }]

    def _real_extract(self, url):
        id = self._match_id(url).split('-')[-1]
        webpage = self._download_webpage(url, id)
        channel_id = self._search_regex(r'data-channel-id=\"(?P<channel_id>[^\"]+)', webpage, 'channel_id')
        channel_name = self._search_regex(r'data-channel-name=\"(?P<channel_id>[^\"]+)', webpage, 'channel_name')
        title = self._search_regex(r'data-episode-title=\"(?P<channel_id>[^\"]+)', webpage, 'title')
        view_key = self._search_regex(r'data-view-key=\"(?P<channel_id>[^\"]+)', webpage, 'view_key')
        description = clean_html(
            self._html_search_regex(self._meta_regex('description'), webpage, 'description', group='content')) or None
        available_resolutions = re.findall(r'<a\ data-episode-id=\"%s\"\ data-resolution=\"(?P<resolution>[^\"]+)' % id,
                                           webpage)

        formats = []
        for resolution in available_resolutions:
            frmt = {
                'url': f'https://tv.gab.com/media/{id}?viewKey={view_key}&r={resolution}',
                'format_id': resolution,
                'vcodec': 'h264',
                'acodec': 'aac',
                'ext': 'mp4'
            }
            if 'audio-' in resolution:
                frmt['abr'] = str_to_int(resolution.replace('audio-', ''))
                frmt['height'] = 144
                frmt['quality'] = -10
            else:
                frmt['height'] = str_to_int(resolution.replace('p', ''))
            formats.append(frmt)
        self._sort_formats(formats)

        return {
            'id': id,
            'title': title,
            'formats': formats,
            'description': description,
            'uploader': channel_name,
            'uploader_id': channel_id,
            'thumbnail': f'https://tv.gab.com/image/{id}',
        }


class GabIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?gab\.com/[^/]+/posts/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://gab.com/SomeBitchIKnow/posts/107163961867310434',
        'md5': '8ca34fb00f1e1033b5c5988d79ec531d',
        'info_dict': {
            'id': '107163961867310434-0',
            'ext': 'mp4',
            'title': "L on Gab: ''",
            'uploader_id': '946600',
            'uploader': 'SomeBitchIKnow',
            'description': 'md5:204055fafd5e1a519f5d6db953567ca3',
            'timestamp': 1635192289,
            'upload_date': '20211025',
        }
    }, {
        'url': 'https://gab.com/TheLonelyProud/posts/107045884469287653',
        'md5': 'f9cefcfdff6418e392611a828d47839d',
        'info_dict': {
            'id': '107045884469287653-0',
            'ext': 'mp4',
            'title': "Jody Sadowski on Gab: ''",
            'uploader_id': '1390705',
            'timestamp': 1633390571,
            'upload_date': '20211004',
            'uploader': 'TheLonelyProud',
        }
    }]

    def _real_extract(self, url):
        post_id = self._match_id(url)
        webpage = self._download_webpage(url, post_id, note='Downloading guest tokens',
                                         errnote='Failed to download guest tokens')

        title = self._html_search_meta(('og:title', 'title'), webpage)

        csfr_token = self._html_search_meta('csrf-token', webpage)

        json_data = self._download_json(f'https://gab.com/api/v1/statuses/{post_id}', post_id,
                                        headers={'X-CSRF-Token': csfr_token})

        timestamp = unified_timestamp(json_data.get('created_at'))
        description = clean_html(json_data.get('content'))
        like_count = json_data.get('favourites_count')
        comment_count = json_data.get('replies_count')
        repost_count = json_data.get('reblogs_count')

        media_list = json_data['media_attachments']
        author = json_data.get('account') or {}
        uploader = author.get('username')
        uploader_id = author.get('id')
        uploader_url = author.get('url')

        entities = []
        for p, media in enumerate(media_list):
            if media['type'] not in ('video', 'gifv'):
                continue
            metadata = media['meta']
            formats = []
            duration = metadata.get('duration') or parse_duration(metadata.get('length'))
            acodec = parse_codecs(metadata.get('audio_encode')).get('acodec')
            abr = parse_bitrate(metadata.get('audio_bitrate'))
            fps = metadata.get('fps')
            for i, format in enumerate([metadata.get('original') or {}, metadata.get('playable') or {}]):
                if i == 0:
                    url = media.get('url')
                elif i == 1:
                    url = media.get('source_mp4')
                if not url:
                    continue
                formats.append({
                    'url': url,
                    'width': format.get('width'),
                    'height': format.get('height'),
                    'tbr': int_or_none(format.get('bitrate'), scale=1000),
                    'fps': fps,
                    'abr': abr,
                    'acodec': acodec,
                })
            entities.append({
                'id': f'{post_id}-{p}',
                'title': title,
                'timestamp': timestamp,
                'formats': formats,
                'description': description,
                'duration': duration,
                'like_count': like_count,
                'comment_count': comment_count,
                'repost_count': repost_count,
                'uploader': uploader,
                'uploader_id': uploader_id,
                'uploader_url': uploader_url,
            })

        if len(entities) > 1:
            return self.playlist_result(entities, post_id)

        return entities[0]
