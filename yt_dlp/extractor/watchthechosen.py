import datetime
import json

from .common import InfoExtractor
from ..utils import unified_strdate
from ..utils.traversal import traverse_obj


class WatchTheChosenIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?watch\.thechosen\.tv/video/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://watch.thechosen.tv/video/184683594325',
        'md5': 'a7030265262d659b9692a3418b189833',
        'info_dict': {
            'id': '184683594325',
            'ext': 'mp4',
            'title': 'Season 3 Episode 2: Two by Two',
            'description': 'Jesus is a problem for the Romans. With pilgrims from everywhere setting up a tent city at the gates of Capernaum to see Jesus, tensions rise. Jesus officially sends the twelve apostles on an exciting but dangerous mission, causing Little James to ask why he hasn’t been healed.',
            'thumbnail': 'https://fastly.frontrowcdn.com/channels/12884901895/VIDEO_THUMBNAIL/184683594325/3b180a4a-797e-403d-8929-ffcd3f29db4d.VIDEO_THUMBNAIL',
            'modified_date': str,
            'upload_date': '20231102',
            'duration': 4212,
            'like_count': int,
            'comment_count': int,
            'view_count': int,
        },
    }, {
        'url': 'https://watch.thechosen.tv/video/184683596189',
        'md5': '3bbfd4f0718b076481c5b823ec7a6760',
        'info_dict': {
            'id': '184683596189',
            'ext': 'mp4',
            'title': 'Season 4 Episode 8: Humble',
            'description': 'Jesus refuses to look and act like the Messiah everyone expects—arriving like a lamb instead of a lion and riding a donkey instead of a war horse.',
            'thumbnail': 'https://fastly.frontrowcdn.com/channels/12884901895/VIDEO_THUMBNAIL/184683596189/a6c070e0-0f8e-4813-a264-85b9944c98ea.VIDEO_THUMBNAIL',
            'modified_date': str,
            'upload_date': '20240506',
            'duration': 5092,
            'like_count': int,
            'comment_count': int,
            'view_count': int,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # DOWNLOADING METADATA
        metadata = traverse_obj(self._download_json(
            'https://api.frontrow.cc/query', video_id, data=json.dumps({
                'operationName': 'Video',
                'variables': {'channelID': '12884901895', 'videoID': video_id},
                'query': r'''query Video($channelID: ID!, $videoID: ID!) {
                    video(ChannelID: $channelID, VideoID: $videoID) {
                        ...VideoFragment __typename
                    }
                }
                fragment VideoFragment on Video {
                    title description updatedAt thumbnail createdAt duration likeCount comments views
                }''',
            }).encode(), headers={
                'channelid': '12884901895',
                'content-type': 'application/json',
            }), ('data', 'video'))

        # DOWNLOADING LIST OF SOURCES (LIST OF M3U8 FILES)
        hls_url = 'https://api.frontrow.cc/channels/12884901895/VIDEO/' + video_id + '/v2/hls.m3u8'
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(hls_url, video_id)

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(metadata, {
                'title': 'title',
                'description': 'description',
                'thumbnail': 'thumbnail',
                'modified_date': ('updatedAt', {unified_strdate}),
                'upload_date': ('createdAt', {unified_strdate}),
                'duration': 'duration',
                'like_count': 'likeCount',
                'comment_count': 'comments',
                'view_count': 'views',
            }),
        }
