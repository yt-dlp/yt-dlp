from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    parse_qs,
    str_or_none,
    traverse_obj,
    url_or_none,
)


class TapTapIE(InfoExtractor):
    _VALID_URL = r'https?://www\.taptap\.cn/(?P<section>moment|app)/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.taptap.cn/moment/194618230982052443',
        'info_dict': {
            'id': 'moment_194618230982052443',
            'title': '《崩坏3》开放世界「后崩坏书」新篇章 于淹没之地仰视辰星',
            'description': 'md5:cf66f7819d413641b8b28c8543f4ecda',
            'timestamp': 1633453402,
            'upload_date': '20211005',
            'uploader': '乌酱',
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
                'uploader': '乌酱',
                'thumbnail': r're:^https?://.*\.(png|jpg)',
            }
        }]
    }, {
        'url': 'https://www.taptap.cn/moment/521630629209573493',
        'info_dict': {
            'id': 'moment_521630629209573493',
            'title': '《崩坏：星穹铁道》黄泉角色PV——「你的颜色」',
            'description': 'md5:2c81245da864428c904d53ae4ad2182b',
            'timestamp': 1711425600,
            'upload_date': '20240326',
            'uploader': '崩坏：星穹铁道',
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
                'uploader': '崩坏：星穹铁道',
                'thumbnail': r're:^https?://.*\.(png|jpg)',
            }
        }]
    }, {
        'url': 'https://www.taptap.cn/app/168332',
        'info_dict': {
            'id': 'app_168332',
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
            }
        }, {
            'info_dict': {
                'id': '4058462',
                'ext': 'mp4',
                'title': '原神',
                'description': 'md5:e345f39a5fea5de2a46923f70d5f76ab',
                'duration': 295,
                'thumbnail': r're:^https?://.*\.(png|jpg)',
            }
        }]

    }]

    def _deserialize_nuxt_data(self, serialized_nuxt):
        for row in serialized_nuxt:
            if isinstance(row, dict):
                for key, value_or_ref in row.items():
                    if isinstance(value_or_ref, int):
                        row[key] = serialized_nuxt[value_or_ref]
            elif isinstance(row, list):
                for index, value_or_ref in tuple(enumerate(row)):
                    if isinstance(value_or_ref, int):
                        row[index] = serialized_nuxt[value_or_ref]
        return serialized_nuxt[0]

    def _extract_video(self, video_id, x_ua):
        data = self._download_json(
            'https://www.taptap.cn/webapiv2/video-resource/v1/multi-get', video_id,
            query={'video_ids': video_id, 'X-UA': x_ua})

        video = traverse_obj(data, ('data', 'list', 0, {
            'id': ('video_id', {str_or_none}),
            'url': ('play_url', ('url', 'url_h265'), {url_or_none}),
            'duration': ('info', 'duration', {int_or_none}),
            'thumbnail': ('thumbnail', ('original_url', 'url'), {url_or_none}),
        }), get_all=False)
        if '.m3u8' in video['url']:
            video['formats'] = self._extract_m3u8_formats(video.pop('url'), video_id)
        return video

    def _real_extract(self, url):
        section, list_id = self._match_valid_url(url).groups()
        list_id = f'{section}_{list_id}'

        webpage = self._download_webpage(url, list_id)
        nuxt_data = self._deserialize_nuxt_data(self._search_json(
            r'<script[^>]+\bid=["\']__NUXT_DATA__["\'][^>]*>', webpage,
            'nuxt data', list_id, contains_pattern=r'\[(?s:.+)\]'))[1]
        x_ua = traverse_obj(nuxt_data, (
            'state', '$sbff', ..., {lambda x: parse_qs(x)['X-UA']}, ...), get_all=False)

        if section == 'moment':
            moment_data = traverse_obj(nuxt_data, ('data', ..., 'moment'), get_all=False)
            video_ids = traverse_obj(moment_data, ('topic', (('videos', ...), 'pin_video'), 'video_id'))
            metainfo = traverse_obj(moment_data, {
                'timestamp': ('created_time', {int_or_none}),
                'uploader': ('author', 'user', 'name', {str}),
                'title': ('topic', 'title', {str}),
                'description': ('topic', 'summary', {str}),
            })
        elif section == 'app':
            video_ids = traverse_obj(nuxt_data, ('data', ..., ('app_videos', 'videos'), ..., 'video_id'))
            metainfo = traverse_obj(nuxt_data, ('data', ..., {
                'title': ('title', {str}),
                'description': ('description', 'text', {str}, {clean_html}),
            }), get_all=False)

        entries = [self._extract_video(video_id, x_ua) for video_id in set(video_ids)]

        return self.playlist_result([{**metainfo, **e} for e in entries], **metainfo, id=list_id)
