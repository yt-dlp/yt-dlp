from .common import InfoExtractor
from ..compat import (
    compat_parse_qs,
    compat_urllib_parse_urlparse,
)
from ..utils import (
    dict_get,
    int_or_none,
    parse_duration,
    unified_timestamp,
)


class SkyItPlayerIE(InfoExtractor):
    IE_NAME = 'player.sky.it'
    _VALID_URL = r'https?://player\.sky\.it/player/(?:external|social)\.html\?.*?\bid=(?P<id>\d+)'
    _GEO_BYPASS = False
    _DOMAIN = 'sky'
    _PLAYER_TMPL = 'https://player.sky.it/player/external.html?id=%s&domain=%s'
    # http://static.sky.it/static/skyplayer/conf.json
    _TOKEN_MAP = {
        'cielo': 'Hh9O7M8ks5yi6nSROL7bKYz933rdf3GhwZlTLMgvy4Q',
        'hotclub': 'kW020K2jq2lk2eKRJD2vWEg832ncx2EivZlTLQput2C',
        'mtv8': 'A5Nn9GGb326CI7vP5e27d7E4PIaQjota',
        'salesforce': 'C6D585FD1615272C98DE38235F38BD86',
        'sitocommerciale': 'VJwfFuSGnLKnd9Phe9y96WkXgYDCguPMJ2dLhGMb2RE',
        'sky': 'F96WlOd8yoFmLQgiqv6fNQRvHZcsWk5jDaYnDvhbiJk',
        'skyacademy': 'A6LAn7EkO2Q26FRy0IAMBekX6jzDXYL3',
        'skyarte': 'LWk29hfiU39NNdq87ePeRach3nzTSV20o0lTv2001Cd',
        'theupfront': 'PRSGmDMsg6QMGc04Obpoy7Vsbn7i2Whp',
    }

    def _player_url_result(self, video_id):
        return self.url_result(
            self._PLAYER_TMPL % (video_id, self._DOMAIN),
            SkyItPlayerIE.ie_key(), video_id)

    def _parse_video(self, video, video_id):
        title = video['title']
        is_live = video.get('type') == 'live'
        hls_url = video.get(('streaming' if is_live else 'hls') + '_url')
        if not hls_url and video.get('geoblock' if is_live else 'geob'):
            self.raise_geo_restricted(countries=['IT'])

        if is_live:
            formats = self._extract_m3u8_formats(hls_url, video_id, 'mp4')
        else:
            formats = self._extract_akamai_formats(
                hls_url, video_id, {'http': 'videoplatform.sky.it'})
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': dict_get(video, ('video_still', 'video_still_medium', 'thumb')),
            'description': video.get('short_desc') or None,
            'timestamp': unified_timestamp(video.get('create_date')),
            'duration': int_or_none(video.get('duration_sec')) or parse_duration(video.get('duration')),
            'is_live': is_live,
        }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        domain = compat_parse_qs(compat_urllib_parse_urlparse(
            url).query).get('domain', [None])[0]
        token = dict_get(self._TOKEN_MAP, (domain, 'sky'))
        video = self._download_json(
            'https://apid.sky.it/vdp/v1/getVideoData',
            video_id, query={
                'caller': 'sky',
                'id': video_id,
                'token': token
            }, headers=self.geo_verification_headers())
        return self._parse_video(video, video_id)


class SkyItVideoIE(SkyItPlayerIE):
    IE_NAME = 'video.sky.it'
    _VALID_URL = r'https?://(?:masterchef|video|xfactor)\.sky\.it(?:/[^/]+)*/video/[0-9a-z-]+-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://video.sky.it/news/mondo/video/uomo-ucciso-da-uno-squalo-in-australia-631227',
        'md5': 'fe5c91e59a84a3437eaa0bca6e134ccd',
        'info_dict': {
            'id': '631227',
            'ext': 'mp4',
            'title': 'Uomo ucciso da uno squalo in Australia',
            'timestamp': 1606036192,
            'upload_date': '20201122',
        }
    }, {
        'url': 'https://xfactor.sky.it/video/x-factor-2020-replay-audizioni-1-615820',
        'only_matching': True,
    }, {
        'url': 'https://masterchef.sky.it/video/masterchef-9-cosa-e-successo-nella-prima-puntata-562831',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self._player_url_result(video_id)


class SkyItVideoLiveIE(SkyItPlayerIE):
    IE_NAME = 'video.sky.it:live'
    _VALID_URL = r'https?://video\.sky\.it/diretta/(?P<id>[^/?&#]+)'
    _TEST = {
        'url': 'https://video.sky.it/diretta/tg24',
        'info_dict': {
            'id': '1',
            'ext': 'mp4',
            'title': r're:Diretta TG24 \d{4}-\d{2}-\d{2} \d{2}:\d{2}',
            'description': 'Guarda la diretta streaming di SkyTg24, segui con Sky tutti gli appuntamenti e gli speciali di Tg24.',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        asset_id = str(self._search_nextjs_data(webpage, display_id)['props']['initialState']['livePage']['content']['asset_id'])
        livestream = self._download_json(
            'https://apid.sky.it/vdp/v1/getLivestream',
            asset_id, query={'id': asset_id})
        return self._parse_video(livestream, asset_id)


class SkyItIE(SkyItPlayerIE):
    IE_NAME = 'sky.it'
    _VALID_URL = r'https?://(?:sport|tg24)\.sky\.it(?:/[^/]+)*/\d{4}/\d{2}/\d{2}/(?P<id>[^/?&#]+)'
    _TESTS = [{
        'url': 'https://sport.sky.it/calcio/serie-a/2020/11/21/juventus-cagliari-risultato-gol',
        'info_dict': {
            'id': '631201',
            'ext': 'mp4',
            'title': 'Un rosso alla violenza: in campo per i diritti delle donne',
            'upload_date': '20201121',
            'timestamp': 1605995753,
        },
        'expected_warnings': ['Unable to download f4m manifest'],
    }, {
        'url': 'https://tg24.sky.it/mondo/2020/11/22/australia-squalo-uccide-uomo',
        'md5': 'fe5c91e59a84a3437eaa0bca6e134ccd',
        'info_dict': {
            'id': '631227',
            'ext': 'mp4',
            'title': 'Uomo ucciso da uno squalo in Australia',
            'timestamp': 1606036192,
            'upload_date': '20201122',
        },
    }]
    _VIDEO_ID_REGEX = r'data-videoid="(\d+)"'

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        video_id = self._search_regex(
            self._VIDEO_ID_REGEX, webpage, 'video id')
        return self._player_url_result(video_id)


class SkyItAcademyIE(SkyItIE):
    IE_NAME = 'skyacademy.it'
    _VALID_URL = r'https?://(?:www\.)?skyacademy\.it(?:/[^/]+)*/\d{4}/\d{2}/\d{2}/(?P<id>[^/?&#]+)'
    _TESTS = [{
        'url': 'https://www.skyacademy.it/eventi-speciali/2019/07/05/a-lezione-di-cinema-con-sky-academy-/',
        'md5': 'ced5c26638b7863190cbc44dd6f6ba08',
        'info_dict': {
            'id': '523458',
            'ext': 'mp4',
            'title': 'Sky Academy "The Best CineCamp 2019"',
            'timestamp': 1562843784,
            'upload_date': '20190711',
        }
    }]
    _DOMAIN = 'skyacademy'
    _VIDEO_ID_REGEX = r'id="news-videoId_(\d+)"'


class SkyItArteIE(SkyItIE):
    IE_NAME = 'arte.sky.it'
    _VALID_URL = r'https?://arte\.sky\.it/video/(?P<id>[^/?&#]+)'
    _TESTS = [{
        'url': 'https://arte.sky.it/video/serie-musei-venezia-collezionismo-12-novembre/',
        'md5': '515aee97b87d7a018b6c80727d3e7e17',
        'info_dict': {
            'id': '627926',
            'ext': 'mp4',
            'title': "Musei Galleria Franchetti alla Ca' d'Oro Palazzo Grimani",
            'upload_date': '20201106',
            'timestamp': 1604664493,
        }
    }]
    _DOMAIN = 'skyarte'
    _VIDEO_ID_REGEX = r'(?s)<iframe[^>]+src="(?:https:)?//player\.sky\.it/player/external\.html\?[^"]*\bid=(\d+)'


class CieloTVItIE(SkyItIE):
    IE_NAME = 'cielotv.it'
    _VALID_URL = r'https?://(?:www\.)?cielotv\.it/video/(?P<id>[^.]+)\.html'
    _TESTS = [{
        'url': 'https://www.cielotv.it/video/Il-lunedi-e-sempre-un-dramma.html',
        'md5': 'c4deed77552ba901c2a0d9258320304b',
        'info_dict': {
            'id': '499240',
            'ext': 'mp4',
            'title': 'Il lunedì è sempre un dramma',
            'upload_date': '20190329',
            'timestamp': 1553862178,
        }
    }]
    _DOMAIN = 'cielo'
    _VIDEO_ID_REGEX = r'videoId\s*=\s*"(\d+)"'


class TV8ItIE(SkyItVideoIE):
    IE_NAME = 'tv8.it'
    _VALID_URL = r'https?://tv8\.it/showvideo/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://tv8.it/showvideo/630529/ogni-mattina-ucciso-asino-di-andrea-lo-cicero/18-11-2020/',
        'md5': '9ab906a3f75ea342ed928442f9dabd21',
        'info_dict': {
            'id': '630529',
            'ext': 'mp4',
            'title': 'Ogni mattina - Ucciso asino di Andrea Lo Cicero',
            'timestamp': 1605721374,
            'upload_date': '20201118',
        }
    }]
    _DOMAIN = 'mtv8'
