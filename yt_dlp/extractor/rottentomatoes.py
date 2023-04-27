from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    js_to_json,
    parse_duration,
    traverse_obj,
    urljoin,
)


class RottenTomatoesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rottentomatoes\.com/m/(?P<playlist>[^/]+)(?:/(?P<tr>trailers)(?:/(?P<id>\w+))?)?'

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


class RottenTomatoesPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rottentomatoes\.com/m/(?P<id>[^/]+)(?:/trailers)?/?(?:$|[#?])'

    _TESTS = [{
        'url': 'http://www.rottentomatoes.com/m/toy_story_3',
        'info_dict': {
            'id': 'toy_story_3',
            'title': 'Toy Story 3',
        },
        'playlist_mincount': 4,
    }, {
        'url': 'http://www.rottentomatoes.com/m/toy_story_3/trailers',
        'info_dict': {
            'id': 'toy_story_3',
            'title': 'toy_story_3',
        },
        'playlist_mincount': 5,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        webpage = self._download_webpage(url, playlist_id)
        raw_playlist_info = self._html_search_regex(
            r'<script[^>]*id=["\'](?:videos|heroVideos)["\'][^>]*>([^<]+)</script>',
            webpage, 'playlist info', default=None)
        playlist_info = self._parse_json(raw_playlist_info, playlist_id, transform_source=js_to_json)

        if isinstance(playlist_info, list):
            entries = [self.url_result(urljoin(url, video.get('videoPageUrl')),
                       ie=RottenTomatoesIE.ie_key()) for video in playlist_info]
        else:
            raise ExtractorError('Playlist %s is not available' % playlist_id, expected=True)

        title = self._html_search_regex(
            r'<h1[^>]+slot=["\']title["\'][^>]*>([^<]+)</h1>', webpage, 'playlist title',
            fatal=False, default=playlist_id)

        return self.playlist_result(entries, playlist_id, title)
