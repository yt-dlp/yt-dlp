import urllib.parse

from .common import InfoExtractor
from ..utils import (
    clean_html,
    dict_get,
    int_or_none,
    parse_duration,
    unified_timestamp,
    url_or_none,
    urljoin,
)
from ..utils.traversal import traverse_obj


class SkyItBaseIE(InfoExtractor):
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
        'skyarte': 'LWk29hfiU39NNdq87ePeRach3nzTSV20o0lTv2001Cd',
        'theupfront': 'PRSGmDMsg6QMGc04Obpoy7Vsbn7i2Whp',
    }

    def _player_url_result(self, video_id):
        return self.url_result(
            self._PLAYER_TMPL % (video_id, self._DOMAIN),
            SkyItPlayerIE.ie_key(), video_id)

    def _parse_video(self, video, video_id):
        is_live = video.get('type') == 'live'
        hls_url = video.get(('streaming' if is_live else 'hls') + '_url')
        if not hls_url and video.get('geoblock' if is_live else 'geob'):
            self.raise_geo_restricted(countries=['IT'])

        formats = self._extract_m3u8_formats(hls_url, video_id, 'mp4')

        return {
            'id': video_id,
            'title': video.get('title'),
            'formats': formats,
            'thumbnail': dict_get(video, ('video_still', 'video_still_medium', 'thumb')),
            'description': video.get('short_desc') or None,
            'timestamp': unified_timestamp(video.get('create_date')),
            'duration': int_or_none(video.get('duration_sec')) or parse_duration(video.get('duration')),
            'is_live': is_live,
        }


class SkyItPlayerIE(SkyItBaseIE):
    IE_NAME = 'player.sky.it'
    _VALID_URL = r'https?://player\.sky\.it/player/(?:external|social)\.html\?.*?\bid=(?P<id>\d+)'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        domain = urllib.parse.parse_qs(urllib.parse.urlparse(
            url).query).get('domain', [None])[0]
        token = dict_get(self._TOKEN_MAP, (domain, 'sky'))
        video = self._download_json(
            'https://apid.sky.it/vdp/v1/getVideoData',
            video_id, query={
                'caller': 'sky',
                'id': video_id,
                'token': token,
            }, headers=self.geo_verification_headers())
        return self._parse_video(video, video_id)


class SkyItVideoIE(SkyItBaseIE):
    IE_NAME = 'video.sky.it'
    _VALID_URL = r'https?://(?:masterchef|video|xfactor)\.sky\.it(?:/[^/]+)*/video/[0-9a-z-]+-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://video.sky.it/news/mondo/video/uomo-ucciso-da-uno-squalo-in-australia-631227',
        'md5': '5b858a62d9ffe2ab77b397553024184a',
        'info_dict': {
            'id': '631227',
            'ext': 'mp4',
            'title': 'Uomo ucciso da uno squalo in Australia',
            'timestamp': 1606036192,
            'upload_date': '20201122',
            'duration': 26,
            'thumbnail': 'https://video.sky.it/captures/thumbs/631227/631227_thumb_880x494.jpg',
        },
        'params': {'skip_download': 'm3u8'},
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


class SkyItVideoLiveIE(SkyItBaseIE):
    IE_NAME = 'video.sky.it:live'
    _VALID_URL = r'https?://video\.sky\.it/diretta/(?P<id>[^/?&#]+)'
    _TEST = {
        'url': 'https://video.sky.it/diretta/tg24',
        'info_dict': {
            'id': '1',
            'ext': 'mp4',
            'title': r're:Diretta TG24 \d{4}-\d{2}-\d{2} \d{2}:\d{2}',
            'description': r're:(?:Clicca play e )?[Gg]uarda la diretta streaming di SkyTg24, segui con Sky tutti gli appuntamenti e gli speciali di Tg24\.',
            'live_status': 'is_live',
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


class SkyItIE(SkyItBaseIE):
    IE_NAME = 'sky.it'
    _VALID_URL = r'https?://(?:sport|tg24)\.sky\.it(?:/[^/]+)*/\d{4}/\d{2}/\d{2}/(?P<id>[^/?&#]+)'
    _TESTS = [{
        'url': 'https://sport.sky.it/calcio/serie-a/2022/11/03/brozovic-inter-news',
        'info_dict': {
            'id': '789222',
            'ext': 'mp4',
            'title': 'Brozovic con il gruppo: verso convocazione per Juve-Inter',
            'upload_date': '20221103',
            'timestamp': 1667484130,
            'duration': 22,
            'thumbnail': 'https://videoplatform.sky.it/still/2022/11/03/1667480526353_brozovic_videostill_1.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://tg24.sky.it/mondo/2020/11/22/australia-squalo-uccide-uomo',
        'md5': 'fe5c91e59a84a3437eaa0bca6e134ccd',
        'info_dict': {
            'id': '631227',
            'ext': 'mp4',
            'title': 'Uomo ucciso da uno squalo in Australia',
            'timestamp': 1606036192,
            'upload_date': '20201122',
            'duration': 26,
            'thumbnail': 'https://video.sky.it/captures/thumbs/631227/631227_thumb_880x494.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }]
    _VIDEO_ID_REGEX = r'data-videoid="(\d+)"'

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        video_id = self._search_regex(
            self._VIDEO_ID_REGEX, webpage, 'video id')
        return self._player_url_result(video_id)


class SkyItArteIE(SkyItIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'arte.sky.it'
    _VALID_URL = r'https?://arte\.sky\.it/video/(?P<id>[^/?&#]+)'
    _TESTS = [{
        'url': 'https://arte.sky.it/video/oliviero-toscani-torino-galleria-mazzoleni-788962',
        'md5': '515aee97b87d7a018b6c80727d3e7e17',
        'info_dict': {
            'id': '788962',
            'ext': 'mp4',
            'title': 'La fotografia di Oliviero Toscani conquista Torino',
            'upload_date': '20221102',
            'timestamp': 1667399996,
            'duration': 12,
            'thumbnail': 'https://videoplatform.sky.it/still/2022/11/02/1667396388552_oliviero-toscani-torino-galleria-mazzoleni_videostill_1.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }]
    _DOMAIN = 'skyarte'
    _VIDEO_ID_REGEX = r'"embedUrl"\s*:\s*"(?:https:)?//player\.sky\.it/player/external\.html\?[^"]*\bid=(\d+)'


class CieloTVItIE(SkyItIE):  # XXX: Do not subclass from concrete IE
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
            'duration': 30,
            'thumbnail': 'https://videoplatform.sky.it/still/2019/03/29/1553858575610_lunedi_dramma_mant_videostill_1.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }]
    _DOMAIN = 'cielo'
    _VIDEO_ID_REGEX = r'videoId\s*=\s*"(\d+)"'


class TV8ItIE(SkyItVideoIE):  # XXX: Do not subclass from concrete IE
    IE_NAME = 'tv8.it'
    _VALID_URL = r'https?://(?:www\.)?tv8\.it/(?:show)?video/(?:[0-9a-z-]+-)?(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.tv8.it/video/ogni-mattina-ucciso-asino-di-andrea-lo-cicero-630529',
        'md5': '9ab906a3f75ea342ed928442f9dabd21',
        'info_dict': {
            'id': '630529',
            'ext': 'mp4',
            'title': 'Ogni mattina - Ucciso asino di Andrea Lo Cicero',
            'timestamp': 1605721374,
            'upload_date': '20201118',
            'duration': 114,
            'thumbnail': 'https://videoplatform.sky.it/still/2020/11/18/1605717753954_ogni-mattina-ucciso-asino-di-andrea-lo-cicero_videostill_1.jpg',
        },
        'params': {'skip_download': 'm3u8'},
    }, {
        'url': 'https://www.tv8.it/video/964361',
        'md5': '1e58e807154658a16edc29e45be38107',
        'info_dict': {
            'id': '964361',
            'ext': 'mp4',
            'title': 'GialappaShow - S.4 Ep.2',
            'description': 'md5:60bb4ff5af18bbeeaedabc1de5f9e1e2',
            'duration': 8030,
            'thumbnail': 'https://videoplatform.sky.it/captures/494/2024/11/06/964361/964361_1730888412914_thumb_494.jpg',
            'timestamp': 1730821499,
            'upload_date': '20241105',
        },
    }]
    _DOMAIN = 'mtv8'


class TV8ItLiveIE(SkyItBaseIE):
    IE_NAME = 'tv8.it:live'
    IE_DESC = 'TV8 Live'
    _VALID_URL = r'https?://(?:www\.)?tv8\.it/streaming'
    _TESTS = [{
        'url': 'https://tv8.it/streaming',
        'info_dict': {
            'id': 'tv8',
            'ext': 'mp4',
            'title': str,
            'description': str,
            'is_live': True,
            'live_status': 'is_live',
        },
    }]

    def _real_extract(self, url):
        video_id = 'tv8'
        livestream = self._download_json(
            'https://apid.sky.it/vdp/v1/getLivestream', video_id,
            'Downloading manifest JSON', query={'id': '7'})
        metadata = self._download_json('https://tv8.it/api/getStreaming', video_id, fatal=False)

        return {
            **self._parse_video(livestream, video_id),
            **traverse_obj(metadata, ('info', {
                'title': ('title', 'text', {str}),
                'description': ('description', 'html', {clean_html}),
            })),
        }


class TV8ItPlaylistIE(InfoExtractor):
    IE_NAME = 'tv8.it:playlist'
    IE_DESC = 'TV8 Playlist'
    _VALID_URL = r'https?://(?:www\.)?tv8\.it/(?!video)[^/#?]+/(?P<id>[^/#?]+)'
    _TESTS = [{
        'url': 'https://tv8.it/intrattenimento/tv8-gialappas-night',
        'playlist_mincount': 32,
        'info_dict': {
            'id': 'tv8-gialappas-night',
            'title': 'Tv8 Gialappa\'s Night',
            'description': 'md5:c876039d487d9cf40229b768872718ed',
            'thumbnail': r're:https://static\.sky\.it/.+\.(png|jpe?g|webp)',
        },
    }, {
        'url': 'https://tv8.it/sport/uefa-europa-league',
        'playlist_mincount': 11,
        'info_dict': {
            'id': 'uefa-europa-league',
            'title': 'UEFA Europa League',
            'description': 'md5:9ab1832b7a8b1705b1f590e13a36bc6a',
            'thumbnail': r're:https://static\.sky\.it/.+\.(png|jpe?g|webp)',
        },
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)
        data = self._search_nextjs_data(webpage, playlist_id)['props']['pageProps']['data']
        entries = [self.url_result(
            urljoin('https://tv8.it', card['href']), ie=TV8ItIE,
            **traverse_obj(card, {
                'description': ('extraData', 'videoDesc', {str}),
                'id': ('extraData', 'asset_id', {str}),
                'thumbnail': ('image', 'src', {url_or_none}),
                'title': ('title', 'typography', 'text', {str}),
            }))
            for card in traverse_obj(data, ('lastContent', 'cards', lambda _, v: v['href']))]

        return self.playlist_result(entries, playlist_id, **traverse_obj(data, ('card', 'desktop', {
            'description': ('description', 'html', {clean_html}),
            'thumbnail': ('image', 'src', {url_or_none}),
            'title': ('title', 'text', {str}),
        })))
