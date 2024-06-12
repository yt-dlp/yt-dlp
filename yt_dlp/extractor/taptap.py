import re
import uuid

from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    join_nonempty,
    str_or_none,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class TapTapBaseIE(InfoExtractor):
    _X_UA = 'V=1&PN=WebApp&LANG=zh_CN&VN_CODE=102&LOC=CN&PLT=PC&DS=Android&UID={uuid}&OS=Windows&OSV=10&DT=PC'
    _VIDEO_API = 'https://www.taptap.cn/webapiv2/video-resource/v1/multi-get'
    _INFO_API = None
    _INFO_QUERY_KEY = 'id'
    _DATA_PATH = None
    _ID_PATH = None
    _META_PATH = None

    def _get_api(self, url, video_id, query, **kwargs):
        query = {**query, 'X-UA': self._X_UA.format(uuid=uuid.uuid4())}
        return self._download_json(url, video_id, query=query, **kwargs)['data']

    def _extract_video(self, video_id):
        video_data = self._get_api(self._VIDEO_API, video_id, query={'video_ids': video_id})['list'][0]

        # h265 playlist contains both h265 and h264 formats
        video_url = traverse_obj(video_data, ('play_url', ('url_h265', 'url'), {url_or_none}, any))
        formats = self._extract_m3u8_formats(video_url, video_id, fatal=False)
        for fmt in formats:
            if re.search(r'^(hev|hvc|hvt)\d', fmt.get('vcodec', '')):
                fmt['format_id'] = join_nonempty(fmt.get('format_id'), 'h265', delim='_')

        return {
            'id': str(video_id),
            'formats': formats,
            **traverse_obj(video_data, ({
                'duration': ('info', 'duration', {int_or_none}),
                'thumbnail': ('thumbnail', ('original_url', 'url'), {url_or_none}),
            }), get_all=False),
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        query = {self._INFO_QUERY_KEY: video_id}

        data = traverse_obj(
            self._get_api(self._INFO_API, video_id, query=query), self._DATA_PATH)

        metainfo = traverse_obj(data, self._META_PATH)
        entries = [{
            **metainfo,
            **self._extract_video(id_),
        } for id_ in set(traverse_obj(data, self._ID_PATH))]

        return self.playlist_result(entries, **metainfo, id=video_id)


class TapTapMomentIE(TapTapBaseIE):
    _VALID_URL = r'https?://www\.taptap\.cn/moment/(?P<id>\d+)'
    _INFO_API = 'https://www.taptap.cn/webapiv2/moment/v3/detail'
    _ID_PATH = ('moment', 'topic', (('videos', ...), 'pin_video'), 'video_id')
    _META_PATH = ('moment', {
        'timestamp': ('created_time', {int_or_none}),
        'modified_timestamp': ('edited_time', {int_or_none}),
        'uploader': ('author', 'user', 'name', {str}),
        'uploader_id': ('author', 'user', 'id', {int}, {str_or_none}),
        'title': ('topic', 'title', {str}),
        'description': ('topic', 'summary', {str}),
    })
    _TESTS = [{
        'url': 'https://www.taptap.cn/moment/194618230982052443',
        'info_dict': {
            'id': '194618230982052443',
            'title': '《崩坏3》开放世界「后崩坏书」新篇章 于淹没之地仰视辰星',
            'description': 'md5:cf66f7819d413641b8b28c8543f4ecda',
            'timestamp': 1633453402,
            'upload_date': '20211005',
            'modified_timestamp': 1633453402,
            'modified_date': '20211005',
            'uploader': '乌酱',
            'uploader_id': '532896',
        },
        'playlist_count': 1,
        'playlist': [{
            'info_dict': {
                'id': '2202584',
                'ext': 'mp4',
                'title': '《崩坏3》开放世界「后崩坏书」新篇章 于淹没之地仰视辰星',
                'description': 'md5:cf66f7819d413641b8b28c8543f4ecda',
                'duration': 66,
                'timestamp': 1633453402,
                'upload_date': '20211005',
                'modified_timestamp': 1633453402,
                'modified_date': '20211005',
                'uploader': '乌酱',
                'uploader_id': '532896',
                'thumbnail': r're:^https?://.*\.(png|jpg)',
            },
        }],
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.taptap.cn/moment/521630629209573493',
        'info_dict': {
            'id': '521630629209573493',
            'title': '《崩坏：星穹铁道》黄泉角色PV——「你的颜色」',
            'description': 'md5:2c81245da864428c904d53ae4ad2182b',
            'timestamp': 1711425600,
            'upload_date': '20240326',
            'modified_timestamp': 1711425600,
            'modified_date': '20240326',
            'uploader': '崩坏：星穹铁道',
            'uploader_id': '414732580',
        },
        'playlist_count': 1,
        'playlist': [{
            'info_dict': {
                'id': '4006511',
                'ext': 'mp4',
                'title': '《崩坏：星穹铁道》黄泉角色PV——「你的颜色」',
                'description': 'md5:2c81245da864428c904d53ae4ad2182b',
                'duration': 173,
                'timestamp': 1711425600,
                'upload_date': '20240326',
                'modified_timestamp': 1711425600,
                'modified_date': '20240326',
                'uploader': '崩坏：星穹铁道',
                'uploader_id': '414732580',
                'thumbnail': r're:^https?://.*\.(png|jpg)',
            },
        }],
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.taptap.cn/moment/540493587511511299',
        'playlist_count': 2,
        'info_dict': {
            'id': '540493587511511299',
            'title': '中式民俗解谜《纸嫁衣7》、新系列《纸不语》公布！',
            'description': 'md5:d60842350e686ddb242291ddfb8e39c9',
            'timestamp': 1715920200,
            'upload_date': '20240517',
            'modified_timestamp': 1715942225,
            'modified_date': '20240517',
            'uploader': 'TapTap 编辑',
            'uploader_id': '7159244',
        },
        'params': {'skip_download': 'm3u8'},
    }]


class TapTapAppIE(TapTapBaseIE):
    _VALID_URL = r'https?://www\.taptap\.cn/app/(?P<id>\d+)'
    _INFO_API = 'https://www.taptap.cn/webapiv2/app/v4/detail'
    _ID_PATH = (('app_videos', 'videos'), ..., 'video_id')
    _META_PATH = {
        'title': ('title', {str}),
        'description': ('description', 'text', {str}, {clean_html}),
    }
    _TESTS = [{
        'url': 'https://www.taptap.cn/app/168332',
        'info_dict': {
            'id': '168332',
            'title': '原神',
            'description': 'md5:e345f39a5fea5de2a46923f70d5f76ab',
        },
        'playlist_count': 2,
        'playlist': [{
            'info_dict': {
                'id': '4058443',
                'ext': 'mp4',
                'title': '原神',
                'description': 'md5:e345f39a5fea5de2a46923f70d5f76ab',
                'duration': 26,
                'thumbnail': r're:^https?://.*\.(png|jpg)',
            },
        }, {
            'info_dict': {
                'id': '4058462',
                'ext': 'mp4',
                'title': '原神',
                'description': 'md5:e345f39a5fea5de2a46923f70d5f76ab',
                'duration': 295,
                'thumbnail': r're:^https?://.*\.(png|jpg)',
            },
        }],
        'params': {'skip_download': 'm3u8'},
    }]


class TapTapIntlBase(TapTapBaseIE):
    _X_UA = 'V=1&PN=WebAppIntl2&LANG=zh_TW&VN_CODE=115&VN=0.1.0&LOC=CN&PLT=PC&DS=Android&UID={uuid}&CURR=&DT=PC&OS=Windows&OSV=NT%208.0.0'
    _VIDEO_API = 'https://www.taptap.io/webapiv2/video-resource/v1/multi-get'


class TapTapAppIntlIE(TapTapIntlBase):
    _VALID_URL = r'https?://www\.taptap\.io/app/(?P<id>\d+)'
    _INFO_API = 'https://www.taptap.io/webapiv2/i/app/v5/detail'
    _DATA_PATH = 'app'
    _ID_PATH = (('app_videos', 'videos'), ..., 'video_id')
    _META_PATH = {
        'title': ('title', {str}),
        'description': ('description', 'text', {str}, {clean_html}),
    }
    _TESTS = [{
        'url': 'https://www.taptap.io/app/233287',
        'info_dict': {
            'id': '233287',
            'title': '《虹彩六號 M》',
            'description': 'md5:418285f9c15347fc3cf3e3a3c649f182',
        },
        'playlist_count': 1,
        'playlist': [{
            'info_dict': {
                'id': '2149708997',
                'ext': 'mp4',
                'title': '《虹彩六號 M》',
                'description': 'md5:418285f9c15347fc3cf3e3a3c649f182',
                'duration': 78,
                'thumbnail': r're:^https?://.*\.(png|jpg)',
            },
        }],
        'params': {'skip_download': 'm3u8'},
    }]


class TapTapPostIntlIE(TapTapIntlBase):
    _VALID_URL = r'https?://www\.taptap\.io/post/(?P<id>\d+)'
    _INFO_API = 'https://www.taptap.io/webapiv2/creation/post/v1/detail'
    _INFO_QUERY_KEY = 'id_str'
    _DATA_PATH = 'post'
    _ID_PATH = ((('videos', ...), 'pin_video'), 'video_id')
    _META_PATH = {
        'timestamp': ('published_time', {int_or_none}),
        'modified_timestamp': ('edited_time', {int_or_none}),
        'uploader': ('user', 'name', {str}),
        'uploader_id': ('user', 'id', {int}, {str_or_none}),
        'title': ('title', {str}),
        'description': ('list_fields', 'summary', {str}),
    }
    _TESTS = [{
        'url': 'https://www.taptap.io/post/571785',
        'info_dict': {
            'id': '571785',
            'title': 'Arknights x Rainbow Six Siege | Event PV',
            'description': 'md5:f7717c13f6d3108e22db7303e6690bf7',
            'timestamp': 1614664951,
            'upload_date': '20210302',
            'modified_timestamp': 1614664951,
            'modified_date': '20210302',
            'uploader': 'TapTap Editor',
            'uploader_id': '80224473',
        },
        'playlist_count': 1,
        'playlist': [{
            'info_dict': {
                'id': '2149491903',
                'ext': 'mp4',
                'title': 'Arknights x Rainbow Six Siege | Event PV',
                'description': 'md5:f7717c13f6d3108e22db7303e6690bf7',
                'duration': 122,
                'timestamp': 1614664951,
                'upload_date': '20210302',
                'modified_timestamp': 1614664951,
                'modified_date': '20210302',
                'uploader': 'TapTap Editor',
                'uploader_id': '80224473',
                'thumbnail': r're:^https?://.*\.(png|jpg)',
            },
        }],
        'params': {'skip_download': 'm3u8'},
    }]
