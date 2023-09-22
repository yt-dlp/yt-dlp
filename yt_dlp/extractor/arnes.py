import binascii
import hashlib
import json
import os
import random
import time
from datetime import datetime

from .common import InfoExtractor
from ..compat import (
    compat_parse_qs,
    compat_urllib_parse_urlparse,
)
from ..dependencies import Cryptodome
from ..utils import (
    format_field,
    float_or_none,
    int_or_none,
    parse_iso8601,
    remove_start,
)


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
            'thumbnail': 'https://video.arnes.si/attachments/video/a1/a1qrWTOQfVoU/transcoded/image/ZfOtoJ9CVl7AKcZIpK3jTEvB.480p.jpg'
        }
    }, {
        # one needs to be registered to get this url on: https://bsf.si/sl/film/dan-ljubezni-epizoda-10/
        'url': 'https://video-4.arnes.si/embed/4zdg767pl9sv?accessToken=ZONPEE6G6ZM36WYPAIC5M2BL&hideRelated=1',
        'only_matching': True,
        'md5': '84c1e19403a4e50fa2394451675563f3',
        'info_dict': {
            'id': '4zdg767pl9sv',
            'ext': 'mp4',
            'title': 'Dan ljubezni E10 - nova',
            'thumbnail': 'https://video-4.arnes.si/attachments/video/4z/4zdg767pl9sv/transcoded/image/Q1gZUVXgDgZZ.1nvm5msy0xkg.480p.jpg',
            'description': 'film',
            'license': 'CC_BY_NC_SA',
            'creator': 'Video Filmoteka',
            'timestamp': 1681422237,
            'channel': 'Video Filmoteka',
            'channel_id': 'd6rb30mw368k',
            'channel_url': 'https://video-4.arnes.si/?channel=d6rb30mw368k',
            'duration': 651.6,
            'view_count': 44,
            'upload_date': '20230413',
            'tags': []
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

    _PARSED_URL = None
    _ACCESS_TOKEN = None
    _TIME_OF_LAST_VID_ACCESS_COOKIE_CHANGED = 0

    # 10s was found when watching how requests are send and when cookie changes
    _TIME_BETWEEN_NEW_COOKIE = 10

    def _generate_video_access_cookie(self):
        # Text of key that is then sha256ed gathered from main-es2015.62cf37eb23d6552e6e54.js
        # before video_access_cookie is added
        key_text = 'Xmw1MSIlpZYdyy1DlqIl'
        key = hashlib.sha256(key_text.encode('utf-8')).digest()

        iv = os.urandom(12)

        time_component = int(datetime.now().timestamp() * 1000) + random.randint(0, 1000)

        token_data = f'{self._ACCESS_TOKEN}|{time_component}'
        encoded_token = token_data.encode('utf-8')
        encrypted_data, tag = Cryptodome.AES.new(key, Cryptodome.AES.MODE_GCM, iv).encrypt_and_digest(encoded_token)

        base16encrypted_data = binascii.hexlify(iv).decode() + binascii.hexlify(encrypted_data + tag).decode()

        return base16encrypted_data

    def _set_access_cookie(self):
        """
        Generates a new video access cookie and sets it.

        This function should be executed between each downloaded segment.
        """
        if self._ACCESS_TOKEN is None:
            return

        current_time = time.time()
        if current_time - self._TIME_OF_LAST_VID_ACCESS_COOKIE_CHANGED > self._TIME_BETWEEN_NEW_COOKIE:
            vid_access_cookie = self._generate_video_access_cookie()
            self._set_cookie(self._PARSED_URL.netloc, 'video_access_cookie', vid_access_cookie)
            self._TIME_OF_LAST_VID_ACCESS_COOKIE_CHANGED = current_time
            self.write_debug("New video_access_cookie generated.")

    def _fragment_hook_before_download(self, frag_filename, frag_info_dict, ctx):
        self._set_access_cookie()

    def _real_extract(self, url):
        video_id = self._match_id(url)
        self._PARSED_URL = compat_urllib_parse_urlparse(url)
        at_list = compat_parse_qs(self._PARSED_URL.query).get('accessToken')
        self._ACCESS_TOKEN = at_list[0] if at_list is not None and len(at_list) != 0 else None

        base_url = f'{self._PARSED_URL.scheme}://{self._PARSED_URL.netloc}'
        access_token_query = f'?accessToken={self._ACCESS_TOKEN}' if self._ACCESS_TOKEN is not None else '?'

        video_res = self._downloader.urlopen(f'{base_url}/api/public/video/{video_id}{access_token_query}')

        video_res = json.loads(video_res.read().decode())
        video = video_res['data']

        title = video['title']
        channel = video.get('channel') or {}
        channel_id = channel.get('url')
        thumbnail = video.get('thumbnailUrl')

        formats = []
        if video.get('hls') is None:
            for media in (video.get('media') or []):
                media_url = media.get('url')
                if not media_url:
                    continue
                formats.append({
                    'url': base_url + media_url + access_token_query,
                    'format_id': remove_start(media.get('format'), 'FORMAT_'),
                    'format_note': media.get('formatTranslation'),
                    'width': int_or_none(media.get('width')),
                    'height': int_or_none(media.get('height')),
                })
        else:
            m3u8_url = f'{base_url}{video.get("hls").get("url")}{access_token_query}'
            self._set_access_cookie()
            formats = self._extract_m3u8_formats(m3u8_url, video_id)

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
            '_fragment_hook_before_dl': self._fragment_hook_before_download,
            '_test': self._fragment_hook_before_download
        }
