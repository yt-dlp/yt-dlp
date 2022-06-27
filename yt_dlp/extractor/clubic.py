from .common import InfoExtractor
from ..utils import (
    clean_html,
    qualities,
)


class ClubicIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?clubic\.com/video/(?:[^/]+/)*video.*-(?P<id>[0-9]+)\.html'

    _TESTS = [{
        'url': 'http://www.clubic.com/video/clubic-week/video-clubic-week-2-0-le-fbi-se-lance-dans-la-photo-d-identite-448474.html',
        'md5': '1592b694ba586036efac1776b0b43cd3',
        'info_dict': {
            'id': '448474',
            'ext': 'mp4',
            'title': 'Clubic Week 2.0 : le FBI se lance dans la photo d\u0092identité',
            'description': 're:Gueule de bois chez Nokia. Le constructeur a indiqué cette.*',
            'thumbnail': r're:^http://img\.clubic\.com/.*\.jpg$',
        }
    }, {
        'url': 'http://www.clubic.com/video/video-clubic-week-2-0-apple-iphone-6s-et-plus-mais-surtout-le-pencil-469792.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        player_url = 'http://player.m6web.fr/v1/player/clubic/%s.html' % video_id
        player_page = self._download_webpage(player_url, video_id)

        config = self._parse_json(self._search_regex(
            r'(?m)M6\.Player\.config\s*=\s*(\{.+?\});$', player_page,
            'configuration'), video_id)

        video_info = config['videoInfo']
        sources = config['sources']
        quality_order = qualities(['sd', 'hq'])

        formats = [{
            'format_id': src['streamQuality'],
            'url': src['src'],
            'quality': quality_order(src['streamQuality']),
        } for src in sources]
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': video_info['title'],
            'formats': formats,
            'description': clean_html(video_info.get('description')),
            'thumbnail': config.get('poster'),
        }
