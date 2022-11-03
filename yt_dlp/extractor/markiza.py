
from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    parse_duration,
    try_get,
)


class MarkizaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?videoarchiv\.markiza\.sk/(?:video/(?:[^/]+/)*|embed/)(?P<id>\d+)(?:[_/]|$)'
    _TESTS = [{
        'url': 'http://videoarchiv.markiza.sk/video/oteckovia/84723_oteckovia-109',
        'md5': 'ada4e9fad038abeed971843aa028c7b0',
        'info_dict': {
            'id': '139078',
            'ext': 'mp4',
            'title': 'Oteckovia 109',
            'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 2760,
        },
    }, {
        'url': 'http://videoarchiv.markiza.sk/video/televizne-noviny/televizne-noviny/85430_televizne-noviny',
        'info_dict': {
            'id': '85430',
            'title': 'Televízne noviny',
        },
        'playlist_count': 23,
    }, {
        'url': 'http://videoarchiv.markiza.sk/video/oteckovia/84723',
        'only_matching': True,
    }, {
        'url': 'http://videoarchiv.markiza.sk/video/84723',
        'only_matching': True,
    }, {
        'url': 'http://videoarchiv.markiza.sk/video/filmy/85190_kamenak',
        'only_matching': True,
    }, {
        'url': 'http://videoarchiv.markiza.sk/video/reflex/zo-zakulisia/84651_pribeh-alzbetky',
        'only_matching': True,
    }, {
        'url': 'http://videoarchiv.markiza.sk/embed/85295',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        data = self._download_json(
            'http://videoarchiv.markiza.sk/json/video_jwplayer7.json',
            video_id, query={'id': video_id})

        info = self._parse_jwplayer_data(data, m3u8_id='hls', mpd_id='dash')

        if info.get('_type') == 'playlist':
            info.update({
                'id': video_id,
                'title': try_get(
                    data, lambda x: x['details']['name'], compat_str),
            })
        else:
            info['duration'] = parse_duration(
                try_get(data, lambda x: x['details']['duration'], compat_str))
        return info


class MarkizaPageIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?(?:(?:[^/]+\.)?markiza|tvnoviny)\.sk/(?:[^/]+/)*(?P<id>\d+)-'
    _TESTS = [{
        'url': 'https://tvnoviny.sk/domace/clanok/141815-byvaly-sportovec-udajne-vyrabal-mast-z-marihuany-sud-mu-vymeral-20-rocny-trest-a-vzal-aj-rodinny-dom',
        'md5': '74fdfc216f91de4d9aa4780a5c742720',
        'info_dict': {
            'id': '141815',
            'title': 'Bývalý športovec údajne vyrábal masť z marihuany. Súd mu vymeral 20-ročný trest a vzal aj rodinný dom | TVNOVINY.sk',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://tvnoviny.sk/domace/clanok/144055-robert-z-kosic-dostal-najnizsi-mozny-trest-za-to-co-spravil-je-to-aj-tak-vela-tvrdia-blizki',
        'info_dict': {
            'id': '144055',
            'title': 'Róbert z Košíc dostal najnižší možný trest. Za to, čo spravil, je to aj tak veľa, tvrdia blízki | TVNOVINY.sk',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://tvnoviny.sk/domace/clanok/338907-preco-sa-mnozia-utoky-tinedzerov-podla-psychologiciek-je-za-tym-rastuca-frustracia',
        'info_dict': {
            'id': '338907',
            'title': 'Prečo sa množia útoky tínedžerov? Podľa psychologičiek je za tým rastúca frustrácia | TVNOVINY.sk',
            'ext': 'mp4',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        iframe_url = self._html_search_regex(r'\"(https://media.cms.markiza.sk/embed/[\w]*?)(?:\?[\w\W]*?)?\"', webpage, 'iframe url')
        iframe_website = self._download_webpage(iframe_url, video_id)
        playlist_url = self._search_regex(r'\"src\":\"(https:\\\/\\\/[\w\W]*?playlist\.m3u8)', iframe_website, 'playlist url')
        stripped_playlist_url = playlist_url.replace("\\", "")
        formats = self._extract_m3u8_formats(stripped_playlist_url, video_id, 'mp4')
        return {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'formats': formats,
        }
