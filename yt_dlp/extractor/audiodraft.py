from .common import InfoExtractor
from ..utils import int_or_none


class AudiodraftBaseIE(InfoExtractor):
    def _audiodraft_extract_from_id(self, player_entry_id):
        data_json = self._download_json(
            'https://www.audiodraft.com/scripts/general/player/getPlayerInfoNew.php', player_entry_id,
            headers={
                'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
            }, data=f'id={player_entry_id}'.encode())

        return {
            'id': str(data_json['entry_id']),
            'title': data_json.get('entry_title'),
            'url': data_json['path'],
            'vcodec': 'none',
            'ext': 'mp3',
            'uploader': data_json.get('designer_name'),
            'uploader_id': data_json.get('designer_id'),
            'webpage_url': data_json.get('entry_url'),
            'like_count': int_or_none(data_json.get('entry_likes')),
            'average_rating': int_or_none(data_json.get('entry_rating')),
        }


class AudiodraftCustomIE(AudiodraftBaseIE):
    IE_NAME = 'Audiodraft:custom'
    _VALID_URL = r'https?://(?:[-\w]+)\.audiodraft\.com/entry/(?P<id>\d+)'

    _TESTS = [{
        'url': 'http://nokiatune.audiodraft.com/entry/5874',
        'info_dict': {
            'id': '9485',
            'ext': 'mp3',
            'title': 'Hula Hula Calls',
            'uploader': 'unclemaki',
            'uploader_id': '13512',
            'average_rating': 5,
            'like_count': int,
        },
    }, {
        'url': 'http://vikinggrace.audiodraft.com/entry/501',
        'info_dict': {
            'id': '22241',
            'ext': 'mp3',
            'title': 'MVG Happy',
            'uploader': 'frog',
            'uploader_id': '19142',
            'average_rating': 5,
            'like_count': int,
        },
    }, {
        'url': 'http://timferriss.audiodraft.com/entry/765',
        'info_dict': {
            'id': '19710',
            'ext': 'mp3',
            'title': 'ferris03',
            'uploader': 'malex',
            'uploader_id': '17335',
            'average_rating': 5,
            'like_count': int,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        player_entry_id = self._search_regex(
            r'playAudio\(\'(player_entry_\d+)\'\);', webpage, video_id, 'play entry id')
        return self._audiodraft_extract_from_id(player_entry_id)


class AudiodraftGenericIE(AudiodraftBaseIE):
    IE_NAME = 'Audiodraft:generic'
    _VALID_URL = r'https?://www\.audiodraft\.com/contests/[^/#]+#entries&eid=(?P<id>\d+)'

    _TESTS = [{
        'url': 'https://www.audiodraft.com/contests/570-Score-A-Video-Surprise-Us#entries&eid=30138',
        'info_dict': {
            'id': '30138',
            'ext': 'mp3',
            'title': 'DROP in sound_V2',
            'uploader': 'TiagoSilva',
            'uploader_id': '19452',
            'average_rating': 4,
            'like_count': int,
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        return self._audiodraft_extract_from_id(f'player_entry_{video_id}')
