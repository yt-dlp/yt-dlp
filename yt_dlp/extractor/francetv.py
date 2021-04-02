# coding: utf-8

from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import (
    compat_str,
    compat_urlparse,
)
from ..utils import (
    clean_html,
    determine_ext,
    ExtractorError,
    int_or_none,
    parse_duration,
    try_get,
    url_or_none,
    urljoin,
)
from .dailymotion import DailymotionIE


class FranceTVBaseInfoExtractor(InfoExtractor):
    def _make_url_result(self, video_or_full_id, catalog=None):
        full_id = 'francetv:%s' % video_or_full_id
        if '@' not in video_or_full_id and catalog:
            full_id += '@%s' % catalog
        return self.url_result(
            full_id, ie=FranceTVIE.ie_key(),
            video_id=video_or_full_id.split('@')[0])


class FranceTVIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    (?:
                        https?://
                            sivideo\.webservices\.francetelevisions\.fr/tools/getInfosOeuvre/v2/\?
                            .*?\bidDiffusion=[^&]+|
                        (?:
                            https?://videos\.francetv\.fr/video/|
                            francetv:
                        )
                        (?P<id>[^@]+)(?:@(?P<catalog>.+))?
                    )
                    '''

    _TESTS = [{
        # without catalog
        'url': 'https://sivideo.webservices.francetelevisions.fr/tools/getInfosOeuvre/v2/?idDiffusion=162311093&callback=_jsonp_loader_callback_request_0',
        'md5': 'c2248a8de38c4e65ea8fae7b5df2d84f',
        'info_dict': {
            'id': '162311093',
            'ext': 'mp4',
            'title': '13h15, le dimanche... - Les mystères de Jésus',
            'description': 'md5:75efe8d4c0a8205e5904498ffe1e1a42',
            'timestamp': 1502623500,
            'upload_date': '20170813',
        },
    }, {
        # with catalog
        'url': 'https://sivideo.webservices.francetelevisions.fr/tools/getInfosOeuvre/v2/?idDiffusion=NI_1004933&catalogue=Zouzous&callback=_jsonp_loader_callback_request_4',
        'only_matching': True,
    }, {
        'url': 'http://videos.francetv.fr/video/NI_657393@Regions',
        'only_matching': True,
    }, {
        'url': 'francetv:162311093',
        'only_matching': True,
    }, {
        'url': 'francetv:NI_1004933@Zouzous',
        'only_matching': True,
    }, {
        'url': 'francetv:NI_983319@Info-web',
        'only_matching': True,
    }, {
        'url': 'francetv:NI_983319',
        'only_matching': True,
    }, {
        'url': 'francetv:NI_657393@Regions',
        'only_matching': True,
    }, {
        # france-3 live
        'url': 'francetv:SIM_France3',
        'only_matching': True,
    }]

    def _extract_video(self, video_id, catalogue=None):
        # Videos are identified by idDiffusion so catalogue part is optional.
        # However when provided, some extra formats may be returned so we pass
        # it if available.
        info = self._download_json(
            'https://sivideo.webservices.francetelevisions.fr/tools/getInfosOeuvre/v2/',
            video_id, 'Downloading video JSON', query={
                'idDiffusion': video_id,
                'catalogue': catalogue or '',
            })

        if info.get('status') == 'NOK':
            raise ExtractorError(
                '%s returned error: %s' % (self.IE_NAME, info['message']),
                expected=True)
        allowed_countries = info['videos'][0].get('geoblocage')
        if allowed_countries:
            georestricted = True
            geo_info = self._download_json(
                'http://geo.francetv.fr/ws/edgescape.json', video_id,
                'Downloading geo restriction info')
            country = geo_info['reponse']['geo_info']['country_code']
            if country not in allowed_countries:
                raise ExtractorError(
                    'The video is not available from your location',
                    expected=True)
        else:
            georestricted = False

        def sign(manifest_url, manifest_id):
            for host in ('hdfauthftv-a.akamaihd.net', 'hdfauth.francetv.fr'):
                signed_url = url_or_none(self._download_webpage(
                    'https://%s/esi/TA' % host, video_id,
                    'Downloading signed %s manifest URL' % manifest_id,
                    fatal=False, query={
                        'url': manifest_url,
                    }))
                if signed_url:
                    return signed_url
            return manifest_url

        is_live = None

        videos = []

        for video in (info.get('videos') or []):
            if video.get('statut') != 'ONLINE':
                continue
            if not video.get('url'):
                continue
            videos.append(video)

        if not videos:
            for device_type in ['desktop', 'mobile']:
                fallback_info = self._download_json(
                    'https://player.webservices.francetelevisions.fr/v1/videos/%s' % video_id,
                    video_id, 'Downloading fallback %s video JSON' % device_type, query={
                        'device_type': device_type,
                        'browser': 'chrome',
                    }, fatal=False)

                if fallback_info and fallback_info.get('video'):
                    videos.append(fallback_info['video'])

        formats = []
        for video in videos:
            video_url = video.get('url')
            if not video_url:
                continue
            if is_live is None:
                is_live = (try_get(
                    video, lambda x: x['plages_ouverture'][0]['direct'], bool) is True
                    or video.get('is_live') is True
                    or '/live.francetv.fr/' in video_url)
            format_id = video.get('format')
            ext = determine_ext(video_url)
            if ext == 'f4m':
                if georestricted:
                    # See https://github.com/ytdl-org/youtube-dl/issues/3963
                    # m3u8 urls work fine
                    continue
                formats.extend(self._extract_f4m_formats(
                    sign(video_url, format_id) + '&hdcore=3.7.0&plugin=aasp-3.7.0.39.44',
                    video_id, f4m_id=format_id, fatal=False))
            elif ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    sign(video_url, format_id), video_id, 'mp4',
                    entry_protocol='m3u8_native', m3u8_id=format_id,
                    fatal=False))
            elif ext == 'mpd':
                formats.extend(self._extract_mpd_formats(
                    sign(video_url, format_id), video_id, mpd_id=format_id, fatal=False))
            elif video_url.startswith('rtmp'):
                formats.append({
                    'url': video_url,
                    'format_id': 'rtmp-%s' % format_id,
                    'ext': 'flv',
                })
            else:
                if self._is_valid_url(video_url, video_id, format_id):
                    formats.append({
                        'url': video_url,
                        'format_id': format_id,
                    })

        self._sort_formats(formats)

        title = info['titre']
        subtitle = info.get('sous_titre')
        if subtitle:
            title += ' - %s' % subtitle
        title = title.strip()

        subtitles = {}
        subtitles_list = [{
            'url': subformat['url'],
            'ext': subformat.get('format'),
        } for subformat in info.get('subtitles', []) if subformat.get('url')]
        if subtitles_list:
            subtitles['fr'] = subtitles_list

        return {
            'id': video_id,
            'title': self._live_title(title) if is_live else title,
            'description': clean_html(info.get('synopsis')),
            'thumbnail': urljoin('https://sivideo.webservices.francetelevisions.fr', info.get('image')),
            'duration': int_or_none(info.get('real_duration')) or parse_duration(info.get('duree')),
            'timestamp': int_or_none(try_get(info, lambda x: x['diffusion']['timestamp'])),
            'is_live': is_live,
            'formats': formats,
            'subtitles': subtitles,
        }

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')
        catalog = mobj.group('catalog')

        if not video_id:
            qs = compat_urlparse.parse_qs(compat_urlparse.urlparse(url).query)
            video_id = qs.get('idDiffusion', [None])[0]
            catalog = qs.get('catalogue', [None])[0]
            if not video_id:
                raise ExtractorError('Invalid URL', expected=True)

        return self._extract_video(video_id, catalog)


class FranceTVSiteIE(FranceTVBaseInfoExtractor):
    _VALID_URL = r'https?://(?:(?:www\.)?france\.tv|mobile\.france\.tv)/(?:[^/]+/)*(?P<id>[^/]+)\.html'

    _TESTS = [{
        'url': 'https://www.france.tv/france-2/13h15-le-dimanche/140921-les-mysteres-de-jesus.html',
        'info_dict': {
            'id': 'ec217ecc-0733-48cf-ac06-af1347b849d1',
            'ext': 'mp4',
            'title': '13h15, le dimanche... - Les mystères de Jésus',
            'description': 'md5:75efe8d4c0a8205e5904498ffe1e1a42',
            'timestamp': 1502623500,
            'upload_date': '20170813',
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': [FranceTVIE.ie_key()],
    }, {
        # france3
        'url': 'https://www.france.tv/france-3/des-chiffres-et-des-lettres/139063-emission-du-mardi-9-mai-2017.html',
        'only_matching': True,
    }, {
        # france4
        'url': 'https://www.france.tv/france-4/hero-corp/saison-1/134151-apres-le-calme.html',
        'only_matching': True,
    }, {
        # france5
        'url': 'https://www.france.tv/france-5/c-a-dire/saison-10/137013-c-a-dire.html',
        'only_matching': True,
    }, {
        # franceo
        'url': 'https://www.france.tv/france-o/archipels/132249-mon-ancetre-l-esclave.html',
        'only_matching': True,
    }, {
        # france2 live
        'url': 'https://www.france.tv/france-2/direct.html',
        'only_matching': True,
    }, {
        'url': 'https://www.france.tv/documentaires/histoire/136517-argentine-les-500-bebes-voles-de-la-dictature.html',
        'only_matching': True,
    }, {
        'url': 'https://www.france.tv/jeux-et-divertissements/divertissements/133965-le-web-contre-attaque.html',
        'only_matching': True,
    }, {
        'url': 'https://mobile.france.tv/france-5/c-dans-l-air/137347-emission-du-vendredi-12-mai-2017.html',
        'only_matching': True,
    }, {
        'url': 'https://www.france.tv/142749-rouge-sang.html',
        'only_matching': True,
    }, {
        # france-3 live
        'url': 'https://www.france.tv/france-3/direct.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        catalogue = None
        video_id = self._search_regex(
            r'(?:data-main-video\s*=|videoId["\']?\s*[:=])\s*(["\'])(?P<id>(?:(?!\1).)+)\1',
            webpage, 'video id', default=None, group='id')

        if not video_id:
            video_id, catalogue = self._html_search_regex(
                r'(?:href=|player\.setVideo\(\s*)"http://videos?\.francetv\.fr/video/([^@]+@[^"]+)"',
                webpage, 'video ID').split('@')

        return self._make_url_result(video_id, catalogue)


class FranceTVEmbedIE(FranceTVBaseInfoExtractor):
    _VALID_URL = r'https?://embed\.francetv\.fr/*\?.*?\bue=(?P<id>[^&]+)'

    _TESTS = [{
        'url': 'http://embed.francetv.fr/?ue=7fd581a2ccf59d2fc5719c5c13cf6961',
        'info_dict': {
            'id': 'NI_983319',
            'ext': 'mp4',
            'title': 'Le Pen Reims',
            'upload_date': '20170505',
            'timestamp': 1493981780,
            'duration': 16,
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': [FranceTVIE.ie_key()],
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video = self._download_json(
            'http://api-embed.webservices.francetelevisions.fr/key/%s' % video_id,
            video_id)

        return self._make_url_result(video['video_id'], video.get('catalog'))


class FranceTVInfoIE(FranceTVBaseInfoExtractor):
    IE_NAME = 'francetvinfo.fr'
    _VALID_URL = r'https?://(?:www|mobile|france3-regions)\.francetvinfo\.fr/(?:[^/]+/)*(?P<id>[^/?#&.]+)'

    _TESTS = [{
        'url': 'https://www.francetvinfo.fr/replay-jt/france-3/soir-3/jt-grand-soir-3-jeudi-22-aout-2019_3561461.html',
        'info_dict': {
            'id': 'd12458ee-5062-48fe-bfdd-a30d6a01b793',
            'ext': 'mp4',
            'title': 'Soir 3',
            'upload_date': '20190822',
            'timestamp': 1566510900,
            'description': 'md5:72d167097237701d6e8452ff03b83c00',
            'subtitles': {
                'fr': 'mincount:2',
            },
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': [FranceTVIE.ie_key()],
    }, {
        'url': 'http://www.francetvinfo.fr/elections/europeennes/direct-europeennes-regardez-le-debat-entre-les-candidats-a-la-presidence-de-la-commission_600639.html',
        'only_matching': True,
    }, {
        'url': 'http://www.francetvinfo.fr/economie/entreprises/les-entreprises-familiales-le-secret-de-la-reussite_933271.html',
        'only_matching': True,
    }, {
        'url': 'http://france3-regions.francetvinfo.fr/bretagne/cotes-d-armor/thalassa-echappee-breizh-ce-venredi-dans-les-cotes-d-armor-954961.html',
        'only_matching': True,
    }, {
        # Dailymotion embed
        'url': 'http://www.francetvinfo.fr/politique/notre-dame-des-landes/video-sur-france-inter-cecile-duflot-denonce-le-regard-meprisant-de-patrick-cohen_1520091.html',
        'md5': 'ee7f1828f25a648addc90cb2687b1f12',
        'info_dict': {
            'id': 'x4iiko0',
            'ext': 'mp4',
            'title': 'NDDL, référendum, Brexit : Cécile Duflot répond à Patrick Cohen',
            'description': 'Au lendemain de la victoire du "oui" au référendum sur l\'aéroport de Notre-Dame-des-Landes, l\'ancienne ministre écologiste est l\'invitée de Patrick Cohen. Plus d\'info : https://www.franceinter.fr/emissions/le-7-9/le-7-9-27-juin-2016',
            'timestamp': 1467011958,
            'upload_date': '20160627',
            'uploader': 'France Inter',
            'uploader_id': 'x2q2ez',
        },
        'add_ie': ['Dailymotion'],
    }, {
        'url': 'http://france3-regions.francetvinfo.fr/limousin/emissions/jt-1213-limousin',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        dailymotion_urls = DailymotionIE._extract_urls(webpage)
        if dailymotion_urls:
            return self.playlist_result([
                self.url_result(dailymotion_url, DailymotionIE.ie_key())
                for dailymotion_url in dailymotion_urls])

        video_id = self._search_regex(
            (r'player\.load[^;]+src:\s*["\']([^"\']+)',
             r'id-video=([^@]+@[^"]+)',
             r'<a[^>]+href="(?:https?:)?//videos\.francetv\.fr/video/([^@]+@[^"]+)"',
             r'data-id=["\']([\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})'),
            webpage, 'video id')

        return self._make_url_result(video_id)


class FranceTVInfoSportIE(FranceTVBaseInfoExtractor):
    IE_NAME = 'sport.francetvinfo.fr'
    _VALID_URL = r'https?://sport\.francetvinfo\.fr/(?:[^/]+/)*(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://sport.francetvinfo.fr/les-jeux-olympiques/retour-sur-les-meilleurs-moments-de-pyeongchang-2018',
        'info_dict': {
            'id': '6e49080e-3f45-11e8-b459-000d3a2439ea',
            'ext': 'mp4',
            'title': 'Retour sur les meilleurs moments de Pyeongchang 2018',
            'timestamp': 1523639962,
            'upload_date': '20180413',
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': [FranceTVIE.ie_key()],
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        video_id = self._search_regex(r'data-video="([^"]+)"', webpage, 'video_id')
        return self._make_url_result(video_id, 'Sport-web')


class GenerationWhatIE(InfoExtractor):
    IE_NAME = 'france2.fr:generation-what'
    _VALID_URL = r'https?://generation-what\.francetv\.fr/[^/]+/video/(?P<id>[^/?#&]+)'

    _TESTS = [{
        'url': 'http://generation-what.francetv.fr/portrait/video/present-arms',
        'info_dict': {
            'id': 'wtvKYUG45iw',
            'ext': 'mp4',
            'title': 'Generation What - Garde à vous - FRA',
            'uploader': 'Generation What',
            'uploader_id': 'UCHH9p1eetWCgt4kXBYCb3_w',
            'upload_date': '20160411',
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': ['Youtube'],
    }, {
        'url': 'http://generation-what.francetv.fr/europe/video/present-arms',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        youtube_id = self._search_regex(
            r"window\.videoURL\s*=\s*'([0-9A-Za-z_-]{11})';",
            webpage, 'youtube id')

        return self.url_result(youtube_id, ie='Youtube', video_id=youtube_id)


class CultureboxIE(FranceTVBaseInfoExtractor):
    _VALID_URL = r'https?://(?:m\.)?culturebox\.francetvinfo\.fr/(?:[^/]+/)*(?P<id>[^/?#&]+)'

    _TESTS = [{
        'url': 'https://culturebox.francetvinfo.fr/opera-classique/musique-classique/c-est-baroque/concerts/cantates-bwv-4-106-et-131-de-bach-par-raphael-pichon-57-268689',
        'info_dict': {
            'id': 'EV_134885',
            'ext': 'mp4',
            'title': 'Cantates BWV 4, 106 et 131 de Bach par Raphaël Pichon 5/7',
            'description': 'md5:19c44af004b88219f4daa50fa9a351d4',
            'upload_date': '20180206',
            'timestamp': 1517945220,
            'duration': 5981,
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': [FranceTVIE.ie_key()],
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        if ">Ce live n'est plus disponible en replay<" in webpage:
            raise ExtractorError(
                'Video %s is not available' % display_id, expected=True)

        video_id, catalogue = self._search_regex(
            r'["\'>]https?://videos\.francetv\.fr/video/([^@]+@.+?)["\'<]',
            webpage, 'video id').split('@')

        return self._make_url_result(video_id, catalogue)


class FranceTVJeunesseIE(FranceTVBaseInfoExtractor):
    _VALID_URL = r'(?P<url>https?://(?:www\.)?(?:zouzous|ludo)\.fr/heros/(?P<id>[^/?#&]+))'

    _TESTS = [{
        'url': 'https://www.zouzous.fr/heros/simon',
        'info_dict': {
            'id': 'simon',
        },
        'playlist_count': 9,
    }, {
        'url': 'https://www.ludo.fr/heros/ninjago',
        'info_dict': {
            'id': 'ninjago',
        },
        'playlist_count': 10,
    }, {
        'url': 'https://www.zouzous.fr/heros/simon?abc',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        playlist_id = mobj.group('id')

        playlist = self._download_json(
            '%s/%s' % (mobj.group('url'), 'playlist'), playlist_id)

        if not playlist.get('count'):
            raise ExtractorError(
                '%s is not available' % playlist_id, expected=True)

        entries = []
        for item in playlist['items']:
            identity = item.get('identity')
            if identity and isinstance(identity, compat_str):
                entries.append(self._make_url_result(identity))

        return self.playlist_result(entries, playlist_id)
