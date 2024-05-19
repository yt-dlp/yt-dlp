import re
import urllib.parse

from .common import InfoExtractor
from .dailymotion import DailymotionIE
from ..networking import HEADRequest
from ..utils import (
    determine_ext,
    filter_dict,
    format_field,
    int_or_none,
    join_nonempty,
    parse_iso8601,
    smuggle_url,
    unsmuggle_url,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class FranceTVBaseInfoExtractor(InfoExtractor):
    def _make_url_result(self, video_id, url=None):
        video_id = video_id.split('@')[0]  # for compat with old @catalog IDs
        full_id = f'francetv:{video_id}'
        if url:
            full_id = smuggle_url(full_id, {'hostname': urllib.parse.urlparse(url).hostname})
        return self.url_result(full_id, FranceTVIE, video_id)


class FranceTVIE(InfoExtractor):
    _VALID_URL = r'francetv:(?P<id>[^@#]+)'
    _GEO_COUNTRIES = ['FR']
    _GEO_BYPASS = False

    _TESTS = [{
        'url': 'francetv:ec217ecc-0733-48cf-ac06-af1347b849d1',
        'info_dict': {
            'id': 'ec217ecc-0733-48cf-ac06-af1347b849d1',
            'ext': 'mp4',
            'title': '13h15, le dimanche... - Les mystères de Jésus',
            'timestamp': 1502623500,
            'duration': 2580,
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20170813',
        },
        'params': {'skip_download': 'm3u8'},
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

    def _extract_video(self, video_id, hostname=None):
        is_live = None
        videos = []
        title = None
        subtitle = None
        episode_number = None
        season_number = None
        image = None
        duration = None
        timestamp = None
        spritesheets = None

        # desktop+chrome returns dash; mobile+safari returns hls
        for device_type, browser in [('desktop', 'chrome'), ('mobile', 'safari')]:
            dinfo = self._download_json(
                f'https://k7.ftven.fr/videos/{video_id}', video_id,
                f'Downloading {device_type} {browser} video JSON', query=filter_dict({
                    'device_type': device_type,
                    'browser': browser,
                    'domain': hostname,
                }), fatal=False)

            if not dinfo:
                continue

            video = traverse_obj(dinfo, ('video', {dict}))
            if video:
                videos.append(video)
                if duration is None:
                    duration = video.get('duration')
                if is_live is None:
                    is_live = video.get('is_live')
                if spritesheets is None:
                    spritesheets = video.get('spritesheets')

            meta = traverse_obj(dinfo, ('meta', {dict}))
            if meta:
                if title is None:
                    title = meta.get('title')
                # meta['pre_title'] contains season and episode number for series in format "S<ID> E<ID>"
                season_number, episode_number = self._search_regex(
                    r'S(\d+)\s*E(\d+)', meta.get('pre_title'), 'episode info', group=(1, 2), default=(None, None))
                if subtitle is None:
                    subtitle = meta.get('additional_title')
                if image is None:
                    image = meta.get('image_url')
                if timestamp is None:
                    timestamp = parse_iso8601(meta.get('broadcasted_at'))

        formats, subtitles, video_url = [], {}, None
        for video in traverse_obj(videos, lambda _, v: url_or_none(v['url'])):
            video_url = video['url']
            format_id = video.get('format')

            if token_url := url_or_none(video.get('token')):
                tokenized_url = traverse_obj(self._download_json(
                    token_url, video_id, f'Downloading signed {format_id} manifest URL',
                    fatal=False, query={
                        'format': 'json',
                        'url': video_url,
                    }), ('url', {url_or_none}))
                if tokenized_url:
                    video_url = tokenized_url

            ext = determine_ext(video_url)
            if ext == 'f4m':
                formats.extend(self._extract_f4m_formats(
                    video_url, video_id, f4m_id=format_id or ext, fatal=False))
            elif ext == 'm3u8':
                format_id = format_id or 'hls'
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    video_url, video_id, 'mp4', m3u8_id=format_id, fatal=False)
                for f in traverse_obj(fmts, lambda _, v: v['vcodec'] == 'none' and v.get('tbr') is None):
                    if mobj := re.match(rf'{format_id}-[Aa]udio-\w+-(?P<bitrate>\d+)', f['format_id']):
                        f.update({
                            'tbr': int_or_none(mobj.group('bitrate')),
                            'acodec': 'mp4a',
                        })
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            elif ext == 'mpd':
                fmts, subs = self._extract_mpd_formats_and_subtitles(
                    video_url, video_id, mpd_id=format_id or 'dash', fatal=False)
                formats.extend(fmts)
                self._merge_subtitles(subs, target=subtitles)
            elif video_url.startswith('rtmp'):
                formats.append({
                    'url': video_url,
                    'format_id': join_nonempty('rtmp', format_id),
                    'ext': 'flv',
                })
            else:
                if self._is_valid_url(video_url, video_id, format_id):
                    formats.append({
                        'url': video_url,
                        'format_id': format_id,
                    })

            # XXX: what is video['captions']?

        if not formats and video_url:
            urlh = self._request_webpage(
                HEADRequest(video_url), video_id, 'Checking for geo-restriction',
                fatal=False, expected_status=403)
            if urlh and urlh.headers.get('x-errortype') == 'geo':
                self.raise_geo_restricted(countries=self._GEO_COUNTRIES, metadata_available=True)

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
                } for sheet in traverse_obj(spritesheets, (..., {url_or_none}))]
            })

        return {
            'id': video_id,
            'title': join_nonempty(title, subtitle, delim=' - ').strip(),
            'thumbnail': image,
            'duration': duration,
            'timestamp': timestamp,
            'is_live': is_live,
            'formats': formats,
            'subtitles': subtitles,
            'episode': subtitle if episode_number else None,
            'series': title if episode_number else None,
            'episode_number': int_or_none(episode_number),
            'season_number': int_or_none(season_number),
            '_format_sort_fields': ('res', 'tbr', 'proto'),  # prioritize m3u8 over dash
        }

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        video_id = self._match_id(url)
        hostname = smuggled_data.get('hostname') or 'www.france.tv'

        return self._extract_video(video_id, hostname=hostname)


class FranceTVSiteIE(FranceTVBaseInfoExtractor):
    _VALID_URL = r'https?://(?:(?:www\.)?france\.tv|mobile\.france\.tv)/(?:[^/]+/)*(?P<id>[^/]+)\.html'

    _TESTS = [{
        'url': 'https://www.france.tv/france-2/13h15-le-dimanche/140921-les-mysteres-de-jesus.html',
        'info_dict': {
            'id': 'ec217ecc-0733-48cf-ac06-af1347b849d1',
            'ext': 'mp4',
            'title': '13h15, le dimanche... - Les mystères de Jésus',
            'timestamp': 1502623500,
            'duration': 2580,
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20170813',
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': [FranceTVIE.ie_key()],
    }, {
        # geo-restricted
        'url': 'https://www.france.tv/enfants/six-huit-ans/foot2rue/saison-1/3066387-duel-au-vieux-port.html',
        'info_dict': {
            'id': 'a9050959-eedd-4b4a-9b0d-de6eeaa73e44',
            'ext': 'mp4',
            'title': 'Foot2Rue - Duel au vieux port',
            'episode': 'Duel au vieux port',
            'series': 'Foot2Rue',
            'episode_number': 1,
            'season_number': 1,
            'timestamp': 1642761360,
            'upload_date': '20220121',
            'season': 'Season 1',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 1441,
        },
    }, {
        # geo-restricted livestream (workflow == 'token-akamai')
        'url': 'https://www.france.tv/france-4/direct.html',
        'info_dict': {
            'id': '9a6a7670-dde9-4264-adbc-55b89558594b',
            'ext': 'mp4',
            'title': r're:France 4 en direct .+',
            'live_status': 'is_live',
        },
        'skip': 'geo-restricted livestream',
    }, {
        # livestream (workflow == 'dai')
        'url': 'https://www.france.tv/france-2/direct.html',
        'info_dict': {
            'id': '006194ea-117d-4bcf-94a9-153d999c59ae',
            'ext': 'mp4',
            'title': r're:France 2 en direct .+',
            'live_status': 'is_live',
        },
        'params': {'skip_download': 'livestream'},
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

        video_id = self._search_regex(
            r'(?:data-main-video\s*=|videoId["\']?\s*[:=])\s*(["\'])(?P<id>(?:(?!\1).)+)\1',
            webpage, 'video id', default=None, group='id')

        if not video_id:
            video_id = self._html_search_regex(
                r'(?:href=|player\.setVideo\(\s*)"http://videos?\.francetv\.fr/video/([^@"]+@[^"]+)"',
                webpage, 'video ID')

        return self._make_url_result(video_id, url=url)


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
            'timestamp': 1566510730,
            'thumbnail': r're:^https?://.*\.jpe?g$',
            'duration': 1637,
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
            'title': 'Covid-19 : une situation catastrophique à New Dehli - Édition du mercredi 21 avril 2021',
            'thumbnail': r're:^https?://.*\.jpe?g$',
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
            'description': 'md5:fdcb582c370756293a65cdfbc6ecd90e',
            'timestamp': 1467011958,
            'uploader': 'France Inter',
            'uploader_id': 'x2q2ez',
            'upload_date': '20160627',
            'view_count': int,
            'tags': ['Politique', 'France Inter', '27 juin 2016', 'Linvité de 8h20', 'Cécile Duflot', 'Patrick Cohen'],
            'age_limit': 0,
            'duration': 640,
            'like_count': int,
            'thumbnail': r're:https://[^/?#]+/v/[^/?#]+/x1080',
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

        dailymotion_urls = tuple(DailymotionIE._extract_embed_urls(url, webpage))
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

        return self._make_url_result(video_id, url=url)
