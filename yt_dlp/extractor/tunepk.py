from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    int_or_none,
    try_get,
    unified_timestamp,
)


class TunePkIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?:www\.)?tune\.pk/(?:video/|player/embed_player.php?.*?\bvid=)|
                            embed\.tune\.pk/play/
                        )
                        (?P<id>\d+)
                    '''
    _TESTS = [{
        'url': 'https://tune.pk/video/6919541/maudie-2017-international-trailer-1-ft-ethan-hawke-sally-hawkins',
        'md5': '0c537163b7f6f97da3c5dd1e3ef6dd55',
        'info_dict': {
            'id': '6919541',
            'ext': 'mp4',
            'title': 'Maudie (2017) | International Trailer # 1 ft Ethan Hawke, Sally Hawkins',
            'description': 'md5:eb5a04114fafef5cec90799a93a2d09c',
            'thumbnail': r're:^https?://.*\.jpg$',
            'timestamp': 1487327564,
            'upload_date': '20170217',
            'uploader': 'Movie Trailers',
            'duration': 107,
            'view_count': int,
        }
    }, {
        'url': 'https://tune.pk/player/embed_player.php?vid=6919541&folder=2017/02/17/&width=600&height=350&autoplay=no',
        'only_matching': True,
    }, {
        'url': 'https://embed.tune.pk/play/6919541?autoplay=no&ssl=yes&inline=true',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(
            'https://tune.pk/video/%s' % video_id, video_id)

        details = self._parse_json(
            self._search_regex(
                r'new\s+TunePlayer\(({.+?})\)\s*;\s*\n', webpage, 'tune player'),
            video_id)['details']

        video = details['video']
        title = video.get('title') or self._og_search_title(
            webpage, default=None) or self._html_search_meta(
            'title', webpage, 'title', fatal=True)

        formats = self._parse_jwplayer_formats(
            details['player']['sources'], video_id)
        self._sort_formats(formats)

        description = self._og_search_description(
            webpage, default=None) or self._html_search_meta(
            'description', webpage, 'description')

        thumbnail = video.get('thumb') or self._og_search_thumbnail(
            webpage, default=None) or self._html_search_meta(
            'thumbnail', webpage, 'thumbnail')

        timestamp = unified_timestamp(video.get('date_added'))
        uploader = try_get(
            video, lambda x: x['uploader']['name'],
            compat_str) or self._html_search_meta('author', webpage, 'author')

        duration = int_or_none(video.get('duration'))
        view_count = int_or_none(video.get('views'))

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'timestamp': timestamp,
            'uploader': uploader,
            'duration': duration,
            'view_count': view_count,
            'formats': formats,
        }
