import itertools

from .common import InfoExtractor
from ..compat import (
    compat_urllib_parse_unquote,
)
from ..utils import parse_qs


class DaumBaseIE(InfoExtractor):
    _KAKAO_EMBED_BASE = 'http://tv.kakao.com/embed/player/cliplink/'


class DaumIE(DaumBaseIE):
    _VALID_URL = r'https?://(?:(?:m\.)?tvpot\.daum\.net/v/|videofarm\.daum\.net/controller/player/VodPlayer\.swf\?vid=)(?P<id>[^?#&]+)'
    IE_NAME = 'daum.net'

    _TESTS = [{
        'url': 'http://tvpot.daum.net/v/vab4dyeDBysyBssyukBUjBz',
        'info_dict': {
            'id': 'vab4dyeDBysyBssyukBUjBz',
            'ext': 'mp4',
            'title': '마크 헌트 vs 안토니오 실바',
            'description': 'Mark Hunt vs Antonio Silva',
            'upload_date': '20131217',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'duration': 2117,
            'view_count': int,
            'comment_count': int,
            'uploader_id': '186139',
            'uploader': '콘간지',
            'timestamp': 1387310323,
        },
    }, {
        'url': 'http://m.tvpot.daum.net/v/65139429',
        'info_dict': {
            'id': '65139429',
            'ext': 'mp4',
            'title': '1297회, \'아빠 아들로 태어나길 잘 했어\' 민수, 감동의 눈물[아빠 어디가] 20150118',
            'description': 'md5:79794514261164ff27e36a21ad229fc5',
            'upload_date': '20150118',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'duration': 154,
            'view_count': int,
            'comment_count': int,
            'uploader': 'MBC 예능',
            'uploader_id': '132251',
            'timestamp': 1421604228,
        },
    }, {
        'url': 'http://tvpot.daum.net/v/07dXWRka62Y%24',
        'only_matching': True,
    }, {
        'url': 'http://videofarm.daum.net/controller/player/VodPlayer.swf?vid=vwIpVpCQsT8%24&ref=',
        'info_dict': {
            'id': 'vwIpVpCQsT8$',
            'ext': 'flv',
            'title': '01-Korean War ( Trouble on the horizon )',
            'description': 'Korean War 01\r\nTrouble on the horizon\r\n전쟁의 먹구름',
            'upload_date': '20080223',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'duration': 249,
            'view_count': int,
            'comment_count': int,
            'uploader': '까칠한 墮落始祖 황비홍님의',
            'uploader_id': '560824',
            'timestamp': 1203770745,
        },
    }, {
        # Requires dte_type=WEB (#9972)
        'url': 'http://tvpot.daum.net/v/s3794Uf1NZeZ1qMpGpeqeRU',
        'md5': 'a8917742069a4dd442516b86e7d66529',
        'info_dict': {
            'id': 's3794Uf1NZeZ1qMpGpeqeRU',
            'ext': 'mp4',
            'title': '러블리즈 - Destiny (나의 지구) (Lovelyz - Destiny)',
            'description': '러블리즈 - Destiny (나의 지구) (Lovelyz - Destiny)\r\n\r\n[쇼! 음악중심] 20160611, 507회',
            'upload_date': '20170129',
            'uploader': '쇼! 음악중심',
            'uploader_id': '2653210',
            'timestamp': 1485684628,
        },
    }]

    def _real_extract(self, url):
        video_id = compat_urllib_parse_unquote(self._match_id(url))
        if not video_id.isdigit():
            video_id += '@my'
        return self.url_result(
            self._KAKAO_EMBED_BASE + video_id, 'Kakao', video_id)


class DaumClipIE(DaumBaseIE):
    _VALID_URL = r'https?://(?:m\.)?tvpot\.daum\.net/(?:clip/ClipView.(?:do|tv)|mypot/View.do)\?.*?clipid=(?P<id>\d+)'
    IE_NAME = 'daum.net:clip'
    _URL_TEMPLATE = 'http://tvpot.daum.net/clip/ClipView.do?clipid=%s'

    _TESTS = [{
        'url': 'http://tvpot.daum.net/clip/ClipView.do?clipid=52554690',
        'info_dict': {
            'id': '52554690',
            'ext': 'mp4',
            'title': 'DOTA 2GETHER 시즌2 6회 - 2부',
            'description': 'DOTA 2GETHER 시즌2 6회 - 2부',
            'upload_date': '20130831',
            'thumbnail': r're:^https?://.*\.(?:jpg|png)',
            'duration': 3868,
            'view_count': int,
            'uploader': 'GOMeXP',
            'uploader_id': '6667',
            'timestamp': 1377911092,
        },
    }, {
        'url': 'http://m.tvpot.daum.net/clip/ClipView.tv?clipid=54999425',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if DaumPlaylistIE.suitable(url) or DaumUserIE.suitable(url) else super(DaumClipIE, cls).suitable(url)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(
            self._KAKAO_EMBED_BASE + video_id, 'Kakao', video_id)


class DaumListIE(InfoExtractor):  # XXX: Conventionally, base classes should end with BaseIE/InfoExtractor
    def _get_entries(self, list_id, list_id_type):
        name = None
        entries = []
        for pagenum in itertools.count(1):
            list_info = self._download_json(
                'http://tvpot.daum.net/mypot/json/GetClipInfo.do?size=48&init=true&order=date&page=%d&%s=%s' % (
                    pagenum, list_id_type, list_id), list_id, 'Downloading list info - %s' % pagenum)

            entries.extend([
                self.url_result(
                    'http://tvpot.daum.net/v/%s' % clip['vid'])
                for clip in list_info['clip_list']
            ])

            if not name:
                name = list_info.get('playlist_bean', {}).get('name') or \
                    list_info.get('potInfo', {}).get('name')

            if not list_info.get('has_more'):
                break

        return name, entries

    def _check_clip(self, url, list_id):
        query_dict = parse_qs(url)
        if 'clipid' in query_dict:
            clip_id = query_dict['clipid'][0]
            if not self._yes_playlist(list_id, clip_id):
                return self.url_result(DaumClipIE._URL_TEMPLATE % clip_id, 'DaumClip')


class DaumPlaylistIE(DaumListIE):
    _VALID_URL = r'https?://(?:m\.)?tvpot\.daum\.net/mypot/(?:View\.do|Top\.tv)\?.*?playlistid=(?P<id>[0-9]+)'
    IE_NAME = 'daum.net:playlist'
    _URL_TEMPLATE = 'http://tvpot.daum.net/mypot/View.do?playlistid=%s'

    _TESTS = [{
        'note': 'Playlist url with clipid',
        'url': 'http://tvpot.daum.net/mypot/View.do?playlistid=6213966&clipid=73806844',
        'info_dict': {
            'id': '6213966',
            'title': 'Woorissica Official',
        },
        'playlist_mincount': 181
    }, {
        'note': 'Playlist url with clipid - noplaylist',
        'url': 'http://tvpot.daum.net/mypot/View.do?playlistid=6213966&clipid=73806844',
        'info_dict': {
            'id': '73806844',
            'ext': 'mp4',
            'title': '151017 Airport',
            'upload_date': '20160117',
        },
        'params': {
            'noplaylist': True,
            'skip_download': True,
        }
    }]

    @classmethod
    def suitable(cls, url):
        return False if DaumUserIE.suitable(url) else super(DaumPlaylistIE, cls).suitable(url)

    def _real_extract(self, url):
        list_id = self._match_id(url)

        clip_result = self._check_clip(url, list_id)
        if clip_result:
            return clip_result

        name, entries = self._get_entries(list_id, 'playlistid')

        return self.playlist_result(entries, list_id, name)


class DaumUserIE(DaumListIE):
    _VALID_URL = r'https?://(?:m\.)?tvpot\.daum\.net/mypot/(?:View|Top)\.(?:do|tv)\?.*?ownerid=(?P<id>[0-9a-zA-Z]+)'
    IE_NAME = 'daum.net:user'

    _TESTS = [{
        'url': 'http://tvpot.daum.net/mypot/View.do?ownerid=o2scDLIVbHc0',
        'info_dict': {
            'id': 'o2scDLIVbHc0',
            'title': '마이 리틀 텔레비전',
        },
        'playlist_mincount': 213
    }, {
        'url': 'http://tvpot.daum.net/mypot/View.do?ownerid=o2scDLIVbHc0&clipid=73801156',
        'info_dict': {
            'id': '73801156',
            'ext': 'mp4',
            'title': '[미공개] 김구라, 오만석이 부릅니다 \'오케피\' - 마이 리틀 텔레비전 20160116',
            'upload_date': '20160117',
            'description': 'md5:5e91d2d6747f53575badd24bd62b9f36'
        },
        'params': {
            'noplaylist': True,
            'skip_download': True,
        }
    }, {
        'note': 'Playlist url has ownerid and playlistid, playlistid takes precedence',
        'url': 'http://tvpot.daum.net/mypot/View.do?ownerid=o2scDLIVbHc0&playlistid=6196631',
        'info_dict': {
            'id': '6196631',
            'title': '마이 리틀 텔레비전 - 20160109',
        },
        'playlist_count': 11
    }, {
        'url': 'http://tvpot.daum.net/mypot/Top.do?ownerid=o2scDLIVbHc0',
        'only_matching': True,
    }, {
        'url': 'http://m.tvpot.daum.net/mypot/Top.tv?ownerid=45x1okb1If50&playlistid=3569733',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        list_id = self._match_id(url)

        clip_result = self._check_clip(url, list_id)
        if clip_result:
            return clip_result

        query_dict = parse_qs(url)
        if 'playlistid' in query_dict:
            playlist_id = query_dict['playlistid'][0]
            return self.url_result(DaumPlaylistIE._URL_TEMPLATE % playlist_id, 'DaumPlaylist')

        name, entries = self._get_entries(list_id, 'ownerid')

        return self.playlist_result(entries, list_id, name)
