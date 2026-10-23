from .common import InfoExtractor
from ..utils import (
    clean_html,
    int_or_none,
    unified_timestamp,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class CanalAlphaIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?canalalpha\.ch/play/[^/]+/[^/]+/(?P<id>\d+)/?.*'

    _TESTS = [{
        'url': 'https://www.canalalpha.ch/play/le-journal/episode/24520/jeudi-28-octobre-2021',
        'md5': 'b11d6137566ee88666e7e4f9dac74be5',
        'info_dict': {
            'id': '24520',
            'ext': 'mp4',
            'title': 'Jeudi 28 octobre 2021',
            'description': 'md5:d30c6c3e53f8ad40d405379601973b30',
            'duration': 1125,
            'thumbnail': 'https://static.canalalpha.ch/poster/journal/journal_20211028.jpg',
            'timestamp': 1635440400,
            'upload_date': '20211028',
        },
    }, {
        'url': 'https://www.canalalpha.ch/play/le-journal/topic/24512/la-poste-fait-de-neuchatel-un-pole-cryptographique',
        'md5': '57cb9c19a4f71c3237fb3f1423b5e130',
        'info_dict': {
            'id': '24512',
            'ext': 'mp4',
            'title': 'La Poste fait de Neuchâtel un pôle cryptographique',
            'description': 'md5:4ba63ae78a0974d1a53d6703b6e1dedf',
            'duration': 138,
            'thumbnail': 'https://static.canalalpha.ch/poster/news/news_39712.jpg',
            'timestamp': 1635440400,
            'upload_date': '20211028',
        },
    }, {
        'url': 'https://www.canalalpha.ch/play/eureka/episode/24484/ces-innovations-qui-veulent-rendre-lagriculture-plus-durable',
        'md5': 'a846896c7e11aa9cead4a1eca69de65f',
        'info_dict': {
            'id': '24484',
            'ext': 'mp4',
            'title': 'Ces innovations qui veulent rendre l’agriculture plus durable',
            'description': 'md5:85d594a3b5dc6ccfc4a85aba6e73b129',
            'duration': 360,
            'thumbnail': 'https://static.canalalpha.ch/poster/magazine/magazine_10236.jpg',
            'timestamp': 1635268800,
            'upload_date': '20211026',
        },
    }, {
        'url': 'https://www.canalalpha.ch/play/avec-le-temps/episode/23516/redonner-de-leclat-grace-au-polissage',
        'md5': 'a8f18426f85ba304b4471ac0b16d7cfa',
        'info_dict': {
            'id': '23516',
            'ext': 'mp4',
            'title': 'Redonner de l\'éclat grâce au polissage',
            'description': 'md5:0d8fbcda1a5a4d6f6daa3165402177e1',
            'duration': 360,
            'thumbnail': 'https://static.canalalpha.ch/poster/magazine/magazine_9990.png',
            'timestamp': 1627320000,
            'upload_date': '20210726',
        },
    }, {
        'url': 'https://www.canalalpha.ch/play/le-journal/topic/33500/encore-des-mesures-deconomie-dans-le-jura',
        'md5': '96e8aa5e41eca71a88a1feafea8ec80f',
        'info_dict': {
            'id': '33500',
            'ext': 'mp4',
            'title': 'Encore des mesures d\'économie dans le Jura',
            'description': 'md5:938b5b556592f2d1b9ab150268082a80',
            'duration': 105,
            'thumbnail': 'https://static.canalalpha.ch/poster/news/news_46665.jpg',
            'timestamp': 1712853000,
            'upload_date': '20240411',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        media_data = self._download_json(f'https://api.canalalpha.ch/v1/media/{video_id}', video_id)['data']

        subtitles = {}
        formats = [{
            'url': video['$url'],
            'ext': 'mp4',
            **traverse_obj(video, {
                'width': ('res', 'width', {int_or_none}),
                'height': ('res', 'height', {int_or_none}),
            }),
        } for video in traverse_obj(media_data, ('video', 'mp4', lambda _, v: url_or_none(v['$url'])))]

        manifests = traverse_obj(media_data, ('video', 'manifests', {dict}), default={})
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
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(media_data, {
                'title': ('title', {str}, {lambda v: v.strip()}),
                'description': (('longDesc', 'shortDesc'), {clean_html}, any),
                'thumbnail': ('poster', {url_or_none}),
                'timestamp': (('webPublishAt', 'featuredAt', 'diffusionDate'), {unified_timestamp}, any),
                'duration': ('video', 'duration', {int_or_none}),
            }),
        }
