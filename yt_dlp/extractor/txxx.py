import base64

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_duration,
    qualities,
)


class TxxxBaseIE(InfoExtractor):
    # some non-standard characters are used in the base64 string
    _BASE64_CHAR_REPL_MAP = {
        "\u0405": "S",
        "\u0406": "I",
        "\u0408": "J",
        "\u0410": "A",
        "\u0412": "B",
        "\u0415": "E",
        "\u041a": "K",
        "\u041c": "M",
        "\u041d": "H",
        "\u041e": "O",
        "\u0420": "P",
        "\u0421": "C",
        "\u0425": "X",
        ",": "/",
        ".": "+",
        "~": "=",
    }

    def _decode_base64(self, text):
        for from_char, to_char in self._BASE64_CHAR_REPL_MAP.items():
            text = text.replace(from_char, to_char)
        return base64.b64decode(text).decode('utf-8')

    def _get_format_id(self, format_id):
        if not format_id:
            return None
        elif isinstance(format_id, list):
            return '' if len(format_id) == 0 else format_id[0].lstrip('_')
        else:
            return format_id.lstrip('_')


class TxxxIE(TxxxBaseIE):
    _VALID_URL = r'''(?x)
                     https?://
                     (?:(?:www\.)?(?P<host>
                     hclips\.com|
                     hdzog\.com|
                     hotmovs\.com|
                     inporn\.com|
                     privatehomeclips\.com|
                     tubepornclassic\.com|
                     txxx\.com|
                     upornia\.com|
                     vjav\.com|
                     vxxx\.com|
                     voyeurhit\.com|
                     voyeurhit\.tube))
                     (?:/(?:video/|videos/|video-|embed/)(?P<id>[^/]+)/)
                  '''
    _TESTS = [{
        'url': 'https://txxx.com/videos/16574965/digital-desire-malena-morgan/',
        'md5': 'c54e4ace54320aaf8e2a72df87859391',
        'info_dict': {
            'id': '16574965',
            'ext': 'mp4',
            'title': 'Digital Desire - Malena Morgan',
            'uploader': 'Lois Argentum',
            'duration': 694,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'age_limit': 18,
        }
    }, {
        'url': 'https://vxxx.com/video-68925/',
        'md5': '1fcff3748b0c5b41fe41d0afa22409e1',
        'info_dict': {
            'id': '68925',
            'ext': 'mp4',
            'title': 'Malena Morgan',
            'uploader': 'Huge Hughes',
            'duration': 694,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'age_limit': 18,
        }
    }, {
        'url': 'https://hclips.com/videos/6291073/malena-morgan-masturbates-her-sweet/',
        'md5': 'a5dd4f83363972ee043313cff85e7e26',
        'info_dict': {
            'id': '6291073',
            'ext': 'mp4',
            'title': 'Malena Morgan masturbates her sweet',
            'uploader': 'John Salt',
            'duration': 426,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'age_limit': 18,
        }
    }, {
        'url': 'https://hdzog.com/videos/67063/gorgeous-malena-morgan-will-seduce-you-at-the-first-glance/',
        'md5': 'f8bdedafd45d1ec2875c43fe33a846d3',
        'info_dict': {
            'id': '67063',
            'ext': 'mp4',
            'title': 'Gorgeous Malena Morgan will seduce you at the first glance',
            'uploader': 'momlesson',
            'duration': 601,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'age_limit': 18,
        }
    }, {
        'url': 'https://hotmovs.com/videos/8789287/unbelievable-malena-morgan-performing-in-incredible-masturantion/',
        'md5': '71d32c51584876472db87e561171a386',
        'info_dict': {
            'id': '8789287',
            'ext': 'mp4',
            'title': 'Unbelievable Malena Morgan performing in incredible masturantion',
            'uploader': 'Davit Sanchez',
            'duration': 940,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'age_limit': 18,
        }
    }, {
        'url': 'https://inporn.com/video/517897/malena-morgan-solo/',
        'md5': '344db467481edf78f193cdf5820a7cfb',
        'info_dict': {
            'id': '517897',
            'ext': 'mp4',
            'title': 'Malena Morgan - Solo',
            'uploader': 'Ashley Oxy',
            'duration': 480,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'age_limit': 18,
        }
    }, {
        'url': 'https://privatehomeclips.com/videos/3630599/malena-morgan-cam-show/',
        'md5': 'ea657273e352493c5fb6357fbfa4f126',
        'info_dict': {
            'id': '3630599',
            'ext': 'mp4',
            'title': 'malena morgan cam show',
            'uploader': 'Member9915',
            'duration': 290,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'age_limit': 18,
        }
    }, {
        'url': 'https://tubepornclassic.com/videos/1015455/mimi-rogers-full-body-massage-nude-compilation/',
        'md5': '2e9a6cf610c9862e86e0ce24f08f4427',
        'info_dict': {
            'id': '1015455',
            'ext': 'mp4',
            'title': 'Mimi Rogers - Full Body Massage (Nude) compilation',
            'uploader': '88bhuto',
            'duration': 286,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'age_limit': 18,
        }
    }, {
        'url': 'https://upornia.com/videos/1498858/twistys-malena-morgan-starring-at-dr-morgan-baller/',
        'md5': '7ff7033340bc88a173198b7c22600e4f',
        'info_dict': {
            'id': '1498858',
            'ext': 'mp4',
            'title': 'Twistys - Malena Morgan starring at Dr. Morgan-Baller',
            'uploader': 'mindgeek',
            'duration': 480,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'age_limit': 18,
        }
    }, {
        'url': 'https://vjav.com/videos/11761/yui-hatano-in-if-yui-was-my-girlfriend2/',
        'md5': '6de5bc1f13bdfc3491a77f23edb1676f',
        'info_dict': {
            'id': '11761',
            'ext': 'mp4',
            'title': 'Yui Hatano in If Yui Was My Girlfriend',
            'uploader': 'Matheus69',
            'duration': 3310,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'age_limit': 18,
        }
    }, {
        'url': 'https://voyeurhit.com/videos/332875/charlotte-stokely-elle-alexandra-malena-morgan-lingerie/',
        'md5': '12b4666e9c3e60dafe9182e5d12aae33',
        'info_dict': {
            'id': '332875',
            'ext': 'mp4',
            'title': 'Charlotte Stokely, Elle Alexandra, Malena Morgan-Lingerie',
            'uploader': 'Kyle Roberts',
            'duration': 655,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'age_limit': 18,
        }
    }, {
        'url': 'https://voyeurhit.tube/videos/332875/charlotte-stokely-elle-alexandra-malena-morgan-lingerie/',
        'md5': '12b4666e9c3e60dafe9182e5d12aae33',
        'info_dict': {
            'id': '332875',
            'ext': 'mp4',
            'title': 'Charlotte Stokely, Elle Alexandra, Malena Morgan-Lingerie',
            'uploader': 'Kyle Roberts',
            'duration': 655,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'age_limit': 18,
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        group_1 = 0 if not video_id[:-3] else video_id[:-3] + '000'
        group_2 = 0 if not video_id[:-6] else video_id[:-6] + '000000'
        host = self._match_valid_url(url).group('host')
        video_info_url = 'https://%s/api/json/video/86400/%s/%s/%s.json' % (host, group_2, group_1, video_id)
        video_path_url = 'https://%s/api/videofile.php?video_id=%s&lifetime=8640000' % (host, video_id)

        headers = {
            'Referer': url,
            'X-Requested-With': 'XMLHttpRequest',
        }

        video_info = self._download_json(video_info_url, video_id, 'Downloading video info', headers=headers)
        if 'error' in video_info:
            raise ExtractorError(f'Txxx said: {video_info["error"]}', expected=True, video_id=video_id)

        video_file = self._download_json(video_path_url, video_id, 'Downloading video file info', headers=headers)
        if 'error' in video_file:
            raise ExtractorError(f'Txxx said: {video_file["error"]}', expected=True, video_id=video_id)

        video_json = video_info.get('video')
        stat_json = video_json.get('statistics')
        user_json = video_json.get('user')

        formats = []
        for video in video_file:
            format_id = self._get_format_id(video.get('format'))
            formats.append(format_id)
        quality = qualities(formats)

        formats = []
        for video in video_file:
            format_id = self._get_format_id(video.get('format'))
            video_url = self._decode_base64(video.get('video_url'))
            if not video_url:
                continue
            # some hosts only return the path
            if video_url.startswith('/'):
                video_url = 'https://%s%s' % (host, video_url)
            formats.append({
                'url': video_url,
                'format_id': format_id,
                'quality': quality(format_id),
            })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': video_json.get('title'),
            'uploader': user_json.get('username'),
            'duration': parse_duration(video_json.get('duration')),
            'view_count': int_or_none(stat_json.get('viewed')),
            'like_count': int_or_none(stat_json.get('likes')),
            'dislike_count': int_or_none(stat_json.get('dislikes')),
            'age_limit': 18,
            'formats': formats,
        }
