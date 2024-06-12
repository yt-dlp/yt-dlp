import base64
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    js_to_json,
    merge_dicts,
    parse_duration,
    traverse_obj,
    try_call,
    url_or_none,
    urljoin,
    variadic,
)


def decode_base64(text):
    return base64.b64decode(text.translate(text.maketrans({
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
    }))).decode()


def get_formats(host, video_file):
    return [{
        'url': urljoin(f'https://{host}', decode_base64(video['video_url'])),
        'format_id': try_call(lambda: variadic(video['format'])[0].lstrip('_')),
        'quality': index,
    } for index, video in enumerate(video_file) if video.get('video_url')]


class TxxxIE(InfoExtractor):
    _DOMAINS = (
        'hclips.com',
        'hdzog.com',
        'hdzog.tube',
        'hotmovs.com',
        'hotmovs.tube',
        'inporn.com',
        'privatehomeclips.com',
        'tubepornclassic.com',
        'txxx.com',
        'txxx.tube',
        'upornia.com',
        'upornia.tube',
        'vjav.com',
        'vjav.tube',
        'vxxx.com',
        'voyeurhit.com',
        'voyeurhit.tube',
    )
    _VALID_URL = rf'''(?x)
        https?://(?:www\.)?(?P<host>{"|".join(map(re.escape, _DOMAINS))})/
        (?:videos?[/-]|embed/)(?P<id>\d+)(?:/(?P<display_id>[^/?#]+))?
    '''
    _EMBED_REGEX = [rf'<iframe[^>]+?src=(["\'])(?P<url>(?:https?:)?//(?:www\.)?(?:{"|".join(map(re.escape, _DOMAINS))})/embed/[^"\']*)\1']
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
            'thumbnail': 'https://tn.txxx.tube/contents/videos_sources/16574000/16574965/screenshots/1.jpg',
        },
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
            'thumbnail': 'https://tn.txxx.tube/contents/videos_sources/16574000/16574965/screenshots/1.jpg',
        },
    }, {
        'url': 'https://vxxx.com/video-68925/',
        'md5': '1fcff3748b0c5b41fe41d0afa22409e1',
        'info_dict': {
            'id': '68925',
            'display_id': '68925',
            'ext': 'mp4',
            'title': 'Malena Morgan',
            'uploader': 'Huge Hughes',
            'duration': 694,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'age_limit': 18,
            'thumbnail': 'https://tn.vxxx.com/contents/videos_sources/68000/68925/screenshots/1.jpg',
        },
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
            'thumbnail': 'https://hctn.nv7s.com/contents/videos_sources/6291000/6291073/screenshots/1.jpg',
        },
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
            'thumbnail': 'https://tn.hdzog.com/contents/videos_sources/67000/67063/screenshots/1.jpg',
        },
    }, {
        'url': 'https://hdzog.tube/videos/67063/gorgeous-malena-morgan-will-seduce-you-at-the-first-glance/',
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
            'thumbnail': 'https://tn.hdzog.com/contents/videos_sources/67000/67063/screenshots/1.jpg',
        },
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
            'thumbnail': 'https://tn.hotmovs.com/contents/videos_sources/8789000/8789287/screenshots/10.jpg',
        },
    }, {
        'url': 'https://hotmovs.tube/videos/8789287/unbelievable-malena-morgan-performing-in-incredible-masturantion/',
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
            'thumbnail': 'https://tn.hotmovs.com/contents/videos_sources/8789000/8789287/screenshots/10.jpg',
        },
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
            'thumbnail': 'https://iptn.m3pd.com/media/tn/sources/517897_1.jpg',
        },
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
            'thumbnail': 'https://hctn.nv7s.com/contents/videos_sources/3630000/3630599/screenshots/15.jpg',
        },
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
            'thumbnail': 'https://tn.tubepornclassic.com/contents/videos_sources/1015000/1015455/screenshots/6.jpg',
        },
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
            'thumbnail': 'https://tn.upornia.com/contents/videos_sources/1498000/1498858/screenshots/1.jpg',
        },
    }, {
        'url': 'https://upornia.tube/videos/1498858/twistys-malena-morgan-starring-at-dr-morgan-baller/',
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
            'thumbnail': 'https://tn.upornia.com/contents/videos_sources/1498000/1498858/screenshots/1.jpg',
        },
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
            'thumbnail': 'https://tn.vjav.com/contents/videos_sources/11000/11761/screenshots/23.jpg',
        },
    }, {
        'url': 'https://vjav.tube/videos/11761/yui-hatano-in-if-yui-was-my-girlfriend2/',
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
            'thumbnail': 'https://tn.vjav.com/contents/videos_sources/11000/11761/screenshots/23.jpg',
        },
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
            'thumbnail': 'https://tn.voyeurhit.com/contents/videos_sources/332000/332875/screenshots/1.jpg',
        },
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
            'thumbnail': 'https://tn.voyeurhit.com/contents/videos_sources/332000/332875/screenshots/1.jpg',
        },
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://pornzog.com/video/9125519/michelle-malone-dreamgirls-wild-wet-3/',
        'info_dict': {
            'id': '5119660',
            'display_id': '5119660',
            'ext': 'mp4',
            'title': 'Michelle Malone - Dreamgirls - Wild Wet 3',
            'uploader': 'FallenAngel12',
            'duration': 402,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'age_limit': 18,
            'thumbnail': 'https://hctn.nv7s.com/contents/videos_sources/5119000/5119660/screenshots/1.jpg',
        },
    }]

    def _call_api(self, url, video_id, fatal=False, **kwargs):
        content = self._download_json(url, video_id, fatal=fatal, **kwargs)
        if traverse_obj(content, 'error'):
            raise self._error_or_warning(ExtractorError(
                f'Txxx said: {content["error"]}', expected=True), fatal=fatal)
        return content or {}

    def _real_extract(self, url):
        video_id, host, display_id = self._match_valid_url(url).group('id', 'host', 'display_id')
        headers = {'Referer': url, 'X-Requested-With': 'XMLHttpRequest'}

        video_file = self._call_api(
            f'https://{host}/api/videofile.php?video_id={video_id}&lifetime=8640000',
            video_id, fatal=True, note='Downloading video file info', headers=headers)

        slug = f'{int(1E6 * (int(video_id) // 1E6))}/{1000 * (int(video_id) // 1000)}'
        video_info = self._call_api(
            f'https://{host}/api/json/video/86400/{slug}/{video_id}.json',
            video_id, note='Downloading video info', headers=headers)

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
            'thumbnail': traverse_obj(video_info, ('video', 'thumbsrc', {url_or_none})),
            'formats': get_formats(host, video_file),
        }


class PornTopIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<host>(?:www\.)?porntop\.com)/video/(?P<id>\d+)(?:/(?P<display_id>[^/?]+))?'
    _TESTS = [{
        'url': 'https://porntop.com/video/101569/triple-threat-with-lia-lor-malena-morgan-and-dani-daniels/',
        'md5': '612ba7b3cb99455b382972948e200b08',
        'info_dict': {
            'id': '101569',
            'display_id': 'triple-threat-with-lia-lor-malena-morgan-and-dani-daniels',
            'ext': 'mp4',
            'title': 'Triple Threat With Lia Lor, Malena Morgan And Dani Daniels',
            'description': 'md5:285357d9d3a00ce5acb29f39f826dbf6',
            'uploader': 'PatrickBush',
            'duration': 480,
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'age_limit': 18,
            'timestamp': 1609455029,
            'upload_date': '20201231',
            'thumbnail': 'https://tn.porntop.com/media/tn/sources/101569_1.jpg',
        },
    }]

    def _real_extract(self, url):
        video_id, host, display_id = self._match_valid_url(url).group('id', 'host', 'display_id')
        webpage = self._download_webpage(url, video_id)

        json_ld = self._json_ld(self._search_json(
            r'\bschemaJson\s*=', webpage, 'JSON-LD', video_id, transform_source=js_to_json,
            contains_pattern='{[^<]+?VideoObject[^<]+};'), video_id, fatal=True)

        video_file = self._parse_json(decode_base64(self._search_regex(
            r"window\.initPlayer\(.*}}},\s*'(?P<json_b64c>[^']+)'",
            webpage, 'json_urls', group='json_b64c')), video_id)

        return merge_dicts({
            'id': video_id,
            'display_id': display_id,
            'age_limit': 18,
            'formats': get_formats(host, video_file),
        }, json_ld)
