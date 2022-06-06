from .common import InfoExtractor
import base64
import json


class UporniaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?upornia\.com/videos/(?P<id>[0-9]+)/?(?P<title>.*)/?.+'
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
            # TODO more properties, either as:
            # * A value
            # * MD5 checksum; start the string with md5:
            # * A regular expression; start the string with re:
            # * Any Python type (for example int or float)
        }
    }]

    def fixcyr(self, bla):
        # https://stackoverflow.com/questions/14173421/use-string-translate-in-python-to-transliterate-cyrillic/14173535#14173535
        # used SO base but extraced clean mapping
        symbols = (u"МВАС,Е",
                   u"MBAC/E")
        tr = {ord(a): ord(b) for a, b in zip(*symbols)}
        return bla.translate(tr)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        constants = self._search_regex(r'window.constants = (.+)', webpage, 'cons')
        constants = json.loads(constants)
        lt = constants.get('query').get('lifetime')
        if len(video_id) < 7:
            dira = '0'
            dirb = video_id[:-3] + '000'
        elif len(video_id) == 7:
            dira = video_id[0] + '000000'
            dirb = video_id[:4] + '000'
        else:
            print('Not yet defined')  # TODO: throw an error - wont happen for the foreseeable future
        consturl = 'https://upornia.com/api/json/video/{}/{}/{}/{}.json'.format(lt, dira, dirb, video_id)
        more_data = self._download_json(consturl, video_id)
        title = more_data.get('video').get('title')
        description = more_data.get('video').get('description')
        thumbnail = more_data.get('video').get('thumb')
        data = self._download_json('https://upornia.com/api/videofile.php?video_id={}'.format(video_id), video_id, headers={'Referer': url})
        roman = self.fixcyr(data[0].get('video_url'))
        get_vid = base64.b64decode(roman.encode('utf-8') + b'==')
        url = 'https://upornia.com{}'.format(get_vid.decode())

        # TODO more code goes here, for example ...

        return {
            'url': url,
            'id': video_id,
            'title': title,
            'description': description,  # self._og_search_description(webpage),
            'uploader': more_data['video']['user']['username'],
            'thumbnail': thumbnail,
            # TODO more properties (see yt_dlp/extractor/common.py)
        }
