# coding: utf-8
from __future__ import unicode_literals


from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    int_or_none,
    str_or_none,
)


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
            'title': title,
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
        channel_id, broadcast_id = self._match_valid_url(url).groups()
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
