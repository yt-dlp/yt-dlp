from .common import InfoExtractor
from ..compat import (
    compat_parse_qs,
    compat_urllib_parse_urlparse,
)
from ..utils import (
    format_field,
    float_or_none,
    int_or_none,
    parse_iso8601,
    remove_start,
    ExtractorError
)
from ..dependencies import Cryptodome
from ..networking import Request
import time, hashlib, random, os, json, binascii
from datetime import datetime

class ArnesIE(InfoExtractor):
    IE_NAME = 'video.arnes.si'
    IE_DESC = 'Arnes Video'
    _VALID_URL = r'https?://video-?\d?\.arnes\.si/(?:[a-z]{2}/)?(?:watch|embed|api/(?:asset|public/video))/(?P<id>[0-9a-zA-Z]{12})'
    _TESTS = [{
        'url': 'https://video.arnes.si/watch/a1qrWTOQfVoU?t=10',
        'md5': '4d0f4d0a03571b33e1efac25fd4a065d',
        'info_dict': {
            'id': 'a1qrWTOQfVoU',
            'ext': 'mp4',
            'title': 'Linearna neodvisnost, definicija',
            'description': 'Linearna neodvisnost, definicija',
            'license': 'PRIVATE',
            'creator': 'Polona Oblak',
            'timestamp': 1585063725,
            'upload_date': '20200324',
            'channel': 'Polona Oblak',
            'channel_id': 'q6pc04hw24cj',
            'channel_url': 'https://video.arnes.si/?channel=q6pc04hw24cj',
            'duration': 596.75,
            'view_count': int,
            'tags': ['linearna_algebra'],
            'start_time': 10,
        }
    }, {
        'url': 'https://video.arnes.si/api/asset/s1YjnV7hadlC/play.mp4',
        'only_matching': True,
    }, {
        'url': 'https://video.arnes.si/embed/s1YjnV7hadlC',
        'only_matching': True,
    }, {
        'url': 'https://video.arnes.si/en/watch/s1YjnV7hadlC',
        'only_matching': True,
    }, {
        'url': 'https://video.arnes.si/embed/s1YjnV7hadlC?t=123&hideRelated=1',
        'only_matching': True,
    }, {
        'url': 'https://video.arnes.si/api/public/video/s1YjnV7hadlC',
        'only_matching': True,
    }]

    _PARSED_URL=None
    _ACCESS_TOKEN=None

    def _generate_video_access_cookie(self):
        key_text = "Xmw1MSIlpZYdyy1DlqIl"
        key = hashlib.sha256(key_text.encode("utf-8")).digest()

        iv = os.urandom(12)
        # iv = bytearray([177, 70, 39, 213, 109, 49, 245, 24, 92, 85, 25, 187])

        time_component = int(datetime.now().timestamp()*1000)+random.randint(0,1000)
        # time_component = 1695271197003

        token_data = f"{self._ACCESS_TOKEN}|{time_component}"
        encoded_token = token_data.encode('utf-8')
        encrypted_data, tag = Cryptodome.AES.new(key, Cryptodome.AES.MODE_GCM, iv).encrypt_and_digest(encoded_token)

        base16encrypted_data = binascii.hexlify(iv).decode() + binascii.hexlify(encrypted_data+tag).decode()

        return base16encrypted_data

    def _generate_video_test_cookie(self):
        # Generate a random timestamp
        current_time = str(int(time.time()) + random.randint(1, 10000))

        return current_time

    def _set_access_cookie(self):
        vid_access_cookie=self._generate_video_access_cookie()
        self._set_cookie(self._PARSED_URL.netloc,"video_access_cookie",vid_access_cookie)


    def _real_extract(self, url):
        video_id = self._match_id(url)
        self._PARSED_URL = compat_urllib_parse_urlparse(url)

        base_url = f"{self._PARSED_URL.scheme}://{self._PARSED_URL.netloc}"

        self._ACCESS_TOKEN = compat_parse_qs(self._PARSED_URL.query).get("accessToken")[0]

        video_res = self._downloader.urlopen(base_url + '/api/public/video/' + video_id + f"?accessToken={self._ACCESS_TOKEN}")
        header_date = video_res.headers["Date"]

        date_object = datetime.strptime(header_date, '%a, %d %b %Y %H:%M:%S %Z')
        timestamp = int(date_object.timestamp()*1000)
        vid_access_cookie = self._generate_video_access_cookie()

        video_res = json.loads(video_res.read().decode())
            #self._download_json(base_url + '/api/public/video/' + video_id + f"?accessToken={self._ACCESS_TOKEN}", video_id)
        video = video_res['data']
        vid_test_cookie = self._generate_video_test_cookie()
        req_headers = {'Cookie': f'video_test_cookie={vid_test_cookie}; video_access_cookie={vid_access_cookie}'}
        check_cookies_request = Request(base_url + f'/api/public/video/embed-support/{vid_test_cookie}',
                headers = req_headers)

        check_cookies_data = self._download_json(check_cookies_request, video_id)
        if check_cookies_data['status'] != 'OK' or check_cookies_data['data'] != True:
            raise ExtractorError('Check cookies request did not succeed.')

        title = video['title']
        formats = []
        for media in (video.get('media') or []):
            media_url = media.get('url')
            if not media_url:
                continue
            formats.append({
                'url': base_url + media_url,
                'format_id': remove_start(media.get('format'), 'FORMAT_'),
                'format_note': media.get('formatTranslation'),
                'width': int_or_none(media.get('width')),
                'height': int_or_none(media.get('height')),
            })

        channel = video.get('channel') or {}
        channel_id = channel.get('url')
        thumbnail = video.get('thumbnailUrl')
        m3u8_url = base_url+video.get('hls').get('url') + f'?accessToken={self._ACCESS_TOKEN}'

        self._set_cookie(self._PARSED_URL.netloc,"video_access_cookie",vid_access_cookie)
        formats = self._extract_m3u8_formats(m3u8_url,video_id)
        return {
            'id': video_id,
            'title': title,
            'formats': formats,

            'thumbnail': base_url + thumbnail,
            'description': video.get('description'),
            'license': video.get('license'),
            'creator': video.get('author'),
            'timestamp': parse_iso8601(video.get('creationTime')),
            'channel': channel.get('name'),
            'channel_id': channel_id,
            'channel_url': format_field(channel_id, None, f'{base_url}/?channel=%s'),
            'duration': float_or_none(video.get('duration'), 1000),
            'view_count': int_or_none(video.get('views')),
            'tags': video.get('hashtags'),
            'start_time': int_or_none(compat_parse_qs(
                compat_urllib_parse_urlparse(url).query).get('t', [None])[0]),
            '_execute_before_each_fragment': self._set_access_cookie
        }
