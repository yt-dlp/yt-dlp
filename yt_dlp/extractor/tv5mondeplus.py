import urllib.parse

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    extract_attributes,
    int_or_none,
    parse_duration,
    traverse_obj,
    try_get,
    url_or_none,
)


class TV5MondePlusIE(InfoExtractor):
    IE_DESC = 'TV5MONDE+'
    _VALID_URL = r'https?://(?:www\.)?(?:tv5mondeplus|revoir\.tv5monde)\.com/toutes-les-videos/[^/]+/(?P<id>[^/?#]+)'
    _TESTS = [{
        # movie
        'url': 'https://revoir.tv5monde.com/toutes-les-videos/cinema/les-novices',
        'md5': 'c86f60bf8b75436455b1b205f9745955',
        'info_dict': {
            'id': 'ZX0ipMyFQq_6D4BA7b',
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
            'id': 'wJ0eeEPozr_6D4BA7b',
            'display_id': 'opj-les-dents-de-la-terre-2',
            'ext': 'mp4',
            'title': "OPJ - Les dents de la Terre (2)",
            'description': 'md5:288f87fd68d993f814e66e60e5302d9d',
            'upload_date': '20230823',
            'series': 'OPJ',
            'episode': 'Les dents de la Terre (2)',
            'duration': 2877,
            'thumbnail': 'https://dl-revoir.tv5monde.com/images/1a/5753448.jpg'
        },
    }, {
        # movie
        'url': 'https://revoir.tv5monde.com/toutes-les-videos/cinema/ceux-qui-travaillent',
        'md5': '32fa0cde16a4480d1251502a66856d5f',
        'info_dict': {
            'id': 'dc57a011-ec4b-4648-2a9a-4f03f8352ed3',
            'display_id': 'ceux-qui-travaillent',
            'ext': 'mp4',
            'title': 'Ceux qui travaillent',
            'description': 'md5:570e8bb688036ace873b2d50d24c026d',
            'upload_date': '20210819',
        },
        'skip': 'no longer available',
    }, {
        # series episode
        'url': 'https://revoir.tv5monde.com/toutes-les-videos/series-fictions/vestiaires-caro-actrice',
        'info_dict': {
            'id': '9e9d599e-23af-6915-843e-ecbf62e97925',
            'display_id': 'vestiaires-caro-actrice',
            'ext': 'mp4',
            'title': "Vestiaires - Caro actrice",
            'description': 'md5:db15d2e1976641e08377f942778058ea',
            'upload_date': '20210819',
            'series': "Vestiaires",
            'episode': 'Caro actrice',
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'no longer available',
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
        video_id = None

        def process_video_files(v):
            nonlocal video_id
            for video_file in v:
                v_url = video_file.get('url')
                if not v_url:
                    continue
                if video_file.get('type') == 'application/deferred':
                    d_param = urllib.parse.quote(v_url)
                    token = video_file.get('token')
                    if not token:
                        continue
                    deferred_json = self._download_json(
                        f'https://api.tv5monde.com/player/asset/{d_param}/resolve?condenseKS=true', display_id,
                        note='Downloading deferred info', headers={'Authorization': f'Bearer {token}'}, fatal=False)
                    v_url = traverse_obj(deferred_json, (0, 'url', {url_or_none}))
                    if not v_url:
                        continue
                    # data-guid from the webpage isn't stable, use the material id from the json urls
                    video_id = self._search_regex(
                        r'materials/([\da-zA-Z]{10}_[\da-fA-F]{7})/', v_url, 'video id', default=None)
                    process_video_files(deferred_json)

                video_format = video_file.get('format') or determine_ext(v_url)
                if video_format == 'm3u8':
                    formats.extend(self._extract_m3u8_formats(
                        v_url, display_id, 'mp4', 'm3u8_native',
                        m3u8_id='hls', fatal=False))
                elif video_format == 'mpd':
                    formats.extend(self._extract_mpd_formats(
                        v_url, display_id, fatal=False))
                else:
                    formats.append({
                        'url': v_url,
                        'format_id': video_format,
                    })

        process_video_files(video_files)

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
