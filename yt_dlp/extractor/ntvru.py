from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
    unescapeHTML,
    url_or_none,
    xpath_text,
)
from ..utils.traversal import traverse_obj


class NTVRuIE(InfoExtractor):
    IE_NAME = 'ntv.ru'
    _VALID_URL = r'https?://(?:www\.)?ntv\.ru/(?:[^/#?]+/)*(?P<id>[^/?#&]+)'

    _TESTS = [{
        # JSON Api is geo restricted
        'url': 'https://www.ntv.ru/peredacha/svoya_igra/m58980/o818800',
        'md5': '818962a1b52747d446db7cd5be43e142',
        'info_dict': {
            'id': '2520563',
            'ext': 'mp4',
            'title': 'Участники: Ирина Петрова, Сергей Коновалов, Кристина Кораблина',
            'description': 'md5:fcbd21cd45238a940b95550f9e178e3e',
            'thumbnail': r're:^http://.*\.jpg',
            'duration': 2462,
            'view_count': int,
            'comment_count': int,
            'tags': ['игры и игрушки'],
            'timestamp': 1761821096,
            'upload_date': '20251030',
            'release_timestamp': 1761821096,
            'release_date': '20251030',
            'modified_timestamp': 1761821096,
            'modified_date': '20251030',
        },
    }, {
        'url': 'http://www.ntv.ru/novosti/863142/',
        'md5': 'ba7ea172a91cb83eb734cad18c10e723',
        'info_dict': {
            'id': '746000',
            'ext': 'mp4',
            'title': 'Командующий Черноморским флотом провел переговоры в штабе ВМС Украины',
            'description': 'Командующий Черноморским флотом провел переговоры в штабе ВМС Украины',
            'thumbnail': r're:^http://.*\.jpg',
            'duration': 136,
            'view_count': int,
            'comment_count': int,
            'tags': ['ВМС', 'захват', 'митинги', 'Севастополь', 'Украина'],
            'timestamp': 1395222013,
            'upload_date': '20140319',
            'release_timestamp': 1395222013,
            'release_date': '20140319',
            'modified_timestamp': 1395222013,
            'modified_date': '20140319',
        },
    }, {
        # Requires unescapeHTML
        'url': 'http://www.ntv.ru/peredacha/segodnya/m23700/o232416',
        'md5': '82dbd49b38e3af1d00df16acbeab260c',
        'info_dict': {
            'id': '747480',
            'ext': 'mp4',
            'title': '"Сегодня". 21 марта 2014 года. 16:00 ',
            'description': 'md5:bed80745ca72af557433195f51a02785',
            'thumbnail': r're:^http://.*\.jpg',
            'duration': 1496,
            'view_count': int,
            'comment_count': int,
            'tags': ['Брюссель', 'гражданство', 'ЕС', 'Крым', 'ОСАГО', 'саммит', 'санкции', 'события', 'чиновники', 'рейтинг'],
            'timestamp': 1395406951,
            'upload_date': '20140321',
            'release_timestamp': 1395406951,
            'release_date': '20140321',
            'modified_timestamp': 1395406951,
            'modified_date': '20140321',
        },
    }, {
        'url': 'https://www.ntv.ru/kino/Koma_film/m70281/o336036/video/',
        'md5': 'e9c7cde24d9d3eaed545911a04e6d4f4',
        'info_dict': {
            'id': '1126480',
            'ext': 'mp4',
            'title': 'Остросюжетный фильм "Кома"',
            'description': 'md5:e79ffd0887425a0f05a58885c408d7d8',
            'thumbnail': r're:^http://.*\.jpg',
            'duration': 5608,
            'view_count': int,
            'comment_count': int,
            'tags': ['кино'],
            'timestamp': 1432868572,
            'upload_date': '20150529',
            'release_timestamp': 1432868572,
            'release_date': '20150529',
            'modified_timestamp': 1432868572,
            'modified_date': '20150529',
        },
    }, {
        'url': 'http://www.ntv.ru/serial/Delo_vrachey/m31760/o233916/',
        'md5': '9320cd0e23f3ea59c330dc744e06ff3b',
        'info_dict': {
            'id': '751482',
            'ext': 'mp4',
            'title': '"Дело врачей": "Деревце жизни"',
            'description': 'md5:d6fbf9193f880f50d9cbfbcc954161c1',
            'thumbnail': r're:^http://.*\.jpg',
            'duration': 2590,
            'view_count': int,
            'comment_count': int,
            'tags': ['врачи', 'больницы'],
            'timestamp': 1395882300,
            'upload_date': '20140327',
            'release_timestamp': 1395882300,
            'release_date': '20140327',
            'modified_timestamp': 1395882300,
            'modified_date': '20140327',
        },
    }, {
        # Schemeless file URL
        'url': 'https://www.ntv.ru/video/1797442',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        video_id = self._html_search_regex(
            r'<meta property="ya:ovs:feed_url" content="https?://www\.ntv\.ru/(?:exp/)?video/(\d+)', webpage, 'video id')

        player = self._download_xml(
            f'http://www.ntv.ru/vi{video_id}/',
            video_id, 'Downloading video XML')

        video = player.find('./data/video')

        formats = []
        for format_id in ['', 'hi', 'webm']:
            video_url = url_or_none(xpath_text(video, f'./{format_id}file'))
            if not video_url:
                continue
            formats.append({
                'url': video_url,
                'filesize': int_or_none(xpath_text(video, f'./{format_id}size')),
            })
        hls_manifest = xpath_text(video, './playback/hls')
        if hls_manifest:
            formats.extend(self._extract_m3u8_formats(
                hls_manifest, video_id, m3u8_id='hls', fatal=False))
        dash_manifest = xpath_text(video, './playback/dash')
        if dash_manifest:
            formats.extend(self._extract_mpd_formats(
                dash_manifest, video_id, mpd_id='dash', fatal=False))

        metadata = self._download_xml(
            f'https://www.ntv.ru/exp/video/{video_id}', video_id, 'Downloading XML metadata', fatal=False)

        return {
            'id': video_id,
            'formats': formats,
            **traverse_obj(player, {
                'title': ('data/title/text()', ..., {str}, {unescapeHTML}, any),
                'description': ('data/description/text()', ..., {str}, {unescapeHTML}, any),
                'duration': ('data/video/totaltime/text()', ..., {int_or_none}, any),
                'view_count': ('data/video/views/text()', ..., {int_or_none}, any),
                'thumbnail': ('data/video/splash/text()', ..., {url_or_none}, any),
            }),
            **traverse_obj(metadata, {
                'title': ('{*}title/text()', ..., {str}, {unescapeHTML}, any),
                'description': ('{*}description/text()', ..., {str}, {unescapeHTML}, any),
                'duration': ('{*}duration/text()', ..., {int_or_none}, any),
                'timestamp': ('{*}create_date/text()', ..., {parse_iso8601}, any),
                'release_timestamp': ('{*}upload_date/text()', ..., {parse_iso8601}, any),
                'modified_timestamp': ('{*}modify_date/text()', ..., {parse_iso8601}, any),
                'tags': ('{*}tag/text()', ..., {str}, {lambda x: x.split(',')}, ..., {str.strip}, filter),
                'view_count': ('{*}stats/views_total/text()', ..., {int_or_none}, any),
                'comment_count': ('{*}stats/comments/text()', ..., {int_or_none}, any),
            }),
        }
