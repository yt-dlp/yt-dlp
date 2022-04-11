from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
)


class ViddlerIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?viddler\.com/(?:v|embed|player)/(?P<id>[a-z0-9]+)(?:.+?\bsecret=(\d+))?'
    _TESTS = [{
        'url': 'http://www.viddler.com/v/43903784',
        'md5': '9eee21161d2c7f5b39690c3e325fab2f',
        'info_dict': {
            'id': '43903784',
            'ext': 'mov',
            'title': 'Video Made Easy',
            'description': 'md5:6a697ebd844ff3093bd2e82c37b409cd',
            'uploader': 'viddler',
            'timestamp': 1335371429,
            'upload_date': '20120425',
            'duration': 100.89,
            'thumbnail': r're:^https?://.*\.jpg$',
            'view_count': int,
            'comment_count': int,
            'categories': ['video content', 'high quality video', 'video made easy', 'how to produce video with limited resources', 'viddler'],
        }
    }, {
        'url': 'http://www.viddler.com/v/4d03aad9/',
        'md5': 'f12c5a7fa839c47a79363bfdf69404fb',
        'info_dict': {
            'id': '4d03aad9',
            'ext': 'ts',
            'title': 'WALL-TO-GORTAT',
            'upload_date': '20150126',
            'uploader': 'deadspin',
            'timestamp': 1422285291,
            'view_count': int,
            'comment_count': int,
        }
    }, {
        'url': 'http://www.viddler.com/player/221ebbbd/0/',
        'md5': '740511f61d3d1bb71dc14a0fe01a1c10',
        'info_dict': {
            'id': '221ebbbd',
            'ext': 'mov',
            'title': 'LETeens-Grammar-snack-third-conditional',
            'description': ' ',
            'upload_date': '20140929',
            'uploader': 'BCLETeens',
            'timestamp': 1411997190,
            'view_count': int,
            'comment_count': int,
        }
    }, {
        # secret protected
        'url': 'http://www.viddler.com/v/890c0985?secret=34051570',
        'info_dict': {
            'id': '890c0985',
            'ext': 'mp4',
            'title': 'Complete Property Training - Traineeships',
            'description': ' ',
            'upload_date': '20130606',
            'uploader': 'TiffanyBowtell',
            'timestamp': 1370496993,
            'view_count': int,
            'comment_count': int,
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id, secret = self._match_valid_url(url).groups()

        query = {
            'video_id': video_id,
            'key': 'v0vhrt7bg2xq1vyxhkct',
        }
        if secret:
            query['secret'] = secret

        data = self._download_json(
            'http://api.viddler.com/api/v2/viddler.videos.getPlaybackDetails.json',
            video_id, headers={'Referer': url}, query=query)['video']

        formats = []
        for filed in data['files']:
            if filed.get('status', 'ready') != 'ready':
                continue
            format_id = filed.get('profile_id') or filed['profile_name']
            f = {
                'format_id': format_id,
                'format_note': filed['profile_name'],
                'url': self._proto_relative_url(filed['url']),
                'width': int_or_none(filed.get('width')),
                'height': int_or_none(filed.get('height')),
                'filesize': int_or_none(filed.get('size')),
                'ext': filed.get('ext'),
                'source_preference': -1,
            }
            formats.append(f)

            if filed.get('cdn_url'):
                f = f.copy()
                f['url'] = self._proto_relative_url(filed['cdn_url'], 'http:')
                f['format_id'] = format_id + '-cdn'
                f['source_preference'] = 1
                formats.append(f)

            if filed.get('html5_video_source'):
                f = f.copy()
                f['url'] = self._proto_relative_url(filed['html5_video_source'])
                f['format_id'] = format_id + '-html5'
                f['source_preference'] = 0
                formats.append(f)
        self._sort_formats(formats)

        categories = [
            t.get('text') for t in data.get('tags', []) if 'text' in t]

        return {
            'id': video_id,
            'title': data['title'],
            'formats': formats,
            'description': data.get('description'),
            'timestamp': int_or_none(data.get('upload_time')),
            'thumbnail': self._proto_relative_url(data.get('thumbnail_url')),
            'uploader': data.get('author'),
            'duration': float_or_none(data.get('length')),
            'view_count': int_or_none(data.get('view_count')),
            'comment_count': int_or_none(data.get('comment_count')),
            'categories': categories,
        }
