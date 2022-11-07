import base64
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_duration,
    traverse_obj,
    try_call,
    urljoin,
    variadic,
)


class TxxxBaseIE(InfoExtractor):
    # some non-standard characters are used in the base64 string
    _BASE64_CHAR_REPL_MAP = {
        '\u0405': 'S',
        '\u0406': 'I',
        '\u0408': 'J',
        '\u0410': 'A',
        '\u0412': 'B',
        '\u0415': 'E',
        '\u041a': 'K',
        '\u041c': 'M',
        '\u041d': 'H',
        '\u041e': 'O',
        '\u0420': 'P',
        '\u0421': 'C',
        '\u0425': 'X',
        ',': '/',
        '.': '+',
        '~': '=',
    }

    def _decode_base64(self, text):
        for from_char, to_char in self._BASE64_CHAR_REPL_MAP.items():
            text = text.replace(from_char, to_char)
        return base64.b64decode(text).decode('utf-8')

    def _get_format_id(self, format_id):
        return try_call(lambda: variadic(format_id)[0].lstrip('_'))


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
                         txxx\.tube|
                         upornia\.com|
                         vjav\.com|
                         vxxx\.com|
                         voyeurhit\.com|
                         voyeurhit\.tube))
                     (?:/(?:video/|videos/|video-|embed/)(?P<id>\d+)/(?P<display_id>([^/?]+)?))
                  '''
    _TESTS = [{
        'url': 'https://txxx.com/videos/16574965/digital-desire-malena-morgan/',
        'md5': 'c54e4ace54320aaf8e2a72df87859391',
        'info_dict': {
            'id': '16574965',
            'display_id': 'digital-desire-malena-morgan',
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
        'url': 'https://txxx.tube/videos/16574965/digital-desire-malena-morgan/',
        'md5': 'c54e4ace54320aaf8e2a72df87859391',
        'info_dict': {
            'id': '16574965',
            'display_id': 'digital-desire-malena-morgan',
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
            'display_id': '',
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
            'display_id': 'malena-morgan-masturbates-her-sweet',
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
            'display_id': 'gorgeous-malena-morgan-will-seduce-you-at-the-first-glance',
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
            'display_id': 'unbelievable-malena-morgan-performing-in-incredible-masturantion',
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
            'display_id': 'malena-morgan-solo',
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
            'display_id': 'malena-morgan-cam-show',
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
            'display_id': 'mimi-rogers-full-body-massage-nude-compilation',
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
            'display_id': 'twistys-malena-morgan-starring-at-dr-morgan-baller',
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
            'display_id': 'yui-hatano-in-if-yui-was-my-girlfriend2',
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
            'display_id': 'charlotte-stokely-elle-alexandra-malena-morgan-lingerie',
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
            'display_id': 'charlotte-stokely-elle-alexandra-malena-morgan-lingerie',
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
        video_id, host, display_id = self._match_valid_url(url).group('id', 'host', 'display_id')
        group_1 = str(1000 * (int(video_id) // 1000))
        group_2 = str(1000000 * (int(video_id) // 1000000))

        headers = {
            'Referer': url,
            'X-Requested-With': 'XMLHttpRequest',
        }

        video_info = self._call_api(
            f'https://{host}/api/json/video/86400/{group_2}/{group_1}/{video_id}.json',
            video_id, 'Downloading video info', headers)
        video_file = self._call_api(
            f'https://{host}/api/videofile.php?video_id={video_id}&lifetime=8640000',
            video_id, 'Downloading video file info', headers)

        formats = []
        for index, video in enumerate(video_file):
            format_id = self._get_format_id(video.get('format'))
            video_url = self._decode_base64(video.get('video_url'))
            if not video_url:
                continue
            # some hosts only return the path
            if video_url.startswith('/'):
                video_url = urljoin(f'https://{host}', video_url)
            formats.append({
                'url': video_url,
                'format_id': format_id,
                'quality': index,
            })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'display_id': display_id,
            'title': traverse_obj(video_info, ('video', 'title')),
            'uploader': traverse_obj(video_info, ('video', 'user', 'username')),
            'duration': parse_duration(traverse_obj(video_info, ('video', 'duration'))),
            'view_count': int_or_none(traverse_obj(video_info, ('video', 'statistics', 'viewed'))),
            'like_count': int_or_none(traverse_obj(video_info, ('video', 'statistics', 'likes'))),
            'dislike_count': int_or_none(traverse_obj(video_info, ('video', 'statistics', 'dislikes'))),
            'age_limit': 18,
            'formats': formats,
        }

    def _call_api(self, url, video_id, note='Downloading JSON metadata', headers=None):
        content = self._download_json(url, video_id, note=note, headers=headers)
        if 'error' in content:
            raise ExtractorError(f'Txxx said: {content["error"]}', expected=True, video_id=video_id)
        return content


class PornTopIE(TxxxBaseIE):
    _VALID_URL = r'https?://(?:www\.)?porntop\.com/video/(?P<id>\d+)/(?P<display_id>([^/?]+)?)'
    _TESTS = [{
        'url': 'https://porntop.com/video/101569/triple-threat-with-lia-lor-malena-morgan-and-dani-daniels/',
        'md5': '612ba7b3cb99455b382972948e200b08',
        'info_dict': {
            'id': '101569',
            'display_id': 'triple-threat-with-lia-lor-malena-morgan-and-dani-daniels',
            'ext': 'mp4',
            'title': 'Triple Threat With Lia Lor, Malena Morgan And Dani Daniels',
            'description': 'md5:c511b7de2d6135c14868f0e6b0940c41',
            'uploader': 'PatrickBush',
            'duration': 480,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'age_limit': 18,
        }
    }]

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).group('id', 'display_id')

        webpage = self._download_webpage(url, video_id)

        # find the VideoObject json object
        video_obj_text = self._search_regex(
            r'<script[^>]*>[^<]*schemaJson\s*=\s*(?P<json_ld>[^<]+VideoObject[^<]+)\s*;\s*var\s+script\s*=[^<]*</script>',
            webpage, 'VideoObject', group='json_ld')
        # there are javascript code within the declaration that would break json parsing
        # the statistics values look like this: parseInt("2697"). remove the parseInt() function
        video_obj_text = re.sub(r'parseInt\([^\d]+(\d+)[^\d]+\)', r'\1', video_obj_text)
        # remove the function at "duration"
        video_obj_text = re.sub(r'\(function\(duration\).*\(([^)]+)\)(\s*,\s*"thumbnailUrl")', r'\1\2', video_obj_text)
        # change single quote to double quote
        video_obj_text = video_obj_text.replace("'", '"')
        # parse the string
        video_obj = self._parse_json(video_obj_text, video_id, fatal=True)

        views = 0
        likes = 0
        dislikes = 0
        stats_obj = traverse_obj(video_obj, 'interactionStatistic', ...)
        for stat in stats_obj:
            if stat['interactionType'] == 'http://schema.org/WatchAction':
                views = stat['userInteractionCount']
            elif stat['interactionType'] == 'http://schema.org/LikeAction':
                likes = stat['userInteractionCount']
            elif stat['interactionType'] == 'http://schema.org/DislikeAction':
                dislikes = stat['userInteractionCount']

        # actual urls are in this scrambled json object
        urls_json_text = self._decode_base64(self._search_regex(
            r"window\.initPlayer\(.*}}},\s*'(?P<json_b64c>[^']+)'",
            webpage, 'json_urls', group='json_b64c'))
        video_file = self._parse_json(urls_json_text, video_id, fatal=True)

        formats = []
        for index, video in enumerate(video_file):
            format_id = self._get_format_id(video.get('format'))
            video_url = self._decode_base64(video.get('video_url'))
            if not video_url:
                continue
            if video_url.startswith('/'):
                video_url = urljoin('https://porntop.com', video_url)
            formats.append({
                'url': video_url,
                'format_id': format_id,
                'quality': index,
            })
        self._sort_formats(formats)

        return {
            'id': video_id,
            'display_id': display_id,
            'title': video_obj.get('name') or self._html_search_meta('og:title', webpage, 'title', fatal=True),
            'description': video_obj.get('description') or self._html_search_meta('description', webpage, 'description'),
            'uploader': video_obj.get('author'),
            'duration': parse_duration(video_obj.get('duration')),
            'view_count': int_or_none(views),
            'like_count': int_or_none(likes),
            'dislike_count': int_or_none(dislikes),
            'age_limit': 18,
            'formats': formats,
        }


class PornZogIE(TxxxBaseIE):
    _VALID_URL = r'https?://(?:www\.)?pornzog\.com/video/(?P<id>\d+)/'
    _TESTS = [{
        'url': 'https://pornzog.com/video/9125519/michelle-malone-dreamgirls-wild-wet-3/',
        'info_dict': {
            'id': '5119660',
            'display_id': '',
            'ext': 'mp4',
            'title': 'Michelle Malone - Dreamgirls - Wild Wet 3',
            'uploader': 'FallenAngel12',
            'duration': 402,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'age_limit': 18,
        }
    }]

    def _real_extract(self, url):
        # this host just embed videos from other hosts in the txxx network
        # so just redirect
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        new_url = self._html_search_regex(r'<iframe\s+src="([^"]*)"', webpage, 'newurl')
        return self.url_result(new_url)
