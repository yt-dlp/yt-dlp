import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    float_or_none,
    format_field,
    get_element_by_class,
    get_element_by_id,
    get_element_html_by_class,
    get_elements_by_class,
    int_or_none,
    unified_timestamp,
    urlencode_postdata,
)
from ..utils.traversal import find_element, find_elements, traverse_obj


class NubilesPornIE(InfoExtractor):
    _NETRC_MACHINE = 'nubiles-porn'
    _VALID_URL = r'''(?x)
        https://members\.nubiles-porn\.com/video/watch/(?P<id>\d+)
        (?:/(?P<display_id>[\w\-]+-s(?P<season>\d+)e(?P<episode>\d+)))?
    '''

    _TESTS = [{
        'url': 'https://members.nubiles-porn.com/video/watch/165320/trying-to-focus-my-one-track-mind-s3e1',
        'md5': 'fa7f09da8027c35e4bdf0f94f55eac82',
        'info_dict': {
            'id': '165320',
            'title': 'Trying To Focus My One Track Mind - S3:E1',
            'ext': 'mp4',
            'display_id': 'trying-to-focus-my-one-track-mind-s3e1',
            'thumbnail': 'https://images.nubiles-porn.com/videos/trying_to_focus_my_one_track_mind/samples/cover1280.jpg',
            'description': 'md5:81f3d4372e0e39bff5c801da277a5141',
            'timestamp': 1676160000,
            'upload_date': '20230212',
            'channel': 'Younger Mommy',
            'channel_id': '64',
            'channel_url': 'https://members.nubiles-porn.com/video/website/64',
            'like_count': int,
            'average_rating': float,
            'age_limit': 18,
            'categories': ['Big Boobs', 'Big Naturals', 'Blowjob', 'Brunette', 'Cowgirl', 'Girl Orgasm', 'Girl-Boy',
                           'Glasses', 'Hardcore', 'Milf', 'Shaved Pussy', 'Tattoos', 'YoungerMommy.com'],
            'tags': list,
            'cast': ['Kenzie Love'],
            'availability': 'needs_auth',
            'series': 'Younger Mommy',
            'series_id': '64',
            'season': 'Season 3',
            'season_number': 3,
            'episode': 'Episode 1',
            'episode_number': 1,
        },
    }]

    def _perform_login(self, username, password):
        login_webpage = self._download_webpage('https://nubiles-porn.com/login', video_id=None)
        inputs = self._hidden_inputs(login_webpage)
        inputs.update({'username': username, 'password': password})
        self._request_webpage('https://nubiles-porn.com/authentication/login', None, data=urlencode_postdata(inputs))

    def _real_extract(self, url):
        url_match = self._match_valid_url(url)
        video_id = url_match.group('id')
        page = self._download_webpage(url, video_id)

        media_entries = self._parse_html5_media_entries(
            url, get_element_by_class('watch-page-video-wrapper', page), video_id)[0]

        channel_id, channel_name = self._search_regex(
            r'/video/website/(?P<id>\d+).+>(?P<name>\w+).com', get_element_html_by_class('site-link', page) or '',
            'channel', fatal=False, group=('id', 'name')) or (None, None)

        return {
            'id': video_id,
            'title': self._search_regex('<h2>([^<]+)</h2>', page, 'title', fatal=False),
            'formats': media_entries.get('formats'),
            'display_id': url_match.group('display_id'),
            'thumbnail': media_entries.get('thumbnail'),
            'description': clean_html(get_element_html_by_class('content-pane-description', page)),
            'timestamp': unified_timestamp(get_element_by_class('date', page)),
            'channel': re.sub(r'([^A-Z]+)([A-Z]+)', r'\1 \2', channel_name) if channel_name else None,
            'channel_id': channel_id,
            'channel_url': format_field(channel_id, None, 'https://members.nubiles-porn.com/video/website/%s'),
            'like_count': int_or_none(get_element_by_id('likecount', page)),
            'average_rating': float_or_none(get_element_by_class('score', page)),
            'age_limit': 18,
            'categories': traverse_obj(page, ({find_element(cls='categories')}, {find_elements(cls='btn')}, ..., {clean_html})),
            'tags': traverse_obj(page, ({find_elements(cls='tags')}, 1, {find_elements(cls='btn')}, ..., {clean_html})),
            'cast': get_elements_by_class('content-pane-performer', page),
            'availability': 'needs_auth',
            'series': channel_name,
            'series_id': channel_id,
            'season_number': int_or_none(url_match.group('season')),
            'episode_number': int_or_none(url_match.group('episode')),
        }
