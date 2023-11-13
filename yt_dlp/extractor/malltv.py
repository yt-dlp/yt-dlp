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
        'md5': 'cd69ce29176f6533b65bff69ed9a5f2a',
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
            'comment_count': int,
            'thumbnail': 'https://cdn.vpplayer.tech/agmipnzv/encode/vjsnigfq/thumbnails/retina.jpg',
            'average_rating': 9.060869565217391,
            'dislike_count': int,
            'like_count': int,
        }
    }, {
        'url': 'https://www.mall.tv/kdo-to-plati/18-miliard-pro-neziskovky-opravdu-jsou-sportovci-nebo-clovek-v-tisni-pijavice',
        'only_matching': True,
    }, {
        'url': 'https://sk.mall.tv/gejmhaus/reklamacia-nehreje-vyrobnik-tepla-alebo-spekacka',
        'only_matching': True,
    }, {
        'url': 'https://www.mall.tv/zivoty-slavnych/nadeje-vychodu-i-zapadu-jak-michail-gorbacov-zmenil-politickou-mapu-sveta-a-ziskal-za-to-nobelovu-cenu-miru',
        'info_dict': {
            'id': 'yx010y',
            'ext': 'mp4',
            'dislike_count': int,
            'description': 'md5:aee02bee5a8d072c6a8207b91d1905a9',
            'thumbnail': 'https://cdn.vpplayer.tech/agmipnzv/encode/vjsnjdeu/thumbnails/retina.jpg',
            'comment_count': int,
            'display_id': 'md5:0ec2afa94d2e2b7091c019cef2a43a9b',
            'like_count': int,
            'duration': 752,
            'timestamp': 1646956800,
            'title': 'md5:fe79385daaf16d74c12c1ec4a26687af',
            'view_count': int,
            'upload_date': '20220311',
            'average_rating': 9.685714285714285,
        }
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(
            url, display_id, headers=self.geo_verification_headers())

        video = self._parse_json(self._search_regex(
            r'videoObject\s*=\s*JSON\.parse\(JSON\.stringify\(({.+?})\)\);',
            webpage, 'video object'), display_id)

        video_id = self._search_regex(
            r'<input\s*id\s*=\s*player-id-name\s*[^>]+value\s*=\s*(\w+)', webpage, 'video id')

        formats = self._extract_m3u8_formats(
            video['VideoSource'], video_id, 'mp4', 'm3u8_native')

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
            'id': str(video_id),
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
