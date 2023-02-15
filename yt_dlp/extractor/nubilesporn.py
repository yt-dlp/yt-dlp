import re
from typing import Optional

from .common import InfoExtractor
from ..utils import parse_resolution, \
    get_element_text_and_html_by_tag, get_element_html_by_class, get_elements_html_by_class, extract_attributes, \
    clean_html, urlencode_postdata, get_element_by_class, float_or_none, int_or_none, \
    get_element_by_id, get_elements_by_class, unified_timestamp


class NubilesPornIE(InfoExtractor):
    _NETRC_MACHINE: str = 'nubiles-porn'

    _BASE_DOMAIN: str = 'nubiles-porn.com'
    _BASE_URL: str = f'https://{_BASE_DOMAIN}'
    _MEMBERS_URL = f'https://members.{_BASE_DOMAIN}'

    _VALID_URL: str = r'https://members.nubiles-porn.com/video/watch/(?P<id>\d+)/(?P<display_id>[a-z\d\-]+-(s(?P<season>\d+)e(?P<episode>\d+))$)'
    _VALID_VIDEO_URL: str = f're:https://content2a.{_BASE_DOMAIN}/exclusive/' + r'(?:[a-z_]+)/videos/(?:[a-z\d_]+).mp4\?st=(?:[\w\-]{22})&e=(?:[0-9]{10})&tr=(?:[A-Z0-9]{154})'

    _TESTS = [{
        'url': f'{_MEMBERS_URL}/video/watch/165320/trying-to-focus-my-one-track-mind-s3e1',
        'md5': 'fa7f09da8027c35e4bdf0f94f55eac82',
        'info_dict': {
            'id': '165320',
            'title': 'Trying To Focus My One Track Mind - S3:E1',
            'formats': [
                {'url': _VALID_VIDEO_URL, 'format_id': 'mp4_480_270', 'width': 480, 'height': 270},
                {'url': _VALID_VIDEO_URL, 'format_id': 'mp4_640_360', 'width': 640, 'height': 360},
                {'url': _VALID_VIDEO_URL, 'format_id': 'mp4_960_540', 'width': 960, 'height': 540},
                {'url': _VALID_VIDEO_URL, 'format_id': 'mp4_1280_720', 'width': 1280, 'height': 720},
                {'url': _VALID_VIDEO_URL, 'format_id': 'mp4_1920_1080', 'width': 1920, 'height': 1080},
                {'url': _VALID_VIDEO_URL, 'format_id': 'mp4_3840_2160', 'width': 3840, 'height': 2160}
            ],
            'ext': 'mp4',
            'display_id': 'trying-to-focus-my-one-track-mind-s3e1',
            'thumbnail': f'https://images.{_BASE_DOMAIN}/videos/trying_to_focus_my_one_track_mind/samples/cover1280.jpg',
            'description': 'md5:81f3d4372e0e39bff5c801da277a5141',
            'creator': 'NubilesPorn',
            'release_timestamp': 1676160000,
            'release_date': '20230212',
            'uploader': 'NubilesPorn',
            'uploader_url': _MEMBERS_URL,
            'timestamp': 1676160000,
            'upload_date': '20230212',
            'channel': 'Younger Mommy',
            'channel_id': 64,
            'channel_url': f'{_MEMBERS_URL}/video/website/64',
            'like_count': int,
            'average_rating': float,
            'age_limit': 18,
            'webpage_url': f'{_MEMBERS_URL}/video/watch/165320/trying-to-focus-my-one-track-mind-s3e1',
            'categories': ['Big Boobs', 'Big Naturals', 'Blowjob', 'Brunette', 'Cowgirl', 'Girl Orgasm', 'Girl-Boy',
                           'Glasses', 'Hardcore', 'Milf', 'Shaved Pussy', 'Tattoos', 'YoungerMommy.com'],
            'tags': list,
            'cast': ['Kenzie Love'],
            'availability': 'needs_auth',
            'series': 'Younger Mommy',
            'series_id': 64,
            'season': 'Season 3',
            'season_number': 3,
            'episode': 'Episode 1',
            'episode_number': 1
        }
    }]

    def _perform_login(self, username, password):
        login_webpage: str = self._download_webpage(f'{NubilesPornIE._BASE_URL}/login', video_id=None)
        hidden_inputs: dict = self._hidden_inputs(login_webpage)
        hidden_inputs.update({'username': username, 'password': password})
        self._request_webpage(f'{NubilesPornIE._BASE_URL}/authentication/login',
                              data=urlencode_postdata(hidden_inputs), video_id=None)

    @staticmethod
    def _get_channel_info(element: str) -> dict:
        info = {}
        path = extract_attributes(get_element_html_by_class('site-link', element)).get('href')
        if path:
            info['url'] = f'{NubilesPornIE._MEMBERS_URL}{path}'
            info['id'] = int_or_none(re.findall('/([0-9]+)$', path)[0])
        raw_name = get_element_by_class('site-link', element)
        if raw_name:
            info['name'] = ' '.join(re.findall('[A-Z][^A-Z]*', raw_name.replace('.com', '')))
        return info

    @staticmethod
    def _get_formats(element) -> list:
        return [NubilesPornIE._get_format(i) for i in get_elements_html_by_class('edge-download-item', element)]

    @staticmethod
    def _get_format(element: str) -> dict:
        res = parse_resolution(get_element_text_and_html_by_tag('div', element)[1])
        url = extract_attributes(get_element_html_by_class('btn', element)).get('href')
        return dict(url=f'https:{url}', **res, format_id=f'mp4_{res.get("width")}_{res.get("height")}')

    @staticmethod
    def _get_categories(element: str) -> Optional[list]:
        raw_category_section = get_element_by_class('categories', element) or ""
        raw_categories = get_elements_by_class('btn', raw_category_section)
        return [clean_html(i) for i in raw_categories]

    @staticmethod
    def _get_tags(element: str) -> Optional[list]:
        raw_tag_section = get_elements_by_class('tags', element)
        if len(raw_tag_section) >= 2:
            raw_tags = get_elements_by_class('btn', raw_tag_section[1])
            return [clean_html(i) for i in raw_tags]

    def _real_extract(self, url):
        url_match = self._match_valid_url(url)
        video_id = url_match.group('id')
        page: str = self._download_webpage(url, video_id=video_id)
        container = get_element_html_by_class('container', page)
        timestamp = unified_timestamp(get_element_by_class('date', container))
        channel_info = NubilesPornIE._get_channel_info(container)

        return {
            'id': video_id,
            'title': self._search_regex('<h2>([^<]+)</h2>', container, 'title'),
            'formats': NubilesPornIE._get_formats(container), 'ext': 'mp4',
            'display_id': url_match.group('display_id'),
            'thumbnail': self._search_regex('poster=\"(.*?)\"', page, 'thumbnail', fatal=False),
            'description': clean_html(get_element_html_by_class('content-pane-description', container)),
            'creator': 'NubilesPorn',
            'release_timestamp': timestamp,
            'uploader': 'NubilesPorn',
            'uploader_url': NubilesPornIE._MEMBERS_URL,
            'timestamp': timestamp,
            'channel': channel_info.get('name'),
            'channel_id': channel_info.get('id'),
            'channel_url': channel_info.get('url'),
            'like_count': int_or_none(get_element_by_id('likecount', container)),
            'average_rating': float_or_none(get_element_by_class('score', container)),
            'age_limit': 18,
            'webpage_url': url,
            'categories': NubilesPornIE._get_categories(container),
            'tags': NubilesPornIE._get_tags(container),
            'cast': get_elements_by_class('content-pane-performer', container),
            'availability': 'needs_auth',
            'series': channel_info.get('name'),
            'series_id': channel_info.get('id'),
            'season_number': int_or_none(url_match.group('season')),
            'episode_number': int_or_none(url_match.group('episode'))}
