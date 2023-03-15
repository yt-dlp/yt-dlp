from .common import InfoExtractor
from .videomore import VideomoreIE
from ..compat import compat_str
from ..utils import float_or_none, format_field, int_or_none, try_get


class CarambaTVIE(InfoExtractor):
    _VALID_URL = r'(?:carambatv:|https?://video1\.carambatv\.ru/v/)(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://video1.carambatv.ru/v/191910501',
        'md5': '2f4a81b7cfd5ab866ee2d7270cb34a2a',
        'info_dict': {
            'id': '191910501',
            'ext': 'mp4',
            'title': '[BadComedian] - Разборка в Маниле (Абсолютный обзор)',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 2678.31,
        },
    }, {
        'url': 'carambatv:191910501',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video = self._download_json(
            f'http://video1.carambatv.ru/v/{video_id}/videoinfo.js',
            video_id)

        title = video['title']

        base_url = video.get('video') or f'http://video1.carambatv.ru/v/{video_id}/'

        formats = [{
            'url': base_url + f['fn'],
            'height': int_or_none(f.get('height')),
            'format_id': format_field(f, 'height', '%sp'),
        } for f in video['qualities'] if f.get('fn')]

        thumbnail = video.get('splash')
        duration = float_or_none(try_get(
            video, lambda x: x['annotations'][0]['end_time'], compat_str))

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'duration': duration,
            'formats': formats,
        }


class CarambaTVPageIE(InfoExtractor):
    _VALID_URL = r'https?://carambatv\.ru/(?:[^/]+/)+(?P<id>[^/?#&]+)'
    _TEST = {
        'url': 'http://carambatv.ru/movie/bad-comedian/razborka-v-manile/',
        'md5': 'a49fb0ec2ad66503eeb46aac237d3c86',
        'info_dict': {
            'id': '475222',
            'ext': 'flv',
            'title': '[BadComedian] - Разборка в Маниле (Абсолютный обзор)',
            'thumbnail': r're:^https?://.*\.jpg',
            # duration reported by videomore is incorrect
            'duration': int,
        },
        'add_ie': [VideomoreIE.ie_key()],
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        videomore_url = VideomoreIE._extract_url(webpage)
        if not videomore_url:
            videomore_id = self._search_regex(
                r'getVMCode\s*\(\s*["\']?(\d+)', webpage, 'videomore id',
                default=None)
            if videomore_id:
                videomore_url = f'videomore:{videomore_id}'
        if videomore_url:
            title = self._og_search_title(webpage)
            return {
                '_type': 'url_transparent',
                'url': videomore_url,
                'ie_key': VideomoreIE.ie_key(),
                'title': title,
            }

        video_url = self._og_search_property('video:iframe', webpage, default=None)

        if not video_url:
            video_id = self._search_regex(
                r'(?:video_id|crmb_vuid)\s*[:=]\s*["\']?(\d+)',
                webpage, 'video id')
            video_url = f'carambatv:{video_id}'

        return self.url_result(video_url, CarambaTVIE.ie_key())
