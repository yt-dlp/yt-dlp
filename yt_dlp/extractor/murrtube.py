import functools

from .common import InfoExtractor
from ..utils import (
    OnDemandPagedList,
    clean_html,
    extract_attributes,
    parse_count,
    parse_qs,
    unescapeHTML,
    url_or_none,
    urlencode_postdata,
)
from ..utils.traversal import (
    find_element,
    find_elements,
    traverse_obj,
)


class MurrtubeBaseIE(InfoExtractor):
    _BASE_URL = 'https://murrtube.net'

    def _real_initialize(self):
        if not self._get_cookies(self._BASE_URL).get('age_check'):
            webpage = self._download_webpage(
                self._BASE_URL, None, 'Getting session token')
            self._request_webpage(
                f'{self._BASE_URL}/accept_age_check', None, 'Setting age cookie',
                data=urlencode_postdata(self._hidden_inputs(webpage)))


class MurrtubeIE(MurrtubeBaseIE):
    IE_NAME = 'murrtube'

    _VALID_URL = r'https?://murrtube\.net/v(?:ideos)?/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://murrtube.net/videos/inferno-x-skyler-148b6f2a-fdcc-4902-affe-9c0f41aaaca0',
        'info_dict': {
            'id': 'ca885d8456b95de529b6723b158032e11115d',
            'ext': 'mp4',
            'title': 'Inferno X Skyler',
            'age_limit': 18,
            'comment_count': int,
            'description': 'md5:1b6ffa7e3231b4e976f0f6db035a2184',
            'display_id': 'inferno-x-skyler-148b6f2a-fdcc-4902-affe-9c0f41aaaca0',
            'like_count': int,
            'thumbnail': r're:https://storage\.murrtube\.net/murrtube-production/.*$',
            'uploader': 'Inferno Wolf',
            'uploader_id': 'inferno-wolf',
            'view_count': int,
        },
    }, {
        'url': 'https://murrtube.net/v/0J2Q',
        'info_dict': {
            'id': '8442998c52134968d9caa36e473e1a6bac6ca',
            'ext': 'mp4',
            'title': 'Who\'s in charge now?',
            'age_limit': 18,
            'comment_count': int,
            'description': 'md5:795791e97e5b0f1805ea84573f02a997',
            'display_id': '0J2Q',
            'like_count': int,
            'thumbnail': r're:https://storage\.murrtube\.net/murrtube-production/.*$',
            'uploader': 'Hayel',
            'uploader_id': 'hayel',
            'view_count': int,
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        thumbnail, m3u8_url = traverse_obj(webpage, (
            {find_element(id='video', html=True)},
            {extract_attributes}, ('poster', 'data-url'), {url_or_none},
        ))

        return {
            'id': self._search_regex(r'(\w+)/index\.m3u8', m3u8_url, 'video_id'),
            'age_limit': 18,
            'display_id': display_id,
            'formats': self._extract_m3u8_formats(m3u8_url, display_id, 'mp4'),
            'thumbnail': thumbnail,
            **traverse_obj(webpage, ({find_element(id='medium-info', html=True)}, {
                'title': ({find_element(tag='h1')}, {str}, {unescapeHTML}),
                'description': ({find_element(cls='is-size-6 has-white-space-pre-wrap has-text-lighter-1')}, {clean_html}, filter),
                'uploader': ({find_element(cls='pl-1 is-size-6 has-text-lighter')}, {str.strip}),
                'uploader_id': (
                    {find_element(tag='a', attr='href', html=True)},
                    {extract_attributes}, 'href', {lambda x: x.lstrip('/')},
                ),
            })),
            **{
                f'{x}_count': parse_count(self._search_regex(
                    rf'([\d,]+)\s+<span[^>]*>{x.capitalize()}s?</span>', webpage, x, default=None,
                )) for x in ('comment', 'like', 'view')
            },
        }


class MurrtubePlaylistIE(MurrtubeBaseIE):
    IE_NAME = 'murrtube:playlist'

    _PAGE_SIZE = 20
    _VALID_URL = r'https?://murrtube\.net/(?P<id>[\w-]+)(?:\?|$)'
    _TESTS = [{
        'url': 'https://murrtube.net/stormy',
        'info_dict': {
            'id': 'stormy',
        },
        'playlist_mincount': 35,
    }, {
        'url': 'https://murrtube.net/search?q=test',
        'info_dict': {
            'id': 'test',
        },
        'playlist_mincount': 10,
    }]

    def _fetch_page(self, slug, query, page):
        page += 1
        webpage = self._download_webpage(
            f'{self._BASE_URL}/{slug}', query or slug,
            f'Downloading page {page}', query={
                'page': page,
                'q': query,
            },
        )
        for video_id in traverse_obj(webpage, (
            {find_elements(tag='a', attr='href', value=r'/v/\w{4}', html=True, regex=True)},
            ..., {extract_attributes}, 'href', {str},
        )):
            yield self.url_result(f'{self._BASE_URL}{video_id}', MurrtubeIE)

    def _real_extract(self, url):
        slug = self._match_id(url)
        query = parse_qs(url).get('q', [None])[0]

        return self.playlist_result(OnDemandPagedList(
            functools.partial(self._fetch_page, slug, query), self._PAGE_SIZE), query or slug)
