# coding: utf-8
from __future__ import unicode_literals


from .common import InfoExtractor
from ..utils import unified_timestamp


class BanByeBaseIE(InfoExtractor):
    _API_BASE = 'https://api.banbye.com'
    _CDN_BASE = 'https://cdn.banbye.com'

    def _extract_playlist(self, playlist_id):
        data = self._download_json('%s/playlists/%s' % (self._API_BASE, playlist_id), playlist_id)
        return self.playlist_result([
            self.url_result('https://banbye.com/watch/%s' % video_id, ie_key='BanBye')
            for video_id in data['videoIds']], playlist_id, data['name'])


class BanByeIE(BanByeBaseIE):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?banbye.com/
                        (?:en/)?watch/
                        (?P<id>[^/?\#&]+)/?
                        \??(?:playlistId=(?P<playlist_id>[^/?\#&]+))?'''
    _TESTS = [{
        'url': 'https://banbye.com/watch/v_ytfmvkVYLE8T',
        'md5': '2f4ea15c5ca259a73d909b2cfd558eb5',
        'info_dict': {
            'id': 'v_ytfmvkVYLE8T',
            'ext': 'mp4',
            'title': 'md5:5ec098f88a0d796f987648de6322ba0f',
            'description': 'md5:4d94836e73396bc18ef1fa0f43e5a63a',
            'uploader': 'wRealu24',
            'channel_id': 'ch_wrealu24',
            'channel_url': 'https://banbye.com/channel/ch_wrealu24',
            'timestamp': 1647604800,
            'upload_date': '20220318',
            'duration': 1931,
            'thumbnail': r're:https?://.*\.webp',
            'tags': 'count:5',
            'like_count': int,
            'dislike_count': int,
            'view_count': int,
            'comment_count': int,
        },
    }, {
        'url': 'https://banbye.com/watch/v_2JjQtqjKUE_F?playlistId=p_Ld82N6gBw_OJ',
        'info_dict': {
            'title': 'Krzysztof Karoń',
            'id': 'p_Ld82N6gBw_OJ',
        },
        'playlist_count': 9,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        playlist_id = mobj.group('playlist_id')

        if playlist_id and not self.get_param('noplaylist'):
            self.to_screen(f'Downloading playlist {playlist_id}; add --no-playlist to just download video {video_id}')
            return self._extract_playlist(playlist_id)

        if playlist_id:
            self.to_screen(f'Downloading just video {video_id} because of --no-playlist')

        data = self._download_json('%s/videos/%s' % (self._API_BASE, video_id), video_id)
        thumbnails = [{
            'id': '%sp' % quality,
            'url': '%s/video/%s/%d.webp' % (self._CDN_BASE, video_id, quality),
        } for quality in [48, 96, 144, 240, 512, 1080]]
        formats = [{
            'format_id': 'http-%sp' % quality,
            'quality': quality,
            'url': '%s/video/%s/%d.mp4' % (self._CDN_BASE, video_id, quality),
        } for quality in data['quality']]

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': data['title'],
            'description': data['desc'],
            'uploader': data['channel']['name'],
            'channel_id': data['channelId'],
            'channel_url': 'https://banbye.com/channel/%s' % data['channelId'],
            'timestamp': unified_timestamp(data['publishedAt']),
            'duration': data['duration'],
            'tags': data['tags'],
            'formats': formats,
            'thumbnails': thumbnails,
            'like_count': data['likes'],
            'dislike_count': data['dislikes'],
            'view_count': data['views'],
            'comment_count': data['commentCount'],
        }


class BanByePlaylistIE(BanByeBaseIE):
    _VALID_URL = r'https?://(?:www\.)?banbye.com/(?:en/)?channel/[^/]+/?\?playlist=(?P<id>[^/?\#&]+)'
    _TESTS = [{
        'url': 'https://banbye.com/channel/ch_wrealu24?playlist=p_Ld82N6gBw_OJ',
        'info_dict': {
            'title': 'Krzysztof Karoń',
            'id': 'p_Ld82N6gBw_OJ',
        },
        'playlist_count': 9,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        return self._extract_playlist(playlist_id)
