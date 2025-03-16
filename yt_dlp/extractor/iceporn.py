from .common import InfoExtractor
from ..utils import int_or_none, parse_duration


class IcePornIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?iceporn\.com/video/(?P<id>[0-9]+)/(?P<display_id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.iceporn.com/video/2296835/eva-karera-gets-her-trimmed-cunt-plowed',
        'md5': '844482e1c3c45831859748550a1b8dcf',
        'info_dict': {
            'id': '2296835',
            'display_id': 'eva-karera-gets-her-trimmed-cunt-plowed',
            'title': 'Eva Karera gets her trimmed cunt plowed',
            'description': 're:Eva Karera Gets Her Trimmed Cunt Plowed - Pornstar, Milf, Blowjob, Big Boobs Porn Movies - 2296835',
            'thumbnail': 're:https?://g\\d.iceppsn.com/media/videos/tmb/\\d+/preview/\\d+.jpg',
            'ext': 'mp4',
            'duration': 2178,
        },
    }]

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).group('id', 'display_id')

        webpage = self._download_webpage(url, video_id)
        video_data = self._download_json('https://www.iceporn.com/player_config_json/', video_id, query={
            'vid': video_id, 'aid': 0, 'domain_id': 0, 'embed': 0, 'ref': 'null', 'check_speed': 0,
        }, headers={
            'Accept': 'application/json',
        })

        formats = []
        for quality_id, video_url in video_data.get('files', {}).items():
            if video_url:
                formats.append({
                    'url': video_url,
                    'format_id': quality_id,
                })

        return {
            'id': video_id,
            'display_id': display_id,
            'title': video_data.get('title')
            or self._html_search_regex(r'<div.*class=[\'"]caption[\'"].*?><h2>(.+?)</h2>',
                                       webpage, 'title'),
            'formats': formats,
            'thumbnail': video_data.get('poster'),
            'duration': int_or_none(video_data.get('duration'))
            or parse_duration(video_data.get('duration_format')),
            'description': self._html_search_meta('description', webpage),
        }
