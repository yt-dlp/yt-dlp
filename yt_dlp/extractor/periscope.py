# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
    unescapeHTML,
)


class PeriscopeBaseIE(InfoExtractor):
    _M3U8_HEADERS = {
        'Referer': 'https://www.periscope.tv/'
    }

    def _call_api(self, method, query, item_id):
        return self._download_json(
            'https://api.periscope.tv/api/v2/%s' % method,
            item_id, query=query)

    def _parse_broadcast_data(self, broadcast, video_id):
        title = broadcast.get('status') or 'Periscope Broadcast'
        uploader = broadcast.get('user_display_name') or broadcast.get('username')
        title = '%s - %s' % (uploader, title) if uploader else title
        is_live = broadcast.get('state').lower() == 'running'

        thumbnails = [{
            'url': broadcast[image],
        } for image in ('image_url', 'image_url_small') if broadcast.get(image)]

        return {
            'id': broadcast.get('id') or video_id,
            'title': self._live_title(title) if is_live else title,
            'timestamp': parse_iso8601(broadcast.get('created_at')),
            'uploader': uploader,
            'uploader_id': broadcast.get('user_id') or broadcast.get('username'),
            'thumbnails': thumbnails,
            'view_count': int_or_none(broadcast.get('total_watched')),
            'tags': broadcast.get('tags'),
            'is_live': is_live,
        }

    @staticmethod
    def _extract_common_format_info(broadcast):
        return broadcast.get('state').lower(), int_or_none(broadcast.get('width')), int_or_none(broadcast.get('height'))

    @staticmethod
    def _add_width_and_height(f, width, height):
        for key, val in (('width', width), ('height', height)):
            if not f.get(key):
                f[key] = val

    def _extract_pscp_m3u8_formats(self, m3u8_url, video_id, format_id, state, width, height, fatal=True):
        m3u8_formats = self._extract_m3u8_formats(
            m3u8_url, video_id, 'mp4',
            entry_protocol='m3u8_native'
            if state in ('ended', 'timed_out') else 'm3u8',
            m3u8_id=format_id, fatal=fatal, headers=self._M3U8_HEADERS)
        if len(m3u8_formats) == 1:
            self._add_width_and_height(m3u8_formats[0], width, height)
        for f in m3u8_formats:
            f.setdefault('http_headers', {}).update(self._M3U8_HEADERS)
        return m3u8_formats


class PeriscopeIE(PeriscopeBaseIE):
    IE_DESC = 'Periscope'
    IE_NAME = 'periscope'
    _VALID_URL = r'https?://(?:www\.)?(?:periscope|pscp)\.tv/[^/]+/(?P<id>[^/?#]+)'
    # Alive example URLs can be found here https://www.periscope.tv/
    _TESTS = [{
        'url': 'https://www.periscope.tv/w/aJUQnjY3MjA3ODF8NTYxMDIyMDl2zCg2pECBgwTqRpQuQD352EMPTKQjT4uqlM3cgWFA-g==',
        'md5': '65b57957972e503fcbbaeed8f4fa04ca',
        'info_dict': {
            'id': '56102209',
            'ext': 'mp4',
            'title': 'Bec Boop - 🚠✈️🇬🇧 Fly above #London in Emirates Air Line cable car at night 🇬🇧✈️🚠 #BoopScope 🎀💗',
            'timestamp': 1438978559,
            'upload_date': '20150807',
            'uploader': 'Bec Boop',
            'uploader_id': '1465763',
        },
        'skip': 'Expires in 24 hours',
    }, {
        'url': 'https://www.periscope.tv/w/1ZkKzPbMVggJv',
        'only_matching': True,
    }, {
        'url': 'https://www.periscope.tv/bastaakanoggano/1OdKrlkZZjOJX',
        'only_matching': True,
    }, {
        'url': 'https://www.periscope.tv/w/1ZkKzPbMVggJv',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_url(webpage):
        mobj = re.search(
            r'<iframe[^>]+src=([\'"])(?P<url>(?:https?:)?//(?:www\.)?(?:periscope|pscp)\.tv/(?:(?!\1).)+)\1', webpage)
        if mobj:
            return mobj.group('url')

    def _real_extract(self, url):
        token = self._match_id(url)

        stream = self._call_api(
            'accessVideoPublic', {'broadcast_id': token}, token)

        broadcast = stream['broadcast']
        info = self._parse_broadcast_data(broadcast, token)

        state = broadcast.get('state').lower()
        width = int_or_none(broadcast.get('width'))
        height = int_or_none(broadcast.get('height'))

        def add_width_and_height(f):
            for key, val in (('width', width), ('height', height)):
                if not f.get(key):
                    f[key] = val

        video_urls = set()
        formats = []
        for format_id in ('replay', 'rtmp', 'hls', 'https_hls', 'lhls', 'lhlsweb'):
            video_url = stream.get(format_id + '_url')
            if not video_url or video_url in video_urls:
                continue
            video_urls.add(video_url)
            if format_id != 'rtmp':
                m3u8_formats = self._extract_pscp_m3u8_formats(
                    video_url, token, format_id, state, width, height, False)
                formats.extend(m3u8_formats)
                continue
            rtmp_format = {
                'url': video_url,
                'ext': 'flv' if format_id == 'rtmp' else 'mp4',
            }
            self._add_width_and_height(rtmp_format)
            formats.append(rtmp_format)
        self._sort_formats(formats)

        info['formats'] = formats
        return info


class PeriscopeUserIE(PeriscopeBaseIE):
    _VALID_URL = r'https?://(?:www\.)?(?:periscope|pscp)\.tv/(?P<id>[^/]+)/?$'
    IE_DESC = 'Periscope user videos'
    IE_NAME = 'periscope:user'

    _TEST = {
        'url': 'https://www.periscope.tv/LularoeHusbandMike/',
        'info_dict': {
            'id': 'LularoeHusbandMike',
            'title': 'LULAROE HUSBAND MIKE',
            'description': 'md5:6cf4ec8047768098da58e446e82c82f0',
        },
        # Periscope only shows videos in the last 24 hours, so it's possible to
        # get 0 videos
        'playlist_mincount': 0,
    }

    def _real_extract(self, url):
        user_name = self._match_id(url)

        webpage = self._download_webpage(url, user_name)

        data_store = self._parse_json(
            unescapeHTML(self._search_regex(
                r'data-store=(["\'])(?P<data>.+?)\1',
                webpage, 'data store', default='{}', group='data')),
            user_name)

        user = list(data_store['UserCache']['users'].values())[0]['user']
        user_id = user['id']
        session_id = data_store['SessionToken']['public']['broadcastHistory']['token']['session_id']

        broadcasts = self._call_api(
            'getUserBroadcastsPublic',
            {'user_id': user_id, 'session_id': session_id},
            user_name)['broadcasts']

        broadcast_ids = [
            broadcast['id'] for broadcast in broadcasts if broadcast.get('id')]

        title = user.get('display_name') or user.get('username') or user_name
        description = user.get('description')

        entries = [
            self.url_result(
                'https://www.periscope.tv/%s/%s' % (user_name, broadcast_id))
            for broadcast_id in broadcast_ids]

        return self.playlist_result(entries, user_id, title, description)
