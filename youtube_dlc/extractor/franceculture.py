# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    extract_attributes,
    int_or_none,
)


class FranceCultureIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?franceculture\.fr/emissions/(?:[^/]+/)*(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'http://www.franceculture.fr/emissions/carnet-nomade/rendez-vous-au-pays-des-geeks',
        'info_dict': {
            'id': 'rendez-vous-au-pays-des-geeks',
            'display_id': 'rendez-vous-au-pays-des-geeks',
            'ext': 'mp3',
            'title': 'Rendez-vous au pays des geeks',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20140301',
            'timestamp': 1393700400,
            'vcodec': 'none',
        }
    }, {
        # no thumbnail
        'url': 'https://www.franceculture.fr/emissions/la-recherche-montre-en-main/la-recherche-montre-en-main-du-mercredi-10-octobre-2018',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        video_data = extract_attributes(self._search_regex(
            r'''(?sx)
                (?:
                    </h1>|
                    <div[^>]+class="[^"]*?(?:title-zone-diffusion|heading-zone-(?:wrapper|player-button))[^"]*?"[^>]*>
                ).*?
                (<button[^>]+data-(?:url|asset-source)="[^"]+"[^>]+>)
            ''',
            webpage, 'video data'))

        video_url = video_data.get('data-url') or video_data['data-asset-source']
        title = video_data.get('data-asset-title') or video_data.get('data-diffusion-title') or self._og_search_title(webpage)

        description = self._html_search_regex(
            r'(?s)<div[^>]+class="intro"[^>]*>.*?<h2>(.+?)</h2>',
            webpage, 'description', default=None)
        thumbnail = self._search_regex(
            r'(?s)<figure[^>]+itemtype="https://schema.org/ImageObject"[^>]*>.*?<img[^>]+(?:data-dejavu-)?src="([^"]+)"',
            webpage, 'thumbnail', default=None)
        uploader = self._html_search_regex(
            r'(?s)<span class="author">(.*?)</span>',
            webpage, 'uploader', default=None)
        ext = determine_ext(video_url.lower())

        return {
            'id': display_id,
            'display_id': display_id,
            'url': video_url,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'ext': ext,
            'vcodec': 'none' if ext == 'mp3' else None,
            'uploader': uploader,
            'timestamp': int_or_none(video_data.get('data-start-time')) or int_or_none(video_data.get('data-asset-created-date')),
            'duration': int_or_none(video_data.get('data-duration')),
        }
