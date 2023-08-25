import urllib.parse

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    extract_attributes,
    int_or_none,
    parse_duration,
    try_get,
)


class TV5MondePlusIE(InfoExtractor):
    IE_DESC = 'TV5MONDE+'
    _VALID_URL = r'https?://(?:www\.)?(?:tv5mondeplus|revoir\.tv5monde)\.com/toutes-les-videos/[^/]+/(?P<id>[^/?#]+)'
    _TESTS = [{
        # movie
        'url': 'https://revoir.tv5monde.com/toutes-les-videos/cinema/les-novices',
        'md5': 'c86f60bf8b75436455b1b205f9745955',
        'info_dict': {
            'id': '106971507_6D4BA7b',
            'display_id': 'les-novices',
            'ext': 'mp4',
            'title': 'Les novices',
            'description': 'md5:2e7c33ba3ad48dabfcc2a956b88bde2b',
            'upload_date': '20230821',
            'thumbnail': 'https://revoir.tv5monde.com/uploads/media/video_thumbnail/0738/60/01e952b7ccf36b7c6007ec9131588954ab651de9.jpeg',
            'duration': 5177,
            'episode': 'Les novices',
        },
    }, {
        # series episode
        'url': 'https://revoir.tv5monde.com/toutes-les-videos/series-fictions/opj-les-dents-de-la-terre-2',
        'info_dict': {
            'id': '106990379_6D4BA7b',
            'display_id': 'opj-les-dents-de-la-terre-2',
            'ext': 'mp4',
            'title': "OPJ - Les dents de la Terre (2)",
            'description': 'md5:288f87fd68d993f814e66e60e5302d9d',
            'upload_date': '20230823',
            'series': "OPJ",
            'episode': 'Les dents de la Terre (2)',
            'duration': 2877,
            'thumbnail': 'https://dl-revoir.tv5monde.com/images/1a/5753448.jpg'
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
            vpl_data['data-broadcast'], display_id)
        formats = []
        for video_file in video_files:
            v_url = video_file.get('url')
            if not v_url:
                continue
            if video_file.get('type') == 'application/deferred':
                d_param = urllib.parse.quote(v_url)
                headers = {'Authorization': 'Bearer ' + video_file.get('token')}
                json = self._download_json(
                    f'https://api.tv5monde.com/player/asset/{d_param}/resolve?condenseKS=true', v_url,
                    note='Downloading deferred info', headers=headers)
                v_url = json[0]['url']
                video_id = self._search_regex(
                    r'assets/([\d]{9}_[\da-fA-F]{7})/materials', v_url, 'video id',
                    default=display_id)

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

        metadata = self._parse_json(
            vpl_data['data-metadata'], display_id)
        duration = (int_or_none(try_get(metadata, lambda x: x['content']['duration']))
                    or parse_duration(self._html_search_meta('duration', webpage)))

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

        if not video_id:
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
            'duration': duration,
            'upload_date': upload_date,
            'formats': formats,
            'series': series,
            'episode': episode,
        }
