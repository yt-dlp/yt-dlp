# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    extract_attributes,
    int_or_none,
    parse_duration,
)


class TV5MondePlusIE(InfoExtractor):
    IE_DESC = 'TV5MONDE+'
    _VALID_URL = r'https?://(?:www\.)?(?:tv5mondeplus|revoir\.tv5monde)\.com/toutes-les-videos/[^/]+/(?P<id>[^/?#]+)'
    _TESTS = [{
        # movie
        'url': 'https://revoir.tv5monde.com/toutes-les-videos/cinema/rendez-vous-a-atlit',
        'md5': '8cbde5ea7b296cf635073e27895e227f',
        'info_dict': {
            'id': '822a4756-0712-7329-1859-a13ac7fd1407',
            'display_id': 'rendez-vous-a-atlit',
            'ext': 'mp4',
            'title': 'Rendez-vous à Atlit',
            'description': 'md5:2893a4c5e1dbac3eedff2d87956e4efb',
            'upload_date': '20200130',
        },
    }, {
        # series episode
        'url': 'https://revoir.tv5monde.com/toutes-les-videos/series-fictions/c-est-la-vie-ennemie-juree',
        'info_dict': {
            'id': '0df7007c-4900-3936-c601-87a13a93a068',
            'display_id': 'c-est-la-vie-ennemie-juree',
            'ext': 'mp4',
            'title': "C'est la vie - Ennemie jurée",
            'description': 'md5:dfb5c63087b6f35fe0cc0af4fe44287e',
            'upload_date': '20200130',
            'series': "C'est la vie",
            'episode': 'Ennemie jurée',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://revoir.tv5monde.com/toutes-les-videos/series-fictions/neuf-jours-en-hiver-neuf-jours-en-hiver',
        'only_matching': True,
    }, {
        'url': 'https://revoir.tv5monde.com/toutes-les-videos/info-societe/le-journal-de-la-rts-edition-du-30-01-20-19h30',
        'only_matching': True,
    }]
    _GEO_BYPASS = False

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        if ">Ce programme n'est malheureusement pas disponible pour votre zone géographique.<" in webpage:
            self.raise_geo_restricted(countries=['FR'])

        title = episode = self._html_search_regex(r'<h1>([^<]+)', webpage, 'title')
        vpl_data = extract_attributes(self._search_regex(
            r'(<[^>]+class="video_player_loader"[^>]+>)',
            webpage, 'video player loader'))

        video_files = self._parse_json(
            vpl_data['data-broadcast'], display_id).get('files', [])
        formats = []
        for video_file in video_files:
            v_url = video_file.get('url')
            if not v_url:
                continue
            video_format = video_file.get('format') or determine_ext(v_url)
            if video_format == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    v_url, display_id, 'mp4', 'm3u8_native',
                    m3u8_id='hls', fatal=False))
            else:
                formats.append({
                    'url': v_url,
                    'format_id': video_format,
                })
        self._sort_formats(formats)

        description = self._html_search_regex(
            r'(?s)<div[^>]+class=["\']episode-texte[^>]+>(.+?)</div>', webpage,
            'description', fatal=False)

        series = self._html_search_regex(
            r'<p[^>]+class=["\']episode-emission[^>]+>([^<]+)', webpage,
            'series', default=None)

        if series and series != title:
            title = '%s - %s' % (series, title)

        upload_date = self._search_regex(
            r'(?:date_publication|publish_date)["\']\s*:\s*["\'](\d{4}_\d{2}_\d{2})',
            webpage, 'upload date', default=None)
        if upload_date:
            upload_date = upload_date.replace('_', '')

        video_id = self._search_regex(
            (r'data-guid=["\']([\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})',
             r'id_contenu["\']\s:\s*(\d+)'), webpage, 'video id',
            default=display_id)

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnail': vpl_data.get('data-image'),
            'duration': int_or_none(vpl_data.get('data-duration')) or parse_duration(self._html_search_meta('duration', webpage)),
            'upload_date': upload_date,
            'formats': formats,
            'series': series,
            'episode': episode,
        }
