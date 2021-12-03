# coding: utf-8
from __future__ import unicode_literals

import re
from .common import InfoExtractor
from ..utils import (
    determine_ext,
    extract_attributes,
    int_or_none,
)


class FranceCultureIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?franceculture\.fr/emissions/(?:[^/]+/)*(?P<id>[^/?#&]+)'
    _TESTS = [{
        # playlist
        'url': 'https://www.franceculture.fr/emissions/hasta-dente',
        'playlist_mincount': 12,
        'playlist_maxcount': 12,
        'info_dict': {
            'id': 'hasta-dente',
            'title': 'Hasta Dente !',
        }
    }, {
        'url': 'https://www.franceculture.fr/emissions/carnet-nomade/rendez-vous-au-pays-des-geeks',
        'info_dict': {
            'id': 'rendez-vous-au-pays-des-geeks',
            'display_id': 'rendez-vous-au-pays-des-geeks',
            'ext': 'mp3',
            'title': 'Rendez-vous au pays des geeks',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20140301',
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

        title = video_data.get('data-emission-title') or video_data.get('data-diffusion-title') or self._og_search_title(webpage)
        description = self._html_search_regex(
            r'(?s)<div[^>]+class="intro"[^>]*>.*?<h2>(.+?)</h2>',
            webpage, 'description', default=None)

        # page has playlist
        if (re.search(r'<div[^>]+class="[^"]*?podcast-list[^"?]*?"[^>]*>', webpage) is not None):
            playlist_data = self._search_regex(
                r'''(?sx)
                    <div[^>]+class="[^"]*?podcast-list[^"?]*?"[^>]*>
                    (.*?)
                    <div[^>]+class="[^"]*?see-more-anchor[^"]*?">
                ''',
                webpage, 'playlist data')

            entries = [
                self.url_result(video_url, FranceCultureIE.ie_key(), video_id, video_title)
                for video_url, video_id, video_title in re.findall(
                    r'data-url="([^"]+)"[^>]*data-diffusion-path="([^"]+)"[^>]*data-diffusion-title="([^"]+)"',
                    playlist_data)
            ]

            return self.playlist_result(entries, display_id, title, description)

        video_url = video_data.get('data-url') or video_data['data-asset-source']

        thumbnail = self._search_regex(
            r'(?s)<figure[^>]+itemtype="https://schema.org/ImageObject"[^>]*>.*?<img[^>]+(?:data-dejavu-)?src="([^"]+)"',
            webpage, 'thumbnail', default=None)
        upload_date = self._search_regex(
            r'(?s)"datePublished":\s*"(\d{4}-\d{2}-\d{2})',
            webpage, 'date', default=None)

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
            'upload_date': upload_date.replace("-", "") if upload_date is not None else None,
            'duration': int_or_none(video_data.get('data-duration')),
        }
