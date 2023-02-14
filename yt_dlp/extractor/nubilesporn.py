import re
import urllib.request
import urllib.response
from datetime import datetime
from urllib.error import HTTPError

from .common import InfoExtractor
from ..utils import parse_resolution, \
    get_element_text_and_html_by_tag, get_element_html_by_class, get_elements_html_by_class, extract_attributes, \
    clean_html, urlencode_postdata, get_element_by_class, parse_iso8601, float_or_none, int_or_none, \
    get_element_by_id, get_elements_by_class


class NubilesPornIE(InfoExtractor):
    _NETRC_MACHINE = 'nubiles-porn'

    _BASE_URL: str = 'nubiles-porn.com'
    _CDN_URL = f"https://content2a.{_BASE_URL}/exclusive"
    _VIDEO_SUFFIX: str = "video/watch"
    _THUMB_SUFFIX: str = "videos"

    _VALID_URL = r'https?://(?:www\.)?(?:members\.)?nubiles-porn\.com/video/watch/(?P<id>[0-9]+)/(?:[a-z-0-9]+)'
    _TESTS = [{
        'url': 'https://members.nubiles-porn.com/video/watch/165320/trying-to-focus-my-one-track-mind-s3e1',
        'md5': 'fa7f09da8027c35e4bdf0f94f55eac82',
        'info_dict': {
            'id': '165320',
            'title': 'Trying To Focus My One Track Mind - S3:E1',
            'formats': [
                {
                    'url': str,
                    'format_id': 'mp4_480_270',
                    'width': 480,
                    'height': 270,
                }, {
                    'url': str,
                    'format_id': 'mp4_640_360',
                    'width': 640,
                    'height': 360,
                }, {
                    'url': str,
                    'format_id': 'mp4_960_540',
                    'width': 960,
                    'height': 540,
                }, {
                    'url': str,
                    'format_id': 'mp4_1280_720',
                    'width': 1280,
                    'height': 720,
                }, {
                    'url': str,
                    'width': 1920,
                    'height': 1080,
                    'format_id': 'mp4_1920_1080',
                }, {
                    'url': str,
                    'format_id': 'mp4_3840_2160',
                    'width': 3840,
                    'height': 2160,
                }
            ],
            'ext': 'mp4',
            'display_id': 'trying-to-focus-my-one-track-mind-s3e1',
            'thumbnail': 'https://images.nubiles-porn.com/videos/trying_to_focus_my_one_track_mind/samples/cover1280.jpg',
            'description': 'Anthony Pierce was supposed to study, but when his tutor Kenzie Love tries to quiz him, '
                           'he can\'t seem to answer anything. Instead, Anthony just sits and stares at Kenzie\'s '
                           'boobs. When Kenzie realizes the source of Anthony\'s distraction, she pops her tits out '
                           'so he can see them and move on. She attempts to continue the lesson, but now Anthony '
                           'can\'t hide his boner.'
                           '\n'
                           'Exasperated, Kenzie offers to drain Anthony\'s balls so she can get the lesson moving. '
                           'Talk about Anthony getting everything he\'s dreamed of! His hot tutor leaves her glasses '
                           'on as she sucks his cock. When she Kenzie realizes that she\'s really impressed by the '
                           'size of Anthony\'s dick and that he\'s still hanging in there without cumming, she '
                           'decides to take things even further and peel her own clothes off for some mutual fun.'
                           '\n'
                           'Climbing onto Anthony\'s lap, the bigtit tutor rides him in reverse cowgirl. Then she '
                           'gets on her back so Anthony can stare at those big jugs as they jiggle with every one '
                           'of his thrusts. Kenzie can\'t stop now, so she rolls onto her knees and moans long and '
                           'loud as Anthony gives it to her in doggy. She finally achieves full ball drainage as '
                           'they spoon together, with Anthony pulling out at the last second to nut on Kenzie\'s '
                           'stomach. Now Kenzie is confident Anthony can concentrate on studying.',

            'creator': 'NubilesPorn',
            'release_timestamp': 1676160000,
            'release_date': '20230212',

            'uploader': 'NubilesPorn',
            'uploader_url': 'https://members.nubiles-porn.com',
            'timestamp': 1676160000,
            'upload_date': '20230212',

            'channel': 'Younger Mommy',
            'channel_id': 64,
            'channel_url': 'https://members.nubiles-porn.com/video/website/64',

            'like_count': int,
            'average_rating': float,

            'age_limit': 18,
            'webpage_url': 'https://members.nubiles-porn.com/video/watch/165320/trying-to-focus-my-one-track-mind-s3e1',

            'categories': ['Big Boobs', 'Big Naturals', 'Blowjob', 'Brunette', 'Cowgirl', 'Girl Orgasm', 'Girl-Boy',
                           'Glasses', 'Hardcore', 'Milf', 'Shaved Pussy', 'Tattoos', 'YoungerMommy.com'],
            'tags': ['Big Boobs', 'Big Naturals', 'Blowjob', 'Brunette', 'Cowgirl', 'Girl Orgasm', 'Girl-Boy',
                     'Glasses', 'Hardcore', 'Milf', 'Shaved Pussy', 'Tattoos', 'YoungerMommy.com'],
            'cast': ['Kenzie Love'],

            'availability': 'needs_auth',

            'series': 'Younger Mommy',
            'series_id': 64,
            'season': 'Season 3',
            'season_number': 3,
            'episode': 'Episode 1',
            'episode_number': 1,
        }
    }]

    def _perform_login(self, username, password):
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        login_webpage = self._download_webpage("https://nubiles-porn.com/login", video_id=None)
        hidden_inputs = self._hidden_inputs(login_webpage)
        hidden_inputs.update({'username': username, 'password': password})

        login_submit = urllib.request.Request(
            'https://nubiles-porn.com/authentication/login',
            data=urlencode_postdata(hidden_inputs)
        )

        opener = urllib.request.build_opener(NoRedirect, urllib.request.HTTPCookieProcessor(self.cookiejar))
        urllib.request.install_opener(opener)

        try:
            login_submission: urllib.response.addinfourl = opener.open(login_submit)
        except HTTPError as e:
            login_submission = e
        location = login_submission.info().get('location')
        login_submission.close()

        self._download_webpage(location, video_id=None)

    @staticmethod
    def _channel_info(element: str) -> dict:
        info = {}
        if path := extract_attributes(get_element_html_by_class('site-link', element)).get('href'):
            info['url'] = f'https://members.nubiles-porn.com{path}'
            info['id'] = int_or_none(path.split('/')[-1])
        if raw_name := get_element_by_class('site-link', element):
            info['name'] = ' '.join(re.findall('[A-Z][^A-Z]*', raw_name.replace('.com', '')))
        return info

    @staticmethod
    def _series_info(element: str) -> list:
        info = []
        if matches := re.findall('[a-zA-Z]+ - S(?P<season>[0-9]+):E(?P<episode>[0-9]+)', element):
            if len(matches) == 1:
                info += matches[0]
        return info

    @staticmethod
    def _get_formats(element) -> list[dict]:
        raw_formats = get_elements_html_by_class('edge-download-item', element)
        return list(map(NubilesPornIE._format_from_element, raw_formats))

    @staticmethod
    def _format_from_element(element: str) -> dict:
        resolution = parse_resolution(get_element_text_and_html_by_tag('div', element)[1])
        return dict(
            url=extract_attributes(get_element_html_by_class('btn', element)).get('href'),
            **resolution,
            format_id=f'mp4_{resolution.get("width")}_{resolution.get("height")}',
        )

    @staticmethod
    def _get_timestamp(element: str) -> int | None:
        if raw := get_element_by_class('date', element):
            return parse_iso8601(datetime.strptime(raw, '%b %d, %Y').isoformat())

    @staticmethod
    def _get_tags(element: str) -> list[str] | None:
        if raw_category_section := get_element_by_class('categories', element):
            if raw_categories := get_elements_by_class('btn', raw_category_section):
                return list(map(NubilesPornIE._tag_from_element, raw_categories))

    @staticmethod
    def _tag_from_element(element: str) -> str:
        return element.replace('\n', '').strip()

    def _real_extract(self, url):
        video_id = self._match_id(url)
        page: str = self._download_webpage(url, video_id=video_id)

        video_container = get_element_html_by_class('watch-page-video-container', page)
        container = get_element_html_by_class('container', page)

        title = get_element_text_and_html_by_tag("h2", container)[0]
        channel_info = NubilesPornIE._channel_info(container)
        series_info = NubilesPornIE._series_info(title)

        return dict(
            id=video_id,
            title=title,
            formats=NubilesPornIE._get_formats(container),
            ext='mp4',
            display_id=url.split('/')[-1],
            thumbnail=extract_attributes(get_element_html_by_class('edgecms-large-video-player', video_container)).get(
                'poster'),
            description=clean_html(get_element_html_by_class('content-pane-description', container)),

            creator='NubilesPorn',
            release_timestamp=NubilesPornIE._get_timestamp(container),

            uploader='NubilesPorn',
            uploader_url='https://members.nubiles-porn.com',
            timestamp=NubilesPornIE._get_timestamp(container),

            channel=channel_info.get('name'),
            channel_id=channel_info.get('id'),
            channel_url=channel_info.get('url'),

            like_count=int_or_none(get_element_by_id('likecount', container)),
            average_rating=float_or_none(get_element_by_class('score', container)),

            age_limit=18,
            webpage_url=url,

            categories=NubilesPornIE._get_tags(get_element_html_by_class('categories', container)),
            tags=NubilesPornIE._get_tags(container),
            cast=get_elements_by_class('content-pane-performer', container),

            availability='needs_auth',

            series=channel_info.get('name'),
            series_id=channel_info.get('id'),
            season_number=int_or_none(series_info[0]),
            episode_number=int_or_none(series_info[1]),
        )
