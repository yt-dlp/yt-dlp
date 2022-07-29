# coding: utf-8
from __future__ import unicode_literals

from .turner import TurnerBaseIE
from ..compat import (
    compat_urllib_parse_urlparse,
    compat_parse_qs,
)
from ..utils import (
    int_or_none,
)


class TruTVIE(TurnerBaseIE):
    _VALID_URL = r'https?://(?:www\.)?trutv\.com/shows/[0-9A-Za-z-]+/season-\d+/episode-\d+/(?P<id>[0-9A-Za-z-]+)'
    _TEST = {
        'url': 'https://www.trutv.com/shows/impractical-jokers/season-8/episode-2/the-closer',
        'info_dict': {
            'id': '0b90803a0d4bba757085a61cc25be505358cd8b5',
            'ext': 'mp4',
            'title': 'The Closer',
            'description': 'Q, Joe, Sal and Murr get tech help from some confused tutors, then play Hot Potato in a shoe store. Plus, the big loser wishes he could press escape during a brutal coffee shop punishment.',
            'series': 'Impractical Jokers',
            'season_number': 8,
            'episode_number': 2,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        episode_slug = self._match_id(url)

        webpage = self._download_webpage(url, episode_slug)

        meta = self._parse_json(self._html_search_regex(r'<script type="application/ld\+json">(.+)</script>', webpage, episode_slug), episode_slug)

        data = self._parse_json(self._html_search_regex(r'<script type="application/json" data-drupal-selector="drupal-settings-json">(.+)</script>', webpage, episode_slug), episode_slug)

        eps = data['turner_playlist']

        for ep in eps:
            if ep['url'] in url:
                video_data = ep

        media_id = video_data['mediaID']
        title = video_data['title'].strip()

        tokenizer_query = compat_parse_qs(compat_urllib_parse_urlparse(data['ngtv_token_url']).query)

        info = self._extract_ngtv_info(
            media_id, tokenizer_query, {
                'url': url,
                'site_name': 'truTV',
                'auth_required': video_data.get('authRequired') == '1',
            })

        thumbnails = []
        for images in meta.get('image', []):
            for image in images:
                if not image:
                    continue
                thumbnails.append({
                    'url': image,
                })

        info.update({
            'id': media_id,
            'display_id': video_data.get('videoId'),
            'title': title,
            'description': video_data.get('shortDescription'),
            'thumbnails': thumbnails,
            'series': meta.get('partOfSeries').get('name'),
            'season_number': int_or_none(meta.get('partOfSeason').get('seasonNumber')),
            'episode_number': int_or_none(meta.get('episodeNumber')),
        })
        return info
