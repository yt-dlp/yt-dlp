from .common import InfoExtractor
from ..utils import traverse_obj
import base64
import json


class UporniaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?upornia\.com/videos/(?P<id>[0-9]{,7})(?:[/#?]|$)'
    _TESTS = [{
        'url': 'https://upornia.com/videos/4451197/fit-girl-with-perfect-ass-in-black-yoga-pants-fucked-and-gets-creampie/',
        'md5': 'd91eaa12f537d5092c357c174e5be5e4',
        'info_dict': {
            'id': '4451197',
            'ext': 'mp4',
            'title': 'Fit Girl With Perfect Ass In Black Yoga Pants Fucked And Gets Creampie',
            'thumbnail': r're:^https?://.*\.jpg$',
            'uploader': 'Anastasia Sorrentino',
            'description': '',
        }
    }]

    def fixcyr(self, bla):
        # the api does some obfuscation - it replaces letters in the base64 data through equivalent cyrillic letters
        # https://stackoverflow.com/questions/14173421/use-string-translate-in-python-to-transliterate-cyrillic/14173535#14173535
        # used SO base but extracted clean mapping
        symbols = (u"МВАС,Е",
                   u"MBAC/E")
        tr = {ord(a): ord(b) for a, b in zip(*symbols)}
        return bla.translate(tr)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        constants = self._search_regex(r'window.constants = (.+)', webpage, 'cons')
        constants = self._parse_json(constants, video_id)
        lifetime = traverse_obj(constants, ('query', 'lifetime'))
        api_slug = (f'0/{video_id[:-3]}000' if len(video_id) < 7
                    else f'{video_id[0]}000000/{video_id[:4]}000')
        consturl = f'https://upornia.com/api/json/video/{lifetime}/{api_slug}/{video_id}.json'
        more_data = self._download_json(consturl, video_id)
        data = self._download_json(f'https://upornia.com/api/videofile.php?video_id={video_id}', video_id, headers={'Referer': url})
        roman = self.fixcyr(data[0].get('video_url'))
        get_vid = base64.b64decode(roman.encode('utf-8') + b'==').decode()
        url = f'https://upornia.com{get_vid}'

        return {
            'url': url,
            'id': video_id,
            'title': traverse_obj(more_data, ('video', 'title')),
            'description': traverse_obj(more_data, ('video', 'description')),
            'uploader': traverse_obj(more_data, ('video', 'user', 'username')),
            'thumbnail': traverse_obj(more_data, ('video', 'thumb')),
        }
