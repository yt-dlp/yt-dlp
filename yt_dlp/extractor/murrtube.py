import itertools
from .common import InfoExtractor
from ..utils import (
    IDENTITY,
    extract_attributes,
    find_element,
    int_or_none,
    parse_qs,
    require,
    traverse_obj,
    unified_timestamp,
    update_url_query,
    urlencode_postdata,
)

class MurrtubeBaseIE(InfoExtractor):
    _BASE_URL = 'https://murrtube.net/'

    _age_check_done = False

    def _real_initialize(self):
        self._accept_age_check()

    def _accept_age_check(self):
        if MurrtubeBaseIE._age_check_done:
            return
        
        landing = self._download_webpage(self._BASE_URL, None, note='Checking home page for age check')
        age_form = self._hidden_inputs(landing)

        # If there's no age form, we're good
        if not age_form:
            MurrtubeBaseIE._age_check_done = True
            return

        # Submit the age confirmation form
        self._download_webpage(
            f'{self._BASE_URL}accept_age_check', None,
            note='Accepting age check',
            data=urlencode_postdata(age_form),
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': self._BASE_URL,
                'X-Requested-With': 'XMLHttpRequest',
            })
        
        MurrtubeBaseIE._age_check_done = True

    def _extract_data_page(self, webpage, page_id, fatal=True):
        maybe_require = require if fatal else lambda _: IDENTITY
        data_page_str = traverse_obj(webpage, (
            {find_element(attr='id', value='app', html=True)},
            {maybe_require('app element')},
            {extract_attributes}, 'data-page', {str},
            {maybe_require('data-page attribute')}))
        
        return traverse_obj(self._parse_json(
            data_page_str or '', page_id, fatal=fatal), {dict}) or {}

class MurrtubeIE(MurrtubeBaseIE):
    _VALID_URL = r'https?://murrtube\.net/v/(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://murrtube.net/v/IAPW',
        'md5': '99c6c5e0a8b1414cf4f52042b6166827',
        'file_minsize': None,
        'info_dict': {
            'id': 'IAPW',
            'ext': 'mp4',
            'title': 'Inferno X Skyler',
            'description': 'Humping a very good slutty sheppy (roomate)',
            'uploader': 'Inferno Wolf',
            'uploader_id': 'inferno-wolf',
            'age_limit': 18,
            'thumbnail': 'https://storage.murrtube.net/038/ca885d8456b95de529b6723b158032e11115d/thumbnail.jpg',
            'comment_count': int,
            'view_count': int,
            'like_count': int,
            'timestamp': 1588192741,
            'release_timestamp': 1588431972,
            'duration': 284,
            'tags': ['bareback', 'breeding', 'fursuit', 'humping', 'murrsuit'],
            'upload_date': '20200429',
            'release_date': '20200502',
            '_old_archive_ids': ['murrtube 148b6f2afdcc4902affe9c0f41aaaca0'],
        }
    }, {
        'url': 'https://murrtube.net/v/0J2Q',
        'md5': '174fe9d6c9e664fdb042e85d0dbffc49',
        'file_minsize': None,
        'info_dict': {
            'id': '0J2Q',
            'ext': 'mp4',
            'uploader': 'Hayel',
            'uploader_id': 'hayel',
            'title': 'Who\'s in charge now?',
            'description': 'Fenny sneaked into my bed room and played naughty with one of my plushies. I caught him in the act and wanted to punish him. He thought he was in charge and wanted to use me instead but he wasn\'t prepared on my butt milking him within just a minute.\n\nFenny: @fenny_ad (both here and on Twitter)\nHayel on Twitter: https://twitter.com/plushmods',
            'age_limit': 18,
            'thumbnail': 'https://storage.murrtube.net/03c/8442998c52134968d9caa36e473e1a6bac6ca/thumbnail.jpg',
            'comment_count': int,
            'view_count': int,
            'like_count': int,
            'timestamp': 1652996188,
            'release_timestamp': 1653039644,
            'duration': 331,
            'upload_date': '20220519',
            'release_date': '20220520',
            'tags': ['anal', 'deer', 'fursuit', 'male/male', 'murrsuit', 'plushie', 'plushophilia', 'toy', 'wolf'],
            '_old_archive_ids': ['murrtube fcfd303b00024da99a9fbef8ce4c0f0d'],
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        data = self._extract_data_page(webpage, video_id)
        
        medium = traverse_obj(data, ('props', 'medium'))

        formats = self._extract_m3u8_formats(medium.get('hls_url'), video_id, 'mp4')

        return {
            'id': video_id,
            'title': medium.get('title'),
            'description': medium.get('description'),
            'thumbnail': medium.get('thumbnail_url'),
            'uploader': traverse_obj(medium, ('user', 'name')),
            'uploader_id': traverse_obj(medium, ('user', 'slug')),
            'timestamp': unified_timestamp(medium.get('created_at')),
            'release_timestamp': unified_timestamp(medium.get('published_at')),
            'duration': medium.get('duration'),
            'view_count': medium.get('views_count'),
            'like_count': medium.get('likes_count'),
            'comment_count': medium.get('comments_count'),
            'tags': traverse_obj(medium, ('tags', ..., 'name')),
            'age_limit': 18,
            'formats': formats,
            '_old_archive_ids': traverse_obj(medium, ('id', {str}, {lambda x: [f'murrtube {x.replace("-", "")}']})) or [],
        }


class MurrtubeUserIE(MurrtubeIE):
    IE_DESC = 'Murrtube user profile'
    _VALID_URL = r'https?://murrtube\.net/(?P<id>[^/?]+)(?:\?|$)'
    _TESTS = [{
        'url': 'https://murrtube.net/stormy',
        'info_dict': {
            'id': 'stormy',
        },
        'playlist_mincount': 10,
    }, {
        'url': 'https://murrtube.net/sacris',
        'info_dict': {
            'id': 'sacris',
        },
        'playlist_mincount': 62,
    },]
    _PAGE_SIZE = 60

    def _entries(self, url, username):
        url_page = url
        the_page = traverse_obj(parse_qs(url), (
            'page', -1, {int_or_none}, all))
        for page in the_page or itertools.count(1):
            if not url_page:
                url_page = update_url_query(
                    f'{self._BASE_URL}{username}',
                    query={'page': page})
            webpage = self._download_webpage(
                url_page, username, f'Downloading page {page}')
            data = self._extract_data_page(webpage, username, fatal=False)
            if not data:
                break
            props = traverse_obj(data, ('props', {dict}) or {})
            for short_code in traverse_obj(props, (
                    'media', ..., 'short_code')):
                if short_code:
                    yield self.url_result(
                        f'{self._BASE_URL}v/{short_code}',
                        MurrtubeIE)
            if page >= (traverse_obj(props, (
                    'pagination', 'pages', {int_or_none})) or 1):
                break
            url_page = None

    def _real_extract(self, url):
        username = self._match_id(url)
        
        return self.playlist_result(self._entries(url, username), playlist_id=username)
