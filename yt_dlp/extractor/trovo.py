# coding: utf-8
from __future__ import unicode_literals

import itertools
import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    format_field,
    int_or_none,
    str_or_none,
    try_get,
)


class TrovoBaseIE(InfoExtractor):
    _VALID_URL_BASE = r'https?://(?:www\.)?trovo\.live/'
    _HEADERS = {'Origin': 'https://trovo.live'}

    def _call_api(self, video_id, query=None, data=None):
        return self._download_json(
            'https://gql.trovo.live/', video_id, query=query, data=data,
            headers={'Accept': 'application/json'})

    def _extract_streamer_info(self, data):
        streamer_info = data.get('streamerInfo') or {}
        username = streamer_info.get('userName')
        return {
            'uploader': streamer_info.get('nickName'),
            'uploader_id': str_or_none(streamer_info.get('uid')),
            'uploader_url': format_field(username, template='https://trovo.live/%s'),
        }


class TrovoIE(TrovoBaseIE):
    _VALID_URL = TrovoBaseIE._VALID_URL_BASE + r'(?!(?:clip|video)/)(?P<id>[^/?&#]+)'

    def _real_extract(self, url):
        username = self._match_id(url)
        live_info = self._call_api(username, query={
            'query': '''{
  getLiveInfo(params: {userName: "%s"}) {
    isLive
    programInfo {
      coverUrl
      id
      streamInfo {
        desc
        playUrl
      }
      title
    }
    streamerInfo {
        nickName
        uid
        userName
    }
  }
}''' % username,
        })['data']['getLiveInfo']
        if live_info.get('isLive') == 0:
            raise ExtractorError('%s is offline' % username, expected=True)
        program_info = live_info['programInfo']
        program_id = program_info['id']
        title = program_info['title']

        formats = []
        for stream_info in (program_info.get('streamInfo') or []):
            play_url = stream_info.get('playUrl')
            if not play_url:
                continue
            format_id = stream_info.get('desc')
            formats.append({
                'format_id': format_id,
                'height': int_or_none(format_id[:-1]) if format_id else None,
                'url': play_url,
                'http_headers': self._HEADERS,
            })
        self._sort_formats(formats)

        info = {
            'id': program_id,
            'title': title,
            'formats': formats,
            'thumbnail': program_info.get('coverUrl'),
            'is_live': True,
        }
        info.update(self._extract_streamer_info(live_info))
        return info


class TrovoVodIE(TrovoBaseIE):
    _VALID_URL = TrovoBaseIE._VALID_URL_BASE + r'(?:clip|video)/(?P<id>[^/?&#]+)'
    _TESTS = [{
        'url': 'https://trovo.live/video/ltv-100095501_100095501_1609596043',
        'info_dict': {
            'id': 'ltv-100095501_100095501_1609596043',
            'ext': 'mp4',
            'title': 'Spontaner 12 Stunden Stream! - Ok Boomer!',
            'uploader': 'Exsl',
            'timestamp': 1609640305,
            'upload_date': '20210103',
            'uploader_id': '100095501',
            'duration': 43977,
            'view_count': int,
            'like_count': int,
            'comment_count': int,
            'comments': 'mincount:8',
            'categories': ['Grand Theft Auto V'],
        },
        'skip': '404'
    }, {
        'url': 'https://trovo.live/clip/lc-5285890810184026005',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        vid = self._match_id(url)
        resp = self._call_api(vid, data=json.dumps([{
            'query': '''{
  batchGetVodDetailInfo(params: {vids: ["%s"]}) {
    VodDetailInfos
  }
}''' % vid,
        }, {
            'query': '''{
  getCommentList(params: {appInfo: {postID: "%s"}, pageSize: 1000000000, preview: {}}) {
    commentList {
      author {
        nickName
        uid
      }
      commentID
      content
      createdAt
      parentID
    }
  }
}''' % vid,
        }]).encode())
        vod_detail_info = resp[0]['data']['batchGetVodDetailInfo']['VodDetailInfos'][vid]
        vod_info = vod_detail_info['vodInfo']
        title = vod_info['title']

        language = vod_info.get('languageName')
        formats = []
        for play_info in (vod_info.get('playInfos') or []):
            play_url = play_info.get('playUrl')
            if not play_url:
                continue
            format_id = play_info.get('desc')
            formats.append({
                'ext': 'mp4',
                'filesize': int_or_none(play_info.get('fileSize')),
                'format_id': format_id,
                'height': int_or_none(format_id[:-1]) if format_id else None,
                'language': language,
                'protocol': 'm3u8_native',
                'tbr': int_or_none(play_info.get('bitrate')),
                'url': play_url,
                'http_headers': self._HEADERS,
            })
        self._sort_formats(formats)

        category = vod_info.get('categoryName')
        get_count = lambda x: int_or_none(vod_info.get(x + 'Num'))

        comment_list = try_get(resp, lambda x: x[1]['data']['getCommentList']['commentList'], list) or []
        comments = []
        for comment in comment_list:
            content = comment.get('content')
            if not content:
                continue
            author = comment.get('author') or {}
            parent = comment.get('parentID')
            comments.append({
                'author': author.get('nickName'),
                'author_id': str_or_none(author.get('uid')),
                'id': str_or_none(comment.get('commentID')),
                'text': content,
                'timestamp': int_or_none(comment.get('createdAt')),
                'parent': 'root' if parent == 0 else str_or_none(parent),
            })

        info = {
            'id': vid,
            'title': title,
            'formats': formats,
            'thumbnail': vod_info.get('coverUrl'),
            'timestamp': int_or_none(vod_info.get('publishTs')),
            'duration': int_or_none(vod_info.get('duration')),
            'view_count': get_count('watch'),
            'like_count': get_count('like'),
            'comment_count': get_count('comment'),
            'comments': comments,
            'categories': [category] if category else None,
        }
        info.update(self._extract_streamer_info(vod_detail_info))
        return info


class TrovoChannelBaseIE(TrovoBaseIE):
    def _get_vod_json(self, page, uid):
        raise NotImplementedError('This method must be implemented by subclasses')

    def _entries(self, uid):
        for page in itertools.count(1):
            vod_json = self._get_vod_json(page, uid)
            vods = vod_json.get('vodInfos', [])
            for vod in vods:
                yield self.url_result(
                    'https://trovo.live/%s/%s' % (self._TYPE, vod.get('vid')),
                    ie=TrovoVodIE.ie_key())
            has_more = vod_json['hasMore']
            if not has_more:
                break

    def _real_extract(self, url):
        id = self._match_id(url)
        uid = str(self._call_api(id, query={
            'query': '{getLiveInfo(params:{userName:"%s"}){streamerInfo{uid}}}' % id
        })['data']['getLiveInfo']['streamerInfo']['uid'])
        return self.playlist_result(self._entries(uid), playlist_id=uid)


class TrovoChannelVodIE(TrovoChannelBaseIE):
    _VALID_URL = r'trovovod:(?P<id>[^\s]+)'
    IE_DESC = 'All VODs of a trovo.live channel; "trovovod:" prefix'

    _TESTS = [{
        'url': 'trovovod:OneTappedYou',
        'playlist_mincount': 24,
        'info_dict': {
            'id': '100719456',
        },
    }]

    _QUERY = '{getChannelLtvVideoInfos(params:{pageSize:99,currPage:%d,channelID:%s}){hasMore,vodInfos{vid}}}'
    _TYPE = 'video'

    def _get_vod_json(self, page, uid):
        return self._call_api(uid, query={
            'query': self._QUERY % (page, uid)
        })['data']['getChannelLtvVideoInfos']


class TrovoChannelClipIE(TrovoChannelBaseIE):
    _VALID_URL = r'trovoclip:(?P<id>[^\s]+)'
    IE_DESC = 'All Clips of a trovo.live channel; "trovoclip:" prefix'

    _TESTS = [{
        'url': 'trovoclip:OneTappedYou',
        'playlist_mincount': 29,
        'info_dict': {
            'id': '100719456',
        },
    }]

    _QUERY = '{getChannelClipVideoInfos(params:{pageSize:99,currPage:%d,channelID:%s,albumType:VOD_CLIP_ALBUM_TYPE_LATEST}){hasMore,vodInfos{vid}}}'
    _TYPE = 'clip'

    def _get_vod_json(self, page, uid):
        return self._call_api(uid, query={
            'query': self._QUERY % (page, uid)
        })['data']['getChannelClipVideoInfos']
