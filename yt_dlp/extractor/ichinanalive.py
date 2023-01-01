from .common import InfoExtractor
from ..utils import ExtractorError, str_or_none, traverse_obj, unified_strdate
from ..compat import compat_str


class IchinanaLiveIE(InfoExtractor):
    IE_NAME = '17live'
    _VALID_URL = r'https?://(?:www\.)?17\.live/(?:[^/]+/)*(?:live|profile/r)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://17.live/live/3773096',
        'info_dict': {
            'id': '3773096',
            'title': '萠珈☕🤡🍫moka',
            'is_live': True,
            'uploader': '萠珈☕🤡🍫moka',
            'uploader_id': '3773096',
            'like_count': 366,
            'view_count': 18121,
            'timestamp': 1630569012,
        },
        'skip': 'running as of writing, but may be ended as of testing',
    }, {
        'note': 'nothing except language differs',
        'url': 'https://17.live/ja/live/3773096',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return not IchinanaLiveClipIE.suitable(url) and super(IchinanaLiveIE, cls).suitable(url)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        url = 'https://17.live/live/%s' % video_id

        enter = self._download_json(
            'https://api-dsa.17app.co/api/v1/lives/%s/enter' % video_id, video_id,
            headers={'Referer': url}, fatal=False, expected_status=420,
            data=b'\0')
        if enter and enter.get('message') == 'ended':
            raise ExtractorError('This live has ended.', expected=True)

        view_data = self._download_json(
            'https://api-dsa.17app.co/api/v1/lives/%s' % video_id, video_id,
            headers={'Referer': url})

        uploader = traverse_obj(
            view_data, ('userInfo', 'displayName'), ('userInfo', 'openID'))

        video_urls = view_data.get('rtmpUrls')
        if not video_urls:
            raise ExtractorError('unable to extract live URL information')
        formats = []
        for (name, value) in video_urls[0].items():
            if not isinstance(value, compat_str):
                continue
            if not value.startswith('http'):
                continue
            quality = -1
            if 'web' in name:
                quality -= 1
            if 'High' in name:
                quality += 4
            if 'Low' in name:
                quality -= 2
            formats.append({
                'format_id': name,
                'url': value,
                'quality': quality,
                'http_headers': {'Referer': url},
                'ext': 'flv',
                'vcodec': 'h264',
                'acodec': 'aac',
            })

        return {
            'id': video_id,
            'title': uploader or video_id,
            'formats': formats,
            'is_live': True,
            'uploader': uploader,
            'uploader_id': video_id,
            'like_count': view_data.get('receivedLikeCount'),
            'view_count': view_data.get('viewerCount'),
            'thumbnail': view_data.get('coverPhoto'),
            'description': view_data.get('caption'),
            'timestamp': view_data.get('beginTime'),
        }


class IchinanaLiveClipIE(InfoExtractor):
    IE_NAME = '17live:clip'
    _VALID_URL = r'https?://(?:www\.)?17\.live/(?:[^/]+/)*profile/r/(?P<uploader_id>\d+)/clip/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://17.live/profile/r/1789280/clip/1bHQSK8KUieruFXaCH4A4upCzlN',
        'info_dict': {
            'id': '1bHQSK8KUieruFXaCH4A4upCzlN',
            'title': 'マチコ先生🦋Class💋',
            'description': 'マチ戦隊　第一次　バスターコール\n総額200万coin！\n動画制作@うぉーかー🌱Walker🎫',
            'uploader_id': '1789280',
        },
    }, {
        'url': 'https://17.live/ja/profile/r/1789280/clip/1bHQSK8KUieruFXaCH4A4upCzlN',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        uploader_id, video_id = self._match_valid_url(url).groups()
        url = 'https://17.live/profile/r/%s/clip/%s' % (uploader_id, video_id)

        view_data = self._download_json(
            'https://api-dsa.17app.co/api/v1/clips/%s' % video_id, video_id,
            headers={'Referer': url})

        uploader = traverse_obj(
            view_data, ('userInfo', 'displayName'), ('userInfo', 'name'))

        formats = []
        if view_data.get('videoURL'):
            formats.append({
                'id': 'video',
                'url': view_data['videoURL'],
                'quality': -1,
            })
        if view_data.get('transcodeURL'):
            formats.append({
                'id': 'transcode',
                'url': view_data['transcodeURL'],
                'quality': -1,
            })
        if view_data.get('srcVideoURL'):
            # highest quality
            formats.append({
                'id': 'srcVideo',
                'url': view_data['srcVideoURL'],
                'quality': 1,
            })

        for fmt in formats:
            fmt.update({
                'ext': 'mp4',
                'protocol': 'https',
                'vcodec': 'h264',
                'acodec': 'aac',
                'http_headers': {'Referer': url},
            })

        return {
            'id': video_id,
            'title': uploader or video_id,
            'formats': formats,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'like_count': view_data.get('likeCount'),
            'view_count': view_data.get('viewCount'),
            'thumbnail': view_data.get('imageURL'),
            'duration': view_data.get('duration'),
            'description': view_data.get('caption'),
            'upload_date': unified_strdate(str_or_none(view_data.get('createdAt'))),
        }
