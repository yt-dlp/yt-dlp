from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    int_or_none,
    smuggle_url,
    try_get,
    unified_timestamp,
)


class TeleQuebecBaseIE(InfoExtractor):
    BRIGHTCOVE_URL_TEMPLATE = 'http://players.brightcove.net/%s/%s_default/index.html?videoId=%s'

    @staticmethod
    def _brightcove_result(brightcove_id, player_id, account_id='6150020952001'):
        return {
            '_type': 'url_transparent',
            'url': smuggle_url(TeleQuebecBaseIE.BRIGHTCOVE_URL_TEMPLATE % (account_id, player_id, brightcove_id), {'geo_countries': ['CA']}),
            'ie_key': 'BrightcoveNew',
        }


class TeleQuebecIE(TeleQuebecBaseIE):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            zonevideo\.telequebec\.tv/media|
                            coucou\.telequebec\.tv/videos
                        )/(?P<id>\d+)
                    '''
    _TESTS = [{
        # available till 01.01.2023
        'url': 'http://zonevideo.telequebec.tv/media/37578/un-petit-choc-et-puis-repart/un-chef-a-la-cabane',
        'info_dict': {
            'id': '6155972771001',
            'ext': 'mp4',
            'title': 'Un petit choc et puis repart!',
            'description': 'md5:b04a7e6b3f74e32d7b294cffe8658374',
            'timestamp': 1589262469,
            'uploader_id': '6150020952001',
            'upload_date': '20200512',
        },
        'add_ie': ['BrightcoveNew'],
    }, {
        'url': 'https://zonevideo.telequebec.tv/media/55267/le-soleil/passe-partout',
        'info_dict': {
            'id': '6167180337001',
            'ext': 'mp4',
            'title': 'Le soleil',
            'description': 'md5:64289c922a8de2abbe99c354daffde02',
            'uploader_id': '6150020952001',
            'upload_date': '20200625',
            'timestamp': 1593090307,
        },
        'add_ie': ['BrightcoveNew'],
    }, {
        # no description
        'url': 'http://zonevideo.telequebec.tv/media/30261',
        'only_matching': True,
    }, {
        'url': 'https://coucou.telequebec.tv/videos/41788/idee-de-genie/l-heure-du-bain',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        media_id = self._match_id(url)
        media = self._download_json(
            'https://mnmedias.api.telequebec.tv/api/v3/media/' + media_id,
            media_id)['media']
        source_id = next(source_info['sourceId'] for source_info in media['streamInfos'] if source_info.get('source') == 'Brightcove')
        info = self._brightcove_result(source_id, '22gPKdt7f')
        product = media.get('product') or {}
        season = product.get('season') or {}
        info.update({
            'description': try_get(media, lambda x: x['descriptions'][-1]['text'], compat_str),
            'series': try_get(season, lambda x: x['serie']['titre']),
            'season': season.get('name'),
            'season_number': int_or_none(season.get('seasonNo')),
            'episode': product.get('titre'),
            'episode_number': int_or_none(product.get('episodeNo')),
        })
        return info


class TeleQuebecSquatIE(InfoExtractor):
    _VALID_URL = r'https://squat\.telequebec\.tv/videos/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://squat.telequebec.tv/videos/9314',
        'info_dict': {
            'id': 'd59ae78112d542e793d83cc9d3a5b530',
            'ext': 'mp4',
            'title': 'Poupeflekta',
            'description': 'md5:2f0718f8d2f8fece1646ee25fb7bce75',
            'duration': 1351,
            'timestamp': 1569057600,
            'upload_date': '20190921',
            'series': 'Miraculous : Les Aventures de Ladybug et Chat Noir',
            'season': 'Saison 3',
            'season_number': 3,
            'episode_number': 57,
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video = self._download_json(
            'https://squat.api.telequebec.tv/v1/videos/%s' % video_id,
            video_id)

        media_id = video['sourceId']

        return {
            '_type': 'url_transparent',
            'url': 'http://zonevideo.telequebec.tv/media/%s' % media_id,
            'ie_key': TeleQuebecIE.ie_key(),
            'id': media_id,
            'title': video.get('titre'),
            'description': video.get('description'),
            'timestamp': unified_timestamp(video.get('datePublication')),
            'series': video.get('container'),
            'season': video.get('saison'),
            'season_number': int_or_none(video.get('noSaison')),
            'episode_number': int_or_none(video.get('episode')),
        }


class TeleQuebecEmissionIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            [^/]+\.telequebec\.tv/emissions/|
                            (?:www\.)?telequebec\.tv/
                        )
                        (?P<id>[^?#&]+)
                    '''
    _TESTS = [{
        'url': 'http://lindicemcsween.telequebec.tv/emissions/100430013/des-soins-esthetiques-a-377-d-interets-annuels-ca-vous-tente',
        'info_dict': {
            'id': '6154476028001',
            'ext': 'mp4',
            'title': 'Des soins esthétiques à 377 % d’intérêts annuels, ça vous tente?',
            'description': 'md5:cb4d378e073fae6cce1f87c00f84ae9f',
            'upload_date': '20200505',
            'timestamp': 1588713424,
            'uploader_id': '6150020952001',
        },
    }, {
        'url': 'http://bancpublic.telequebec.tv/emissions/emission-49/31986/jeunes-meres-sous-pression',
        'only_matching': True,
    }, {
        'url': 'http://www.telequebec.tv/masha-et-michka/epi059masha-et-michka-3-053-078',
        'only_matching': True,
    }, {
        'url': 'http://www.telequebec.tv/documentaire/bebes-sur-mesure/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        media_id = self._search_regex(
            r'mediaId\s*:\s*(?P<id>\d+)', webpage, 'media id')

        return self.url_result(
            'http://zonevideo.telequebec.tv/media/' + media_id,
            TeleQuebecIE.ie_key())


class TeleQuebecLiveIE(TeleQuebecBaseIE):
    _VALID_URL = r'https?://zonevideo\.telequebec\.tv/(?P<id>endirect)'
    _TEST = {
        'url': 'http://zonevideo.telequebec.tv/endirect/',
        'info_dict': {
            'id': '6159095684001',
            'ext': 'mp4',
            'title': 're:^Télé-Québec [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'is_live': True,
            'description': 'Canal principal de Télé-Québec',
            'uploader_id': '6150020952001',
            'timestamp': 1590439901,
            'upload_date': '20200525',
        },
        'params': {
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        return self._brightcove_result('6159095684001', 'skCsmi2Uw')


class TeleQuebecVideoIE(TeleQuebecBaseIE):
    _VALID_URL = r'https?://video\.telequebec\.tv/player(?:-live)?/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://video.telequebec.tv/player/31110/stream',
        'info_dict': {
            'id': '6202570652001',
            'ext': 'mp4',
            'title': 'Le coût du véhicule le plus vendu au Canada / Tous les frais liés à la procréation assistée',
            'description': 'md5:685a7e4c450ba777c60adb6e71e41526',
            'upload_date': '20201019',
            'timestamp': 1603115930,
            'uploader_id': '6101674910001',
        },
    }, {
        'url': 'https://video.telequebec.tv/player-live/28527',
        'only_matching': True,
    }]

    def _call_api(self, path, video_id):
        return self._download_json(
            'http://beacon.playback.api.brightcove.com/telequebec/api/assets/' + path,
            video_id, query={'device_layout': 'web', 'device_type': 'web'})['data']

    def _real_extract(self, url):
        asset_id = self._match_id(url)
        asset = self._call_api(asset_id, asset_id)['asset']
        stream = self._call_api(
            asset_id + '/streams/' + asset['streams'][0]['id'], asset_id)['stream']
        stream_url = stream['url']
        account_id = try_get(
            stream, lambda x: x['video_provider_details']['account_id']) or '6101674910001'
        info = self._brightcove_result(stream_url, 'default', account_id)
        info.update({
            'description': asset.get('long_description') or asset.get('short_description'),
            'series': asset.get('series_original_name'),
            'season_number': int_or_none(asset.get('season_number')),
            'episode': asset.get('original_name'),
            'episode_number': int_or_none(asset.get('episode_number')),
        })
        return info
