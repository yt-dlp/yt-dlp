import re

from .common import InfoExtractor
from ..utils import (
    float_or_none,
    int_or_none,
    traverse_obj,
)


class AcFunVideoIE(InfoExtractor):
    _VALID_URL = r'(?x)https?://(?:www\.acfun\.cn/v/)ac(?P<id>[_\d]+)'

    _TESTS = [{
        'url': 'https://www.acfun.cn/v/ac35457073',
        'info_dict': {
            'id': '35283657',
            'title': '【十五周年庆】文章区UP主祝AcFun生日快乐！',
            'duration': 455.21,
            'timestamp': 1655289827,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'skip': 'Geo-restricted to China',
    }]

    def parse_format(self, info, video_id):
        vcodec, acodec = None, None

        codec_str = info.get('codecs') or ''
        m = re.match('(?P<vc>[^,]+),(?P<ac>[^,]+)', codec_str)
        if m:
            vcodec = m.group("vc")
            acodec = m.group("ac")

        formats, _ = self._extract_m3u8_formats_and_subtitles(
            info['url'], video_id)

        # it seems AcFun do not have subtitles

        return {
            **formats[0],
            'fps': int_or_none(info.get('frameRate')),
            'width': int_or_none(info.get('width')),
            'height': int_or_none(info.get('height')),
            'vcodec': vcodec,
            'acodec': acodec,
            'tbr': float_or_none(info.get('avgBitrate')),
            'ext': 'mp4'
        }

    def parse_format_list(self, jobj, video_id):
        formats = []
        for video in jobj:
            fmt = self.parse_format(video, video_id)
            formats.append(fmt)

        self._sort_formats(formats)

        return formats

    def gen_other_video_info_map(self, video_info):
        return {
            'duration': float_or_none(video_info.get('durationMillis'), 1000),
            'timestamp': int_or_none(video_info.get('uploadTime'), 1000),
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        json_all = self._search_json(r'window.videoInfo\s*=\s*', webpage, 'videoInfo', video_id)

        video_info = json_all['currentVideoInfo']
        playjson = self._parse_json(video_info['ksPlayJson'], video_id)
        video_internal_id = traverse_obj(json_all, ('currentVideoInfo', 'id'))

        formats = self.parse_format_list(traverse_obj(playjson, ('adaptationSet', 0, 'representation')), video_id)

        video_list = json_all['videoList']
        p_idx, video_info = [(idx + 1, v) for (idx, v) in enumerate(video_list)
                             if v['id'] == video_internal_id
                             ][0]

        title = json_all['title']
        if len(video_list) > 1:
            title = f"{title} P{p_idx:02d} {video_info['title']}"

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': json_all.get('coverUrl'),
            'description': json_all.get('description'),
            'uploader': traverse_obj(json_all, ('user', 'name')),
            'uploader_id': traverse_obj(json_all, ('user', 'href')),
            'tags': [t['name'] for t in json_all.get('tagList', []) if 'name' in t],
            'view_count': int_or_none(json_all.get('viewCount')),
            'like_count': int_or_none(json_all.get('likeCountShow')),
            'comment_count': int_or_none(json_all.get('commentCountShow')),
            'http_headers': {
                'Referer': url,
            },
            **self.gen_other_video_info_map(video_info)
        }


class AcFunBangumiIE(AcFunVideoIE):
    _VALID_URL = r'(?x)https?://(?:www\.acfun\.cn/bangumi/)(?P<id>aa[_\d]+(?:\?ac=\d+)?)'

    _TESTS = [{
        'url': 'https://www.acfun.cn/bangumi/aa6002917',
        'info_dict': {
            'id': 'aa6002917',
            'title': '租借女友 第1话 租借女友',
            'duration': 1467,
            'timestamp': 1594432800,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'skip': 'Geo-restricted to China',
    }, {
        'url': 'https://www.acfun.cn/bangumi/aa6002917_36188_1745457?ac=2',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        has_ac_idx = False
        mobj = re.match(r'(?P<id>aa[_\d]+)(?:\?ac=(?P<ac_idx>\d+))?', video_id)
        if mobj.group('ac_idx'):
            has_ac_idx = True
            video_id = f"{mobj.group('id')}_ac={mobj.group('ac_idx')}"

        webpage = self._download_webpage(url, video_id)
        json_bangumi_data = self._search_json(r'window.bangumiData\s*=\s*', webpage, 'bangumiData', video_id)

        other_info = {}
        if not has_ac_idx:
            video_info = json_bangumi_data['currentVideoInfo']
            title = json_bangumi_data['showTitle']
            other_info.update({
                'thumbnail': json_bangumi_data.get('image'),
                'comment_count': int_or_none(json_bangumi_data.get('commentCount')),
            })
        else:
            # if has ac_idx, this url is a proxy to other video which is at https://www.acfun.cn/v/ac
            # the normal video_id is not in json
            video_info = json_bangumi_data['hlVideoInfo']
            title = video_info['title']

        playlist = self._parse_json(video_info['ksPlayJson'], video_id)
        formats = self.parse_format_list(traverse_obj(playlist, ('adaptationSet', 0, 'representation')), video_id)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'http_headers': {
                'Referer': url,
            },
            ** other_info,
            ** self.gen_other_video_info_map(video_info)
        }
