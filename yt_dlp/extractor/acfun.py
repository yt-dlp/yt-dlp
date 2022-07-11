from .common import InfoExtractor
from ..utils import (
    float_or_none,
    format_field,
    int_or_none,
    traverse_obj,
    parse_codecs,
    parse_qs,
)


class AcFunVideoBaseIE(InfoExtractor):
    def _extract_metadata(self, video_id, video_info):
        playjson = self._parse_json(video_info['ksPlayJson'], video_id)

        formats, subtitles = [], {}
        for video in traverse_obj(playjson, ('adaptationSet', 0, 'representation')):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(video['url'], video_id, 'mp4', fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)
            for f in fmts:
                f.update({
                    'fps': float_or_none(video.get('frameRate')),
                    'width': int_or_none(video.get('width')),
                    'height': int_or_none(video.get('height')),
                    'tbr': float_or_none(video.get('avgBitrate')),
                    **parse_codecs(video.get('codecs', ''))
                })

        self._sort_formats(formats)
        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'duration': float_or_none(video_info.get('durationMillis'), 1000),
            'timestamp': int_or_none(video_info.get('uploadTime'), 1000),
            'http_headers': {'Referer': 'https://www.acfun.cn/'},
        }


class AcFunVideoIE(AcFunVideoBaseIE):
    _VALID_URL = r'https?://www\.acfun\.cn/v/ac(?P<id>[_\d]+)'

    _TESTS = [{
        'url': 'https://www.acfun.cn/v/ac35457073',
        'info_dict': {
            'id': '35457073',
            'duration': 174.208,
            'timestamp': 1656403967,
            'title': '1 8 岁 现 状',
            'description': '“赶紧回去！班主任查班了！”',
            'uploader': '锤子game',
            'uploader_id': '51246077',
            'thumbnail': r're:^https?://.*\.(jpg|jpeg)',
            'upload_date': '20220628',
            'like_count': int,
            'view_count': int,
            'tags': ['电子竞技', 'LOL', 'CF', '搞笑', '真人'],
            'comment_count': int,
        },
        'params': {
            'skip_download': 'm3u8',
            'ignore_no_formats_error': True
        },
    }, {
        # example for len(video_list) > 1
        'url': 'https://www.acfun.cn/v/ac35468952_2',
        'info_dict': {
            'id': '35468952_2',
            'duration': 90.459,
            'title': '【动画剧集】Rocket & Groot Season 1（2022）/火箭浣熊与格鲁特第1季 P02 S01E02 十拿九穩',
            'uploader': '比令',
            'uploader_id': '37259967'
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)
        json_all = self._search_json(r'window.videoInfo\s*=\s*', webpage, 'videoInfo', video_id)

        title = json_all.get('title')
        video_list = json_all.get('videoList') or []
        video_internal_id = traverse_obj(json_all, ('currentVideoInfo', 'id'))
        if video_internal_id and len(video_list) > 1:
            part_idx, part_video_info = next(
                (idx + 1, v) for (idx, v) in enumerate(video_list)
                if v['id'] == video_internal_id)
            title = f'{title} P{part_idx:02d} {part_video_info["title"]}'

        return {
            **self._extract_metadata(video_id, json_all['currentVideoInfo']),
            'title': title,
            'thumbnail': json_all.get('coverUrl'),
            'description': json_all.get('description'),
            'uploader': traverse_obj(json_all, ('user', 'name')),
            'uploader_id': traverse_obj(json_all, ('user', 'href')),
            'tags': traverse_obj(json_all, ('tagList', ..., 'name')),
            'view_count': int_or_none(json_all.get('viewCount')),
            'like_count': int_or_none(json_all.get('likeCountShow')),
            'comment_count': int_or_none(json_all.get('commentCountShow')),
        }


class AcFunBangumiIE(AcFunVideoBaseIE):
    _VALID_URL = r'https?://www\.acfun\.cn/bangumi/(?P<id>aa[_\d]+)'

    _TESTS = [{
        'url': 'https://www.acfun.cn/bangumi/aa6002917',
        'info_dict': {
            'id': 'aa6002917',
            'title': '租借女友 第1话 租借女友',
            'duration': 1467,
            'timestamp': 1594432800,
        },
        'params': {
            'skip_download': 'm3u8',
            'ignore_no_formats_error': True,
        },
        'skip': 'Geo-restricted to China',
    }, {
        'url': 'https://www.acfun.cn/bangumi/aa6002917_36188_1745457?ac=2',
        'only_matching': True,
    }, {
        'url': 'https://www.acfun.cn/bangumi/aa5023171_36188_1750645',
        'info_dict': {
            'id': 'aa5023171_36188_1750645',
            'duration': 760.0,
            'timestamp': 1545552185,
            'title': '红孩儿之趴趴蛙寻石记 第5话 ',
            'season': '红孩儿之趴趴蛙寻石记',
            'season_id': 5023171,
            'season_number': 1,  # series has only 1 season
            'episode': '',
            'episode_number': 5
        },
        'params': {
            'skip_download': 'm3u8',
            'ignore_no_formats_error': True,
        },
    }, {
        'url': 'https://www.acfun.cn/bangumi/aa6004596_36188_1759741',
        'info_dict': {
            'id': 'aa6004596_36188_1759741',
            'duration': 1420.04,
            'title': '摇曳露营△ 第二季 第2话 岁末的单人露营女孩',
            'season': '摇曳露营△ 第二季',
            'season_id': 6004596,
            'season_number': 2,
            'episode': '岁末的单人露营女孩',
            'episode_number': 2
        },
        'params': {
            'skip_download': 'm3u8',
            'ignore_no_formats_error': True,
        },
        'skip': 'Geo-restricted to China',
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        ac_idx = parse_qs(url).get('ac', [None])[-1]
        video_id = f'{video_id}{format_field(ac_idx, template="__%s")}'

        webpage = self._download_webpage(url, video_id)
        json_bangumi_data = self._search_json(r'window.bangumiData\s*=\s*', webpage, 'bangumiData', video_id)

        if ac_idx:
            video_info = json_bangumi_data['hlVideoInfo']
            return {
                **self._extract_metadata(video_id, video_info),
                'title': video_info.get('title'),
            }

        video_info = json_bangumi_data['currentVideoInfo']

        season_id = json_bangumi_data.get('bangumiId')
        season_number = season_id and next((
            idx for idx, v in enumerate(json_bangumi_data.get('relatedBangumis') or [], 1)
            if v.get('id') == season_id), 1)

        json_bangumi_list = self._search_json(
            r'window.bangumiList\s*=\s*', webpage, 'bangumiList', video_id, fatal=False)
        video_internal_id = int_or_none(traverse_obj(json_bangumi_data, ('currentVideoInfo', 'id')))
        episode_number = video_internal_id and next((
            idx for idx, v in enumerate(json_bangumi_list.get('items') or [], 1)
            if v.get('videoId') == video_internal_id), None)

        return {
            **self._extract_metadata(video_id, video_info),
            'title': json_bangumi_data.get('showTitle'),
            'thumbnail': json_bangumi_data.get('image'),
            'season': json_bangumi_data.get('bangumiTitle'),
            'season_id': season_id,
            'season_number': season_number,
            'episode': json_bangumi_data.get('title'),
            'episode_number': episode_number,
            'comment_count': int_or_none(json_bangumi_data.get('commentCount')),
        }
