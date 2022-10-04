from .common import InfoExtractor
from ..utils import (
    clean_html,
    dict_get,
    float_or_none,
    int_or_none,
    merge_dicts,
    parse_duration,
    try_get,
)


class MallTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www|sk)\.)?mall\.tv/(?:[^/]+/)*(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.mall.tv/18-miliard-pro-neziskovky-opravdu-jsou-sportovci-nebo-clovek-v-tisni-pijavice',
        'md5': '1c4a37f080e1f3023103a7b43458e518',
        'info_dict': {
            'id': 't0zzt0',
            'display_id': '18-miliard-pro-neziskovky-opravdu-jsou-sportovci-nebo-clovek-v-tisni-pijavice',
            'ext': 'mp4',
            'title': '18 miliard pro neziskovky. Opravdu jsou sportovci nebo Člověk v tísni pijavice?',
            'description': 'md5:db7d5744a4bd4043d9d98324aa72ab35',
            'duration': 216,
            'timestamp': 1538870400,
            'upload_date': '20181007',
            'view_count': int,
        }
    }, {
        'url': 'https://www.mall.tv/kdo-to-plati/18-miliard-pro-neziskovky-opravdu-jsou-sportovci-nebo-clovek-v-tisni-pijavice',
        'only_matching': True,
    }, {
        'url': 'https://sk.mall.tv/gejmhaus/reklamacia-nehreje-vyrobnik-tepla-alebo-spekacka',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(
            url, display_id, headers=self.geo_verification_headers())

        video = self._parse_json(self._search_regex(
            r'videoObject\s*=\s*JSON\.parse\(JSON\.stringify\(({.+?})\)\);',
            webpage, 'video object'), display_id)
        video_source = video['VideoSource']
        video_id = self._search_regex(
            r'/([\da-z]+)/index\b', video_source, 'video id')

        formats = self._extract_m3u8_formats(
            video_source + '.m3u8', video_id, 'mp4', 'm3u8_native')
        self._sort_formats(formats)

        subtitles = {}
        for s in (video.get('Subtitles') or {}):
            s_url = s.get('Url')
            if not s_url:
                continue
            subtitles.setdefault(s.get('Language') or 'cz', []).append({
                'url': s_url,
            })

        entity_counts = video.get('EntityCounts') or {}

        def get_count(k):
            v = entity_counts.get(k + 's') or {}
            return int_or_none(dict_get(v, ('Count', 'StrCount')))

        info = self._search_json_ld(webpage, video_id, default={})

        return merge_dicts({
            'id': video_id,
            'display_id': display_id,
            'title': video.get('Title'),
            'description': clean_html(video.get('Description')),
            'thumbnail': video.get('ThumbnailUrl'),
            'formats': formats,
            'subtitles': subtitles,
            'duration': int_or_none(video.get('DurationSeconds')) or parse_duration(video.get('Duration')),
            'view_count': get_count('View'),
            'like_count': get_count('Like'),
            'dislike_count': get_count('Dislike'),
            'average_rating': float_or_none(try_get(video, lambda x: x['EntityRating']['AvarageRate'])),
            'comment_count': get_count('Comment'),
        }, info)
