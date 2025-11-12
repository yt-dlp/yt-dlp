import re

from .common import InfoExtractor
from ..utils import ExtractorError


class YfanefaIE(InfoExtractor):
    IE_NAME = 'yfanefa'

    _VALID_URL = r'https?://(?:www\.)?yfanefa\.com/(?P<id>[^?#]+)'

    _TESTS = [{
        'url': 'https://www.yfanefa.com/record/2717',
        'info_dict': {
            'id': 'record/2717',
            'ext': 'mp4',
            'title': 'THE HALLAMSHIRE RIFLES LEAVING SHEFFIELD, 1914',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.yfanefa.com/news/53',
        'info_dict': {
            'id': 'news/53',
            'ext': 'mp4',
            'title': 'Memory Bank:  Bradford Launch',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.yfanefa.com/evaluating_nature_matters',
        'info_dict': {
            'id': 'evaluating_nature_matters',
            'ext': 'mp4',
            'title': 'Evaluating Nature Matters',
        },
        'params': {'skip_download': True},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        player_data = self._search_json(
            r'iwPlayer\.options\["[\w.]+"\]\s*=', webpage, 'player options', video_id)

        formats = []
        video_url = join_nonempty(player_data['url'], player_data.get('signature'), delim='')
        if determine_ext(video_url) == 'm3u8':
            formats = self._extract_m3u8_formats(
                video_url, video_id, 'mp4', m3u8_id='hls')
        else:
            formats = [{'url': video_url, 'ext': 'mp4'}]

        return {
            'id': video_id,
            'title': self._og_search_title(webpage, default=None) or self._html_extract_title(webpage),
            'formats': formats,
            **traverse_obj(player_data, {
                'thumbnail': ('preview', {url_or_none}),
                'duration': ('duration', {int_or_none}),
            }),
        }
