from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    float_or_none,
    get_element_by_class,
    join_nonempty,
    traverse_obj,
    url_or_none,
)


class RottenTomatoesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rottentomatoes\.com/m/(?P<playlist>[^/]+)(?:/(?P<tr>trailers)(?:/(?P<id>\w+))?)?'

    _TESTS = [{
        'url': 'http://www.rottentomatoes.com/m/toy_story_3/trailers/11028566/',
        'info_dict': {
            'id': '11028566',
            'ext': 'mp4',
            'title': 'Toy Story 3',
            'description': 'From the creators of the beloved TOY STORY films, comes a story that will reunite the gang in a whole new way.',
        },
        'skip': 'No longer available',
    }, {
        'url': 'https://www.rottentomatoes.com/m/toy_story_3/trailers/VycaVoBKhGuk',
        'info_dict': {
            'id': 'VycaVoBKhGuk',
            'ext': 'mp4',
            'title': 'Toy Story 3: Trailer 2',
            'description': '',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 149.941,
        },
    }, {
        'url': 'http://www.rottentomatoes.com/m/toy_story_3',
        'info_dict': {
            'id': 'toy_story_3',
            'title': 'Toy Story 3',
        },
        'playlist_mincount': 4,
    }, {
        'url': 'http://www.rottentomatoes.com/m/toy_story_3/trailers',
        'info_dict': {
            'id': 'toy_story_3-trailers',
        },
        'playlist_mincount': 5,
    }]

    def _extract_videos(self, data, display_id):
        for video in traverse_obj(data, (lambda _, v: v['publicId'] and v['file'] and v['type'] == 'hls')):
            yield {
                'formats': self._extract_m3u8_formats(
                    video['file'], display_id, 'mp4', m3u8_id='hls', fatal=False),
                **traverse_obj(video, {
                    'id': 'publicId',
                    'title': 'title',
                    'description': 'description',
                    'duration': ('durationInSeconds', {float_or_none}),
                    'thumbnail': ('image', {url_or_none}),
                }),
            }

    def _real_extract(self, url):
        playlist_id, trailers, video_id = self._match_valid_url(url).group('playlist', 'tr', 'id')
        playlist_id = join_nonempty(playlist_id, trailers)
        webpage = self._download_webpage(url, playlist_id)
        data = self._search_json(
            r'<script[^>]+\bid=["\'](?:heroV|v)ideos["\'][^>]*>', webpage,
            'data', playlist_id, contains_pattern=r'\[{(?s:.+)}\]')

        if video_id:
            video_data = traverse_obj(data, lambda _, v: v['publicId'] == video_id)
            if not video_data:
                raise ExtractorError('Unable to extract video from webpage')
            return next(self._extract_videos(video_data, video_id))

        return self.playlist_result(
            self._extract_videos(data, playlist_id), playlist_id,
            clean_html(get_element_by_class('scoreboard__title', webpage)))
