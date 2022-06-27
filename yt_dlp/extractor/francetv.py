from .common import InfoExtractor
from ..utils import (
    determine_ext,
    ExtractorError,
    format_field,
    parse_iso8601,
    parse_qs,
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
        is_live = None
        videos = []
        title = None
        subtitle = None
        image = None
        duration = None
        timestamp = None
        spritesheets = None

        for device_type in ('desktop', 'mobile'):
            dinfo = self._download_json(
                'https://player.webservices.francetelevisions.fr/v1/videos/%s' % video_id,
                video_id, 'Downloading %s video JSON' % device_type, query={
                    'device_type': device_type,
                    'browser': 'chrome',
                }, fatal=False)

            if not dinfo:
                continue

            video = dinfo.get('video')
            if video:
                videos.append(video)
                if duration is None:
                    duration = video.get('duration')
                if is_live is None:
                    is_live = video.get('is_live')
                if spritesheets is None:
                    spritesheets = video.get('spritesheets')

            meta = dinfo.get('meta')
            if meta:
                if title is None:
                    title = meta.get('title')
                # XXX: what is meta['pre_title']?
                if subtitle is None:
                    subtitle = meta.get('additional_title')
                if image is None:
                    image = meta.get('image_url')
                if timestamp is None:
                    timestamp = parse_iso8601(meta.get('broadcasted_at'))

        formats = []
        subtitles = {}
        for video in videos:
            format_id = video.get('format')

            video_url = None
            if video.get('workflow') == 'token-akamai':
                token_url = video.get('token')
                if token_url:
                    token_json = self._download_json(
                        token_url, video_id,
                        'Downloading signed %s manifest URL' % format_id)
                    if token_json:
                        video_url = token_json.get('url')
            if not video_url:
                video_url = video.get('url')

            ext = determine_ext(video_url)
            if ext == 'f4m':
                formats.extend(self._extract_f4m_formats(
                    video_url, video_id, f4m_id=format_id, fatal=False))
            elif ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    video_url, video_id, 'mp4',
                    entry_protocol='m3u8_native', m3u8_id=format_id,
                    fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            elif ext == 'mpd':
                fmts, subs = self._extract_mpd_formats_and_subtitles(
                    video_url, video_id, mpd_id=format_id, fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
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

            # XXX: what is video['captions']?

        for f in formats:
            if f.get('acodec') != 'none' and f.get('language') in ('qtz', 'qad'):
                f['language_preference'] = -10
                f['format_note'] = 'audio description%s' % format_field(f, 'format_note', ', %s')

        if spritesheets:
            formats.append({
                'format_id': 'spritesheets',
                'format_note': 'storyboard',
                'acodec': 'none',
                'vcodec': 'none',
                'ext': 'mhtml',
                'protocol': 'mhtml',
                'url': 'about:invalid',
                'fragments': [{
                    'url': sheet,
                    # XXX: not entirely accurate; each spritesheet seems to be
                    # a 10×10 grid of thumbnails corresponding to approximately
                    # 2 seconds of the video; the last spritesheet may be shorter
                    'duration': 200,
                } for sheet in spritesheets]
            })

        self._sort_formats(formats)

        if subtitle:
            title += ' - %s' % subtitle
        title = title.strip()

        return {
            'id': video_id,
            'title': title,
            'thumbnail': image,
            'duration': duration,
            'timestamp': timestamp,
            'is_live': is_live,
            'formats': formats,
            'subtitles': subtitles,
        }

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        catalog = mobj.group('catalog')

        if not video_id:
            qs = parse_qs(url)
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
        'note': 'Only an image exists in initial webpage instead of the video',
        'url': 'https://www.francetvinfo.fr/sante/maladie/coronavirus/covid-19-en-inde-une-situation-catastrophique-a-new-dehli_4381095.html',
        'info_dict': {
            'id': '7d204c9e-a2d3-11eb-9e4c-000d3a23d482',
            'ext': 'mp4',
            'title': 'Covid-19 : une situation catastrophique à New Dehli',
            'thumbnail': str,
            'duration': 76,
            'timestamp': 1619028518,
            'upload_date': '20210421',
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
    }, {
        # "<figure id=" pattern (#28792)
        'url': 'https://www.francetvinfo.fr/culture/patrimoine/incendie-de-notre-dame-de-paris/notre-dame-de-paris-de-l-incendie-de-la-cathedrale-a-sa-reconstruction_4372291.html',
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
             r'(?:data-id|<figure[^<]+\bid)=["\']([\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})'),
            webpage, 'video id')

        return self._make_url_result(video_id)
