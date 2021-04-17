# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    int_or_none,
    js_to_json,
    str_or_none,
)


class LineTVIE(InfoExtractor):
    _VALID_URL = r'https?://tv\.line\.me/v/(?P<id>\d+)_[^/]+-(?P<segment>ep\d+-\d+)'

    _TESTS = [{
        'url': 'https://tv.line.me/v/793123_goodbye-mrblack-ep1-1/list/69246',
        'info_dict': {
            'id': '793123_ep1-1',
            'ext': 'mp4',
            'title': 'Goodbye Mr.Black | EP.1-1',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 998.509,
            'view_count': int,
        },
    }, {
        'url': 'https://tv.line.me/v/2587507_%E6%B4%BE%E9%81%A3%E5%A5%B3%E9%86%ABx-ep1-02/list/185245',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        series_id, segment = re.match(self._VALID_URL, url).groups()
        video_id = '%s_%s' % (series_id, segment)

        webpage = self._download_webpage(url, video_id)

        player_params = self._parse_json(self._search_regex(
            r'naver\.WebPlayer\(({[^}]+})\)', webpage, 'player parameters'),
            video_id, transform_source=js_to_json)

        video_info = self._download_json(
            'https://global-nvapis.line.me/linetv/rmcnmv/vod_play_videoInfo.json',
            video_id, query={
                'videoId': player_params['videoId'],
                'key': player_params['key'],
            })

        stream = video_info['streams'][0]
        extra_query = '?__gda__=' + stream['key']['value']
        formats = self._extract_m3u8_formats(
            stream['source'] + extra_query, video_id, ext='mp4',
            entry_protocol='m3u8_native', m3u8_id='hls')

        for a_format in formats:
            a_format['url'] += extra_query

        duration = None
        for video in video_info.get('videos', {}).get('list', []):
            encoding_option = video.get('encodingOption', {})
            abr = video['bitrate']['audio']
            vbr = video['bitrate']['video']
            tbr = abr + vbr
            formats.append({
                'url': video['source'],
                'format_id': 'http-%d' % int(tbr),
                'height': encoding_option.get('height'),
                'width': encoding_option.get('width'),
                'abr': abr,
                'vbr': vbr,
                'filesize': video.get('size'),
            })
            if video.get('duration') and duration is None:
                duration = video['duration']

        self._sort_formats(formats)

        if formats and not formats[0].get('width'):
            formats[0]['vcodec'] = 'none'

        title = self._og_search_title(webpage)

        # like_count requires an additional API request https://tv.line.me/api/likeit/getCount

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'extra_param_to_segment_url': extra_query[1:],
            'duration': duration,
            'thumbnails': [{'url': thumbnail['source']}
                           for thumbnail in video_info.get('thumbnails', {}).get('list', [])],
            'view_count': video_info.get('meta', {}).get('count'),
        }


class LineLiveBaseIE(InfoExtractor):
    _API_BASE_URL = 'https://live-api.line-apps.com/web/v4.0/channel/'

    def _parse_broadcast_item(self, item):
        broadcast_id = compat_str(item['id'])
        title = item['title']
        is_live = item.get('isBroadcastingNow')

        thumbnails = []
        for thumbnail_id, thumbnail_url in (item.get('thumbnailURLs') or {}).items():
            if not thumbnail_url:
                continue
            thumbnails.append({
                'id': thumbnail_id,
                'url': thumbnail_url,
            })

        channel = item.get('channel') or {}
        channel_id = str_or_none(channel.get('id'))

        return {
            'id': broadcast_id,
            'title': self._live_title(title) if is_live else title,
            'thumbnails': thumbnails,
            'timestamp': int_or_none(item.get('createdAt')),
            'channel': channel.get('name'),
            'channel_id': channel_id,
            'channel_url': 'https://live.line.me/channels/' + channel_id if channel_id else None,
            'duration': int_or_none(item.get('archiveDuration')),
            'view_count': int_or_none(item.get('viewerCount')),
            'comment_count': int_or_none(item.get('chatCount')),
            'is_live': is_live,
        }


class LineLiveIE(LineLiveBaseIE):
    _VALID_URL = r'https?://live\.line\.me/channels/(?P<channel_id>\d+)/broadcast/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://live.line.me/channels/4867368/broadcast/16331360',
        'md5': 'bc931f26bf1d4f971e3b0982b3fab4a3',
        'info_dict': {
            'id': '16331360',
            'title': '振りコピ講座😙😙😙',
            'ext': 'mp4',
            'timestamp': 1617095132,
            'upload_date': '20210330',
            'channel': '白川ゆめか',
            'channel_id': '4867368',
            'view_count': int,
            'comment_count': int,
            'is_live': False,
        }
    }, {
        # archiveStatus == 'DELETED'
        'url': 'https://live.line.me/channels/4778159/broadcast/16378488',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        channel_id, broadcast_id = re.match(self._VALID_URL, url).groups()
        broadcast = self._download_json(
            self._API_BASE_URL + '%s/broadcast/%s' % (channel_id, broadcast_id),
            broadcast_id)
        item = broadcast['item']
        info = self._parse_broadcast_item(item)
        protocol = 'm3u8' if info['is_live'] else 'm3u8_native'
        formats = []
        for k, v in (broadcast.get(('live' if info['is_live'] else 'archived') + 'HLSURLs') or {}).items():
            if not v:
                continue
            if k == 'abr':
                formats.extend(self._extract_m3u8_formats(
                    v, broadcast_id, 'mp4', protocol,
                    m3u8_id='hls', fatal=False))
                continue
            f = {
                'ext': 'mp4',
                'format_id': 'hls-' + k,
                'protocol': protocol,
                'url': v,
            }
            if not k.isdigit():
                f['vcodec'] = 'none'
            formats.append(f)
        if not formats:
            archive_status = item.get('archiveStatus')
            if archive_status != 'ARCHIVED':
                self.raise_no_formats('this video has been ' + archive_status.lower(), expected=True)
        self._sort_formats(formats)
        info['formats'] = formats
        return info


class LineLiveChannelIE(LineLiveBaseIE):
    _VALID_URL = r'https?://live\.line\.me/channels/(?P<id>\d+)(?!/broadcast/\d+)(?:[/?&#]|$)'
    _TEST = {
        'url': 'https://live.line.me/channels/5893542',
        'info_dict': {
            'id': '5893542',
            'title': 'いくらちゃん',
            'description': 'md5:c3a4af801f43b2fac0b02294976580be',
        },
        'playlist_mincount': 29
    }

    def _archived_broadcasts_entries(self, archived_broadcasts, channel_id):
        while True:
            for row in (archived_broadcasts.get('rows') or []):
                share_url = str_or_none(row.get('shareURL'))
                if not share_url:
                    continue
                info = self._parse_broadcast_item(row)
                info.update({
                    '_type': 'url',
                    'url': share_url,
                    'ie_key': LineLiveIE.ie_key(),
                })
                yield info
            if not archived_broadcasts.get('hasNextPage'):
                return
            archived_broadcasts = self._download_json(
                self._API_BASE_URL + channel_id + '/archived_broadcasts',
                channel_id, query={
                    'lastId': info['id'],
                })

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        channel = self._download_json(self._API_BASE_URL + channel_id, channel_id)
        return self.playlist_result(
            self._archived_broadcasts_entries(channel.get('archivedBroadcasts') or {}, channel_id),
            channel_id, channel.get('title'), channel.get('information'))
