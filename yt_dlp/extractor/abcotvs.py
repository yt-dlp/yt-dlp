from .common import InfoExtractor
from ..utils import (
    dict_get,
    int_or_none,
    try_get,
)


class ABCOTVSIE(InfoExtractor):
    IE_NAME = 'abcotvs'
    IE_DESC = 'ABC Owned Television Stations'
    _VALID_URL = r'https?://(?P<site>abc(?:7(?:news|ny|chicago)?|11|13|30)|6abc)\.com(?:(?:/[^/]+)*/(?P<display_id>[^/]+))?/(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'http://abc7news.com/entertainment/east-bay-museum-celebrates-vintage-synthesizers/472581/',
            'info_dict': {
                'id': '472548',
                'display_id': 'east-bay-museum-celebrates-vintage-synthesizers',
                'ext': 'mp4',
                'title': 'East Bay museum celebrates synthesized music',
                'description': 'md5:24ed2bd527096ec2a5c67b9d5a9005f3',
                'thumbnail': r're:^https?://.*\.jpg$',
                'timestamp': 1421118520,
                'upload_date': '20150113',
            },
            'params': {
                # m3u8 download
                'skip_download': True,
            },
        },
        {
            'url': 'http://abc7news.com/472581',
            'only_matching': True,
        },
        {
            'url': 'https://6abc.com/man-75-killed-after-being-struck-by-vehicle-in-chester/5725182/',
            'only_matching': True,
        },
    ]
    _SITE_MAP = {
        '6abc': 'wpvi',
        'abc11': 'wtvd',
        'abc13': 'ktrk',
        'abc30': 'kfsn',
        'abc7': 'kabc',
        'abc7chicago': 'wls',
        'abc7news': 'kgo',
        'abc7ny': 'wabc',
    }

    def _real_extract(self, url):
        site, display_id, video_id = self._match_valid_url(url).groups()
        display_id = display_id or video_id
        station = self._SITE_MAP[site]

        data = self._download_json(
            'https://api.abcotvs.com/v2/content', display_id, query={
                'id': video_id,
                'key': f'otv.web.{station}.story',
                'station': station,
            })['data']
        video = try_get(data, lambda x: x['featuredMedia']['video'], dict) or data
        video_id = str(dict_get(video, ('id', 'publishedKey'), video_id))
        title = video.get('title') or video['linkText']

        formats = []
        m3u8_url = video.get('m3u8')
        if m3u8_url:
            formats = self._extract_m3u8_formats(
                video['m3u8'].split('?')[0], display_id, 'mp4', m3u8_id='hls', fatal=False)
        mp4_url = video.get('mp4')
        if mp4_url:
            formats.append({
                'abr': 128,
                'format_id': 'https',
                'height': 360,
                'url': mp4_url,
                'width': 640,
            })

        image = video.get('image') or {}

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': dict_get(video, ('description', 'caption'), try_get(video, lambda x: x['meta']['description'])),
            'thumbnail': dict_get(image, ('source', 'dynamicSource')),
            'timestamp': int_or_none(video.get('date')),
            'duration': int_or_none(video.get('length')),
            'formats': formats,
        }


class ABCOTVSClipsIE(InfoExtractor):
    IE_NAME = 'abcotvs:clips'
    _VALID_URL = r'https?://clips\.abcotvs\.com/(?:[^/]+/)*video/(?P<id>\d+)'
    _TEST = {
        'url': 'https://clips.abcotvs.com/kabc/video/214814',
        'info_dict': {
            'id': '214814',
            'ext': 'mp4',
            'title': 'SpaceX launch pad explosion destroys rocket, satellite',
            'description': 'md5:9f186e5ad8f490f65409965ee9c7be1b',
            'upload_date': '20160901',
            'timestamp': 1472756695,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_data = self._download_json('https://clips.abcotvs.com/vogo/video/getByIds?ids=' + video_id, video_id)['results'][0]
        title = video_data['title']
        formats = self._extract_m3u8_formats(
            video_data['videoURL'].split('?')[0], video_id, 'mp4')

        return {
            'id': video_id,
            'title': title,
            'description': video_data.get('description'),
            'thumbnail': video_data.get('thumbnailURL'),
            'duration': int_or_none(video_data.get('duration')),
            'timestamp': int_or_none(video_data.get('pubDate')),
            'formats': formats,
        }
