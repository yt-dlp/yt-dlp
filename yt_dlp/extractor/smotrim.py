import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
)


class SmotrimIE(InfoExtractor):
    _VALID_URL = r'https?://smotrim\.ru/(?:brand|video|article)/[0-9]+'
    _TESTS = [{
        'url': 'https://smotrim.ru/article/2813445',
        'md5': 'e0ac453952afbc6a2742e850b4dc8e77',
        'info_dict': {
            'id': '2588062',
            'ext': 'mp4',
            'title': 'Начались съёмки проекта "Большие и маленькие"',
            'description': 'Это уже четвёртый сезон танцевального шоу юных исполнителей.',
        }
    }]

    def _real_extract(self, url):
        webpage = self._download_webpage(url, 0)

        # Example:
        # <iframe src="https://player.smotrim.ru/iframe/video/id/2431846/start_zoom/true/showZoomBtn/false/sid/smotrim/isPlay/true/mute/true/?acc_video_id=2588062" >
        video_id = self._html_search_regex(r'<iframe[^>]*video_id=([0-9]+)[^>]*>', webpage, 'video_id', default=None)
        if video_id is None:
            raise ExtractorError('This page doesn\'t contain video.', expected=True)

        formats = [
            {
                'format_id': '1',
                'format': 'low-wide',
                'resolution': '234p',
            }, {
                'format_id': '2',
                'format': 'medium-wide',
                'resolution': '360p',
            }, {
                'format_id': '3',
                'format': 'high-wide',
                'resolution': '540p',
            }, {
                'format_id': '4',
                'format': 'hd-wide',
                'resolution': '720p',
            }, {
                'format_id': '5',
                'format': 'fhd-wide',
                'resolution': '1080p',
            }
        ]
        id_split = '/'.join(re.findall('...', video_id.zfill(9)))  # 2624356 > 002/624/356
        video_url = 'https://cdn-v.rtr-vesti.ru/_cdn_auth/secure/v/vh/mp4/{quality}/{id_split}.mp4?auth=mh&vid={id}'
        for i in range(len(formats)):
            formats[i]['url'] = video_url.format(quality=formats[i]['format'], id_split=id_split, id=video_id)
            formats[i]['ext'] = 'mp4'
            formats[i]['acodec'] = 'AAC'
            formats[i]['vcodec'] = 'H264'
        return {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'formats': formats,
        }
