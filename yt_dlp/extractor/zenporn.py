import re
import math
from collections import namedtuple


from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    traverse_obj,
)


class ZenPornIE(InfoExtractor):
    IE_DESC = 'ZenPorn'
    _VALID_URL = r'https?://(?:www\.)?zenporn\.com/video/(?P<id>\d+)'
    _TESTS = [
        {
            'url': 'https://zenporn.com/video/15627016/desi-bhabi-ki-chudai',
            'md5': '07bd576b5920714d74975c054ca28dee',
            'info_dict': {
                'id': '15627016',
                'extr_id': '9563799',
                'ext': 'mp4',
                'title': 'md5:669eafd3bbc688aa29770553b738ada2',
                'description': '',
                'thumbnail': 'md5:2fc044a19bab450fef8f1931e7920a18',
                'post_date': '2023-09-25 18:28:11',
                'uploader': 'md5:9fae59847f1f58d1da8f2772016c12f3',
                'age_limit': 18
            }
        },
        {
            'url': 'https://zenporn.com/video/15570701',
            'md5': 'acba0d080d692664fcc8c4e5502b1a67',
            'info_dict': {
                'id': '15570701',
                'extr_id': '2297875',
                'ext': 'mp4',
                'title': 'md5:47aebdf87644ec91e8b1a844bc832451',
                'description': '',
                'thumbnail': 'https://tn.manysex.com/contents/videos_screenshots/2297000/2297875/480x270/1.jpg',
                'post_date': '2023-09-21 04:42:51',
                'uploader': 'Lois Clarke',
                'age_limit': 18
            }
        },
        {
            'url': 'https://zenporn.com/video/8531117/amateur-students-having-a-fuck-fest-at-club/',
            'md5': '67411256aa9451449e4d29f3be525541',
            'info_dict': {
                'id': '8531117',
                'extr_id': '12791908',
                'ext': 'mp4',
                'title': 'Amateur students having a fuck fest at club',
                'description': '',
                'thumbnail': 'https://tn.txxx.tube/contents/videos_screenshots/12791000/12791908/288x162/1.jpg',
                'post_date': '2019-10-05 12:12:34',
                'uploader': 'Jackopenass',
                'age_limit': 18
            }
        },
        {
            'url': 'https://zenporn.com/video/15872038/glad-you-came/',
            'md5': '296ccab437f5bac6099433768449d8e1',
            'info_dict': {
                'id': '15872038',
                'extr_id': '111585',
                'ext': 'mp4',
                'title': 'Glad You Came',
                'description': '',
                'thumbnail': 'https://vpim.m3pd.com/contents/videos_screenshots/111000/111585/480x270/1.jpg',
                'post_date': '2023-10-24 15:50:03',
                'uploader': 'Martin Rudenko',
                'age_limit': 18
            }
        }
    ]

    def _extract_embed_info(self, source):
        embed = namedtuple('embed', ['ext_domain', 'extr_id'])
        regex = re.compile(
            r'https:\/\/(?P<ext_domain>[\w.-]+\.\w{3})\/embed\/(?P<extr_id>\d+)\/')
        match = regex.search(source)

        if match:
            return embed(match.group('ext_domain'), match.group('extr_id'))
        else:
            return embed(None, None)

    def _gen_info_url(self, embed, lifetime=86400):
        dyn_a = int_or_none(1e6 * math.floor(int_or_none(embed.extr_id) / 1e6))
        dyn_b = int_or_none(1e3 * math.floor(int_or_none(embed.extr_id) / 1e3))
        if dyn_a is None or dyn_b is None:
            raise ExtractorError('Unable to generate the ``gen_info_url``.')

        return f'https://{embed.ext_domain}/api/json/video/{lifetime}/{dyn_a}/{dyn_b}/{embed.extr_id}.json'

    def _decode_video_url(self, ext_domain, encoded_url):
        cust_char_set = 'АВСDЕFGHIJKLМNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,~'
        decoded_url = ''
        cur_pos = 0

        # Check for characters not in the custom character set and handle errors
        if any(char not in cust_char_set for char in encoded_url):
            return None

        # Filter out characters not in the custom character set
        encoded_url = ''.join(char for char in encoded_url if char in cust_char_set)

        while cur_pos < len(encoded_url):
            o = cust_char_set.index(encoded_url[cur_pos])
            i = cust_char_set.index(encoded_url[cur_pos + 1])
            s = cust_char_set.index(encoded_url[cur_pos + 2])
            a = cust_char_set.index(encoded_url[cur_pos + 3])

            o = (o << 2) | (i >> 4)
            i = ((i & 15) << 4) | (s >> 2)
            l = ((s & 3) << 6) | a

            decoded_url += chr(o)
            if s != 64:
                decoded_url += chr(i)
            if a != 64:
                decoded_url += chr(l)

            cur_pos += 4

        return f'https://{ext_domain}{decoded_url}'

    def _real_extract(self, url):

        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        embed = self._extract_embed_info(webpage)
        if not embed.ext_domain or not embed.extr_id:
            raise ExtractorError('Unable to retrieve the ``embed`` info.')

        info_url = self._gen_info_url(embed)
        info_json = self._download_json(
            info_url, video_id, note="Downloading JSON metadata for the video info.")

        video_info_url = f'https://{embed.ext_domain}/api/videofile.php?video_id={embed.extr_id}&lifetime=8640000'
        video_json = self._download_json(
            video_info_url, video_id, note="Downloading JSON metadata for the video location.")

        encoded_url = video_json[0].get('video_url')
        if not encoded_url:
            raise ExtractorError('Unable to retrieve the ``encoded_url``.')

        download_url = self._decode_video_url(embed.ext_domain, encoded_url)
        if not download_url:
            raise ExtractorError('Unable to retrieve the ``download_url``.')

        return {
            'id': video_id,
            'extr_id': embed.extr_id,
            'ext': determine_ext(video_json[0].get('format')),
            'title': traverse_obj(info_json, ('video', 'title')),
            'description': traverse_obj(info_json, ('video', 'description')),
            'thumbnail': traverse_obj(info_json, ('video', 'thumb')),
            'post_date': traverse_obj(info_json, ('video', 'post_date')),
            'uploader': traverse_obj(info_json, ('video', 'user', 'username')),
            'url': download_url,
            'age_limit': 18
        }
