from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    str_to_int,
    unified_strdate,
)
from .keezmovies import KeezMoviesIE


class MofosexIE(KeezMoviesIE):
    _VALID_URL = r'https?://(?:www\.)?mofosex\.com/videos/(?P<id>\d+)/(?P<display_id>[^/?#&.]+)\.html'
    _TESTS = [{
        'url': 'http://www.mofosex.com/videos/318131/amateur-teen-playing-and-masturbating-318131.html',
        'md5': '558fcdafbb63a87c019218d6e49daf8a',
        'info_dict': {
            'id': '318131',
            'display_id': 'amateur-teen-playing-and-masturbating-318131',
            'ext': 'mp4',
            'title': 'amateur teen playing and masturbating',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20121114',
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'age_limit': 18,
        }
    }, {
        # This video is no longer available
        'url': 'http://www.mofosex.com/videos/5018/japanese-teen-music-video.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        webpage, info = self._extract_info(url)

        view_count = str_to_int(self._search_regex(
            r'VIEWS:</span>\s*([\d,.]+)', webpage, 'view count', fatal=False))
        like_count = int_or_none(self._search_regex(
            r'id=["\']amountLikes["\'][^>]*>(\d+)', webpage,
            'like count', fatal=False))
        dislike_count = int_or_none(self._search_regex(
            r'id=["\']amountDislikes["\'][^>]*>(\d+)', webpage,
            'like count', fatal=False))
        upload_date = unified_strdate(self._html_search_regex(
            r'Added:</span>([^<]+)', webpage, 'upload date', fatal=False))

        info.update({
            'view_count': view_count,
            'like_count': like_count,
            'dislike_count': dislike_count,
            'upload_date': upload_date,
            'thumbnail': self._og_search_thumbnail(webpage),
        })

        return info


class MofosexEmbedIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?mofosex\.com/embed/?\?.*?\bvideoid=(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.mofosex.com/embed/?videoid=318131&referrer=KM',
        'only_matching': True,
    }]

    @staticmethod
    def _extract_urls(webpage):
        return re.findall(
            r'<iframe[^>]+\bsrc=["\']((?:https?:)?//(?:www\.)?mofosex\.com/embed/?\?.*?\bvideoid=\d+)',
            webpage)

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self.url_result(
            'http://www.mofosex.com/videos/{0}/{0}.html'.format(video_id),
            ie=MofosexIE.ie_key(), video_id=video_id)
