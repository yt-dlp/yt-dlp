from .common import InfoExtractor
from ..utils import (
    traverse_obj,
    unescapeHTML,
)
from .goplay_auth_aws import AwsIdp


class GoPlayIE(InfoExtractor):
    _VALID_URL = r'https?://(www\.)?goplay\.be/video/([^/]+/[^/]+/|)(?P<display_id>[^/#]+)'

    _NETRC_MACHINE = 'goplay'

    _TESTS = [{
        'url': 'https://www.goplay.be/video/de-container-cup/de-container-cup-s3/de-container-cup-s3-aflevering-2#autoplay',
        'info_dict': {
            'id': '9c4214b8-e55d-4e4b-a446-f015f6c6f811',
            'ext': 'mp4',
            'title': 'S3 - Aflevering 2',
            'series': 'De Container Cup',
            'season': 'Season 3',
            'season_number': 3,
            'episode': 'Episode 2',
            'episode_number': 2,
        },
        'skip': 'This video is only available for registered users'
    }, {
        'url': 'https://www.goplay.be/video/a-family-for-thr-holidays-s1-aflevering-1#autoplay',
        'info_dict': {
            'id': '74e3ed07-748c-49e4-85a0-393a93337dbf',
            'ext': 'mp4',
            'title': 'A Family for the Holidays',
        },
        'skip': 'This video is only available for registered users'
    }]

    _id_token = None

    def _perform_login(self, username, password):
        self.report_login()
        aws = AwsIdp(pool_id='eu-west-1_dViSsKM5Y', client_id='6s1h851s8uplco5h6mqh1jac8m')
        self._id_token, _ = aws.authenticate(username=username, password=password)

    def _real_initialize(self):
        if not self._id_token:
            raise self.raise_login_required(method='password')

    def _real_extract(self, url):
        url, display_id = self._match_valid_url(url).group(0, 'display_id')
        webpage = self._download_webpage(url, display_id)
        video_data_json = self._html_search_regex(r'<div\s+data-hero="([^"]+)"', webpage, 'video_data')
        video_data = self._parse_json(unescapeHTML(video_data_json), display_id).get('data')

        movie = video_data.get('movie')
        if movie:
            video_id = movie.get('videoUuid')
            info_dict = {
                'title': movie.get('title')
            }
        else:
            episode = traverse_obj(video_data, ('playlists', ..., 'episodes', lambda _, v: traverse_obj(v, ('pageInfo', 'url')) == url), get_all=False)
            video_id = episode.get('videoUuid')
            info_dict = {
                'title': episode.get('episodeTitle'),
                'series': traverse_obj(episode, ('program', 'title')),
                'season_number': episode.get('seasonNumber'),
                'episode_number': episode.get('episodeNumber'),
            }

        api = self._download_json(
            f'https://api.viervijfzes.be/content/{video_id}',
            video_id, headers={'Authorization': self._id_token})

        formats, subs = self._extract_m3u8_formats_and_subtitles(
            api['video']['S'], video_id, ext='mp4', m3u8_id='HLS')
        self._sort_formats(formats)

        info_dict.update({
            'id': video_id,
            'formats': formats,
        })

        return info_dict
