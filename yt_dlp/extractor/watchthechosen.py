import datetime
import json

from .common import InfoExtractor


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
    },
        {
        'url': 'https://watch.thechosen.tv/video/184683596189',
        'md5': '52998d02633f7c0e2edc195c6f676a3d',
        'info_dict': {
            'id': '184683596189',
            'ext': 'mp4',
            'title': 'Season 4 Episode 8: Humble',
        },
    },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        # DOWNLOADING METADATA
        post_data = {'operationName': 'Video', 'variables': {'channelID': '12884901895', 'videoID': video_id},
                     'query': 'query Video($channelID: ID!, $videoID: ID!) { video(ChannelID: $channelID, VideoID: $videoID) { ...VideoFragment __typename } } fragment VideoFragment on Video { title description updatedAt thumbnail createdAt duration likeCount comments }'}
        encoded_data = json.dumps(post_data).encode('utf-8')  # Encode post data to bytes (so digestible for _download_json)
        headers = {'channelid': '12884901895', 'content-type': 'application/json'}  # POST-request headers
        metadata = self._download_json('https://api.frontrow.cc/query', video_id, data=encoded_data, headers=headers)['data']['video']

        # Helper for formatting dates in ISO 8601
        def formatDate(date):
            parsed_date = datetime.datetime.fromisoformat(date)
            return parsed_date.strftime('%Y%m%d')

        # DOWNLOADING LIST OF SOURCES (LIST OF M3U8 FILES)
        hls_url = 'https://api.frontrow.cc/channels/12884901895/VIDEO/' + video_id + '/v2/hls.m3u8'
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(hls_url, video_id)

        return {
            'id': video_id,
            'title': metadata['title'],
            'description': metadata['description'],
            'thumbnail': metadata['thumbnail'],
            'modified_date': formatDate(metadata['updatedAt']),
            'upload_date': formatDate(metadata['createdAt']),
            'duration': metadata['duration'],
            'like_count': metadata['likeCount'],
            'comment_count': metadata['comments'],
            'formats': formats,
            'subtitles': subtitles,
        }
