import datetime
import json

from .common import InfoExtractor
from ..utils.traversal import traverse_obj


class WatchTheChosenIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?watch\.thechosen\.tv/video/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://watch.thechosen.tv/video/184683594325',
        'md5': '03405a126e90f5e48d449005de7d585e',
        'info_dict': {
            'id': '184683594325',
            'ext': 'mp4',
            'title': 'Season 3 Episode 2: Two by Two',
        },
    }, {
        'url': 'https://watch.thechosen.tv/video/184683596189',
        'md5': '52998d02633f7c0e2edc195c6f676a3d',
        'info_dict': {
            'id': '184683596189',
            'ext': 'mp4',
            'title': 'Season 4 Episode 8: Humble',
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
                    title description updatedAt thumbnail createdAt duration likeCount comments
                }''',
            }).encode(), headers={
                'channelid': '12884901895',
                'content-type': 'application/json'
            }), ('data', 'video'))

        # Helper for formatting dates in ISO 8601
        def formatDate(date):
            parsed_date = datetime.datetime.fromisoformat(date)
            return parsed_date.strftime('%Y%m%d')

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
                'modified_date': ('updatedAt', {formatDate}),
                'upload_date': ('createdAt', {formatDate}),
                'duration': 'duration',
                'like_count': 'likeCount',
                'comment_count': 'comments',
            }),
        }
