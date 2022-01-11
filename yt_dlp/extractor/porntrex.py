# coding: utf-8
from .common import InfoExtractor
import re


class PorntrexIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?porntrex\.com/video/(?P<id>[0-9]+)/.+?'
    _TESTS = [{
        'url': 'https://www.porntrex.com/video/1894426/rkprime-ariana-van-x-pretty-in-pink',
        'md5': '82229c4b0f05b989984a2dfd090d1bf6',
        'info_dict': {
            'id': '1894426',
            'ext': 'mp4',
            'url': 'https://www.porntrex.com/get_file/12/8d782da4258e2cfd0dd3d9c5fbe93a97715ab0fa8d/1894000/1894426/1894426_1440p.mp4/',
            'title': 'RKPrime-Ariana Van X Pretty In Pink',
            'description': str,
            'thumbnail': r're:^https?://.*preview\.jpg$',
            'tags': list,
            'age_limit': 18
        },
    },
        {
            'url': 'https://www.porntrex.com/video/1894747/robin-mae-cumming-in-my-panties',
            'md5': '2440ec320f79d422f08b2be98c9adcf3',
            'info_dict': {
                'id': '1894747',
                'ext': 'mp4',
                'url': 'https://www.porntrex.com/get_file/18/da50fb34cb95580937389acba37c0b59860f2a1a9c/1894000/1894747/1894747_2160p.mp4/',
                'title': 'Robin Mae - Cumming In My Panties',
                'description': str,
                'thumbnail': r're:^https?://.*preview\.jpg$',
                'tags': list,
                'age_limit': 18
            },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        flashvars = self._html_search_regex(r'flashvars\s*=\s*{\s*([^}]+)', webpage, 'flashvars')

        tags = self._search_regex(r'video_tags:\s*\'([^\']+)\'', flashvars, 'video_url_text', default='').split(', ')
        video_url = self._search_regex(r'video_url:\s*\'([^\']+)\'', flashvars, 'video_url')

        # default url and quality
        formats = [{'url': video_url, 'quality': self._search_regex(r'video_url_text:\s*\'([^\']+)\'', flashvars, 'quality')}]

        # additional url and quality
        for mobj in re.finditer(r'video_alt_url(\d*):\s*\'(?P<video_url>[^\']+)\',[\s\S]*video_alt_url\1_text:\s*\'(?P<quality>[^\']+)\'', webpage):
            _, url, quality = mobj.groups()
            formats.append({
                'url': url,
                'quality': quality,
            })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'formats': formats,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage, default=None),
            'thumbnail': self._og_search_property('image', webpage, default=None),
            'tags': tags,
            'age_limit': 18
        }
