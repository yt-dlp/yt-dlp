from .common import InfoExtractor
from ..utils import (
    strftime_or_none,
    traverse_obj,
)


class RadioRadicaleIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?radioradicale\.it/scheda/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://www.radioradicale.it/scheda/471591',
        'info_dict': {
            'id': '471591',
            'ext': 'mp4',
            'title': 'md5:e8fbb8de57011a3255db0beca69af73d',
            'location': 'Napoli',
            'timestamp': 1459987200,
            'upload_date': '20160407',
            'description': 'md5:5e15a789a2fe4d67da8d1366996e89ef',
            'thumbnail': 'https://www.radioradicale.it/photo400/0/0/9/0/1/00901768.jpg',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        video_info = self._search_json(
            r'jQuery\.extend\(Drupal\.settings\s*,',
            webpage, 'video_info', video_id)['RRscheda']
        json_ld = self._search_json_ld(webpage, video_id)

        formats = []
        for source in traverse_obj(video_info, ('playlist', 0, 'sources')):
            formats.extend(
                self._extract_m3u8_formats(source.get('src'), video_id))

        subtitles = {sub.get('srclang') or 'und': [{
            'url': sub.get('src'),
            'name': sub.get('label')
        }] for sub in traverse_obj(video_info, ('playlist', 0, 'subtitles', ...))}

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'title': json_ld.get('title') or self._og_search_title(webpage),
            'location': video_info.get('luogo'),
            'timestamp': json_ld.get('timestamp'),
            'upload_date': strftime_or_none(json_ld.get('timestamp'), '%Y%m%d'),
            'thumbnail': traverse_obj(json_ld, ('thumbnails', 0, 'url')),
            'description': json_ld.get('description') or self._og_search_description(webpage),
        }
