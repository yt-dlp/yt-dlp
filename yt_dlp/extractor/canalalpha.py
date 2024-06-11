from .common import InfoExtractor
from ..utils import (
    clean_html,
    dict_get,
    try_get,
    unified_strdate,
)


class CanalAlphaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?canalalpha\.ch/play/[^/]+/[^/]+/(?P<id>\d+)/?.*'

    _TESTS = [{
        'url': 'https://www.canalalpha.ch/play/le-journal/episode/24520/jeudi-28-octobre-2021',
        'info_dict': {
            'id': '24520',
            'ext': 'mp4',
            'title': 'Jeudi 28 octobre 2021',
            'description': 'md5:d30c6c3e53f8ad40d405379601973b30',
            'thumbnail': 'https://static.canalalpha.ch/poster/journal/journal_20211028.jpg',
            'upload_date': '20211028',
            'duration': 1125,
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.canalalpha.ch/play/le-journal/topic/24512/la-poste-fait-de-neuchatel-un-pole-cryptographique',
        'info_dict': {
            'id': '24512',
            'ext': 'mp4',
            'title': 'La Poste fait de Neuchâtel un pôle cryptographique',
            'description': 'md5:4ba63ae78a0974d1a53d6703b6e1dedf',
            'thumbnail': 'https://static.canalalpha.ch/poster/news/news_39712.jpg',
            'upload_date': '20211028',
            'duration': 138,
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.canalalpha.ch/play/eureka/episode/24484/ces-innovations-qui-veulent-rendre-lagriculture-plus-durable',
        'info_dict': {
            'id': '24484',
            'ext': 'mp4',
            'title': 'Ces innovations qui veulent rendre l’agriculture plus durable',
            'description': 'md5:85d594a3b5dc6ccfc4a85aba6e73b129',
            'thumbnail': 'https://static.canalalpha.ch/poster/magazine/magazine_10236.jpg',
            'upload_date': '20211026',
            'duration': 360,
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.canalalpha.ch/play/avec-le-temps/episode/23516/redonner-de-leclat-grace-au-polissage',
        'info_dict': {
            'id': '23516',
            'ext': 'mp4',
            'title': 'Redonner de l\'éclat grâce au polissage',
            'description': 'md5:0d8fbcda1a5a4d6f6daa3165402177e1',
            'thumbnail': 'https://static.canalalpha.ch/poster/magazine/magazine_9990.png',
            'upload_date': '20210726',
            'duration': 360,
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://www.canalalpha.ch/play/le-journal/topic/33500/encore-des-mesures-deconomie-dans-le-jura',
        'info_dict': {
            'id': '33500',
            'ext': 'mp4',
            'title': 'Encore des mesures d\'économie dans le Jura',
            'description': 'md5:938b5b556592f2d1b9ab150268082a80',
            'thumbnail': 'https://static.canalalpha.ch/poster/news/news_46665.jpg',
            'upload_date': '20240411',
            'duration': 105,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        data_json = self._parse_json(self._search_regex(
            r'window\.__SERVER_STATE__\s?=\s?({(?:(?!};)[^"]|"([^"]|\\")*")+})\s?;',
            webpage, 'data_json'), video_id)['1']['data']['data']
        manifests = try_get(data_json, lambda x: x['video']['manifests'], expected_type=dict) or {}
        subtitles = {}
        formats = [{
            'url': video['$url'],
            'ext': 'mp4',
            'width': try_get(video, lambda x: x['res']['width'], expected_type=int),
            'height': try_get(video, lambda x: x['res']['height'], expected_type=int),
        } for video in try_get(data_json, lambda x: x['video']['mp4'], expected_type=list) or [] if video.get('$url')]
        if manifests.get('hls'):
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                manifests['hls'], video_id, m3u8_id='hls', fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)
        if manifests.get('dash'):
            fmts, subs = self._extract_mpd_formats_and_subtitles(
                manifests['dash'], video_id, mpd_id='dash', fatal=False)
            formats.extend(fmts)
            self._merge_subtitles(subs, target=subtitles)
        return {
            'id': video_id,
            'title': data_json.get('title').strip(),
            'description': clean_html(dict_get(data_json, ('longDesc', 'shortDesc'))),
            'thumbnail': data_json.get('poster'),
            'upload_date': unified_strdate(dict_get(data_json, ('webPublishAt', 'featuredAt', 'diffusionDate'))),
            'duration': try_get(data_json, lambda x: x['video']['duration'], expected_type=int),
            'formats': formats,
            'subtitles': subtitles,
        }
