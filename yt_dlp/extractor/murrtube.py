from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    extract_attributes,
    get_element_html_by_id,
    unified_timestamp,
    urlencode_postdata,
)


class MurrtubeIE(InfoExtractor):
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

    _age_check_done = False

    def _accept_age_check(self):
        if MurrtubeIE._age_check_done:
            return
        
        landing = self._download_webpage('https://murrtube.net/', None, note='Checking home page for age check')
        age_form = self._hidden_inputs(landing)

        # If there's no age form, we're good
        if not age_form:
            MurrtubeIE._age_check_done = True
            return

        # Submit the age confirmation form
        self._download_webpage(
            'https://murrtube.net/accept_age_check', None,
            note='Accepting age check',
            data=urlencode_postdata(age_form),
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': 'https://murrtube.net/',
                'X-Requested-With': 'XMLHttpRequest',
            })
        
        MurrtubeIE._age_check_done = True


    def _real_extract(self, url):
        video_id = self._match_id(url)

        self._accept_age_check()

        webpage = self._download_webpage(url, video_id)

        app_div = get_element_html_by_id('app', webpage)
        if not app_div:
            raise ExtractorError('Could not find app element')
        
        data_page_str = extract_attributes(app_div).get('data-page')
        if not data_page_str:
            raise ExtractorError('Could not find data-page attribute')
        
        data = self._parse_json(data_page_str, video_id)
        medium = data.get('props', {}).get('medium', {})

        formats = self._extract_m3u8_formats(medium.get('hls_url'), video_id, 'mp4') if medium.get('hls_url') else []

        return {
            'id': video_id,
            'title': medium.get('title'),
            'description': medium.get('description'),
            'thumbnail': medium.get('thumbnail_url'),
            'uploader': medium.get('user', {}).get('name'),
            'uploader_id': medium.get('user', {}).get('slug'),
            'timestamp': unified_timestamp(medium.get('created_at')),
            'release_timestamp': unified_timestamp(medium.get('published_at')),
            'duration': medium.get('duration'),
            'view_count': medium.get('views_count'),
            'like_count': medium.get('likes_count'),
            'comment_count': medium.get('comments_count'),
            'tags': [tag.get('name') for tag in medium.get('tags', []) if tag.get('name')],
            'age_limit': 18,
            'formats': formats,
            '_old_archive_ids': [f'murrtube {medium.get("id").replace("-", "")}'] if medium.get('id') else [],
        }


class MurrtubeUserIE(MurrtubeIE):
    IE_DESC = 'Murrtube user profile'
    _VALID_URL = r'https?://murrtube\.net/(?P<id>[^/]+)$'
    _TESTS = [{
        'url': 'https://murrtube.net/stormy',
        'info_dict': {
            'id': 'stormy',
        },
        'playlist_mincount': 10,
    }]
    _PAGE_SIZE = 60

    def _entries(self, url, username):
        page = 1
        while True:
            url_page = f'https://murrtube.net/{username}?page={page}' if page > 1 else url
            webpage = self._download_webpage(url_page, username, f'Downloading page {page}')
            
            app_div = get_element_html_by_id('app', webpage)
            if not app_div:
                break
                
            data_page_str = extract_attributes(app_div).get('data-page')
            if not data_page_str:
                break
                
            data = self._parse_json(data_page_str, username)
            props = data.get('props', {})
            media = props.get('media', [])
            
            for item in media:
                short_code = item.get('short_code')
                if short_code:
                    yield self.url_result(f'https://murrtube.net/v/{short_code}')
            
            pagination = props.get('pagination', {})
            if page >= pagination.get('pages', 1):
                break
                
            page += 1

    def _real_extract(self, url):
        username = self._match_id(url)
        self._accept_age_check()
        
        return self.playlist_result(self._entries(url, username), playlist_id=username)
