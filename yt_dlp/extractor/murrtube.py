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
    _TEST = {
        'url': 'https://murrtube.net/videos/inferno-x-skyler-148b6f2a-fdcc-4902-affe-9c0f41aaaca0',
        'md5': '70380878a77e8565d4aea7f68b8bbb35',
        'info_dict': {
            'id': 'IAPW',
            'ext': 'mp4',
            'title': 'Inferno X Skyler',
            'description': 'Humping a very good slutty sheppy (roomate)',
            'uploader': 'Inferno Wolf',
            'age_limit': 18,
            'thumbnail': 'https://storage.murrtube.net/murrtube-production/ekbs3zcfvuynnqfx72nn2tkokvsd',
            'comment_count': int,
            'view_count': int,
            'like_count': int,
            'timestamp': int,
            'release_timestamp': int,
            '_old_archive_ids': ['murrtube ca885d8456b95de529b6723b158032e11115d'],
        },
    }, {
        'url': 'https://murrtube.net/v/0J2Q',
        'md5': '31262f6ac56f0ca75e5a54a0f3fefcb6',
        'info_dict': {
            'id': '0J2Q',
            'ext': 'mp4',
            'uploader': 'Hayel',
            'title': 'Who\'s in charge now?',
            'description': 'md5:795791e97e5b0f1805ea84573f02a997',
            'age_limit': 18,
            'thumbnail': 'https://storage.murrtube.net/murrtube-production/fb1ojjwiucufp34ya6hxu5vfqi5s',
            'comment_count': int,
            'view_count': int,
            'like_count': int,
            'timestamp': int,
            'release_timestamp': int,
            'tags': ['anal', 'deer', 'fursuit', 'male/male', 'murrsuit', 'plushie', 'plushophilia', 'toy', 'wolf'],
            '_old_archive_ids': ['murrtube 8442998c52134968d9caa36e473e1a6bac6ca'],
        }
    }

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
    _WORKING = False
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
                    yield self.url_result(f"https://murrtube.net/v/{short_code}")
            
            pagination = props.get('pagination', {})
            if page >= pagination.get('pages', 1):
                break
                
            page += 1

    def _real_extract(self, url):
        username = self._match_id(url)
        self._accept_age_check()
        
        return self.playlist_result(self._entries(url, username), playlist_id=username)
