from .common import InfoExtractor
from ..utils import (
    js_to_json,
    parse_duration,
    traverse_obj,
)


class RottenTomatoesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rottentomatoes\.com/m/(?P<display_id>[^/]+)(?:/trailers/(?P<id>[\da-zA-Z]+))?'

    _TESTS = [{
        'url': 'http://www.rottentomatoes.com/m/toy_story_3/trailers/11028566/',
        'info_dict': {
            'id': '11028566',
            'ext': 'mp4',
            'title': 'Best Tom Hanks Movies',
            'description': 'We look at the filmography of America\'s Dad, as we count down our list of the best Tom Hanks movies.',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 1468.592
        },
    }, {
        'url': 'https://www.rottentomatoes.com/m/toy_story_3/trailers/VycaVoBKhGuk',
        'info_dict': {
            'id': 'VycaVoBKhGuk',
            'ext': 'mp4',
            'title': 'Toy Story 3: Trailer 2',
            'description': '',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 149.941
        },
    }, {
        'url': 'https://www.rottentomatoes.com/m/santa_claus_conquers_the_martians',
        'info_dict': {
            'id': 'santa_claus_conquers_the_martians',
            'ext': 'mp4',
            'title': 'Santa Claus Conquers the Martians: Trailer 1',
            'description': '',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 75.576
        },
    }]

    def _real_extract(self, url):
        display_id, video_id = self._match_valid_url(url).groups()
        video_id = video_id or display_id
        webpage = self._download_webpage(url, video_id)
        raw_video_info = self._html_search_regex(
            r'<script[^>]*id=["\'](?:videos|heroVideos)["\'][^>]*>([^<]+)</script>',
            webpage, 'video_info', default=None)
        video_info = self._parse_json(raw_video_info, video_id, transform_source=js_to_json)

        return {
            'id': video_id,
            'title': traverse_obj(video_info, (0, 'title')),
            'description': traverse_obj(video_info, (0, 'description')),
            'thumbnail': traverse_obj(video_info, (0, 'image')),
            'formats': self._extract_m3u8_formats(
                traverse_obj(video_info, (0, 'file')), video_id, 'mp4', 'm3u8_native',
                m3u8_id=traverse_obj(video_info, (0, 'type')), note='Downloading m3u8 information',
                errnote='Unable to download m3u8 information'),
            'duration': parse_duration(traverse_obj(video_info, (0, 'durationInSeconds'),
                                                    default=traverse_obj(video_info, (0, 'duration'))))
        }
