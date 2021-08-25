# coding: utf-8
from __future__ import unicode_literals


from .common import InfoExtractor
from ..utils import (
    int_or_none,
    remove_end,
)


class GameStarIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?game(?P<site>pro|star)\.de/videos/.*,(?P<id>[0-9]+)\.html'
    _TESTS = [{
        'url': 'http://www.gamestar.de/videos/trailer,3/hobbit-3-die-schlacht-der-fuenf-heere,76110.html',
        'md5': 'ee782f1f8050448c95c5cacd63bc851c',
        'info_dict': {
            'id': '76110',
            'ext': 'mp4',
            'title': 'Hobbit 3: Die Schlacht der Fünf Heere - Teaser-Trailer zum dritten Teil',
            'description': 'Der Teaser-Trailer zu Hobbit 3: Die Schlacht der Fünf Heere zeigt einige Szenen aus dem dritten Teil der Saga und kündigt den...',
            'thumbnail': r're:^https?://.*\.jpg$',
            'timestamp': 1406542380,
            'upload_date': '20140728',
            'duration': 17,
        }
    }, {
        'url': 'http://www.gamepro.de/videos/top-10-indie-spiele-fuer-nintendo-switch-video-tolle-nindies-games-zum-download,95316.html',
        'only_matching': True,
    }, {
        'url': 'http://www.gamestar.de/videos/top-10-indie-spiele-fuer-nintendo-switch-video-tolle-nindies-games-zum-download,95316.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        site = mobj.group('site')
        video_id = mobj.group('id')

        webpage = self._download_webpage(url, video_id)

        # TODO: there are multiple ld+json objects in the webpage,
        # while _search_json_ld finds only the first one
        json_ld = self._parse_json(self._search_regex(
            r'(?s)<script[^>]+type=(["\'])application/ld\+json\1[^>]*>(?P<json_ld>[^<]+VideoObject[^<]+)</script>',
            webpage, 'JSON-LD', group='json_ld'), video_id)
        info_dict = self._json_ld(json_ld, video_id)
        info_dict['title'] = remove_end(
            info_dict['title'], ' - Game%s' % site.title())

        view_count = int_or_none(json_ld.get('interactionCount'))
        comment_count = int_or_none(self._html_search_regex(
            r'<span>Kommentare</span>\s*<span[^>]+class=["\']count[^>]+>\s*\(\s*([0-9]+)',
            webpage, 'comment count', fatal=False))

        info_dict.update({
            'id': video_id,
            'url': 'http://gamestar.de/_misc/videos/portal/getVideoUrl.cfm?premium=0&videoId=' + video_id,
            'ext': 'mp4',
            'view_count': view_count,
            'comment_count': comment_count
        })

        return info_dict
