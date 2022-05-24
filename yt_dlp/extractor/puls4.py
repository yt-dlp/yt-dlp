from .prosiebensat1 import ProSiebenSat1BaseIE
from ..utils import (
    unified_strdate,
    parse_duration,
    compat_str,
)


class Puls4IE(ProSiebenSat1BaseIE):
    _VALID_URL = r'https?://(?:www\.)?puls4\.com/(?P<id>[^?#&]+)'
    _TESTS = [{
        'url': 'http://www.puls4.com/2-minuten-2-millionen/staffel-3/videos/2min2miotalk/Tobias-Homberger-von-myclubs-im-2min2miotalk-118118',
        'md5': 'fd3c6b0903ac72c9d004f04bc6bb3e03',
        'info_dict': {
            'id': '118118',
            'ext': 'flv',
            'title': 'Tobias Homberger von myclubs im #2min2miotalk',
            'description': 'md5:f9def7c5e8745d6026d8885487d91955',
            'upload_date': '20160830',
            'uploader': 'PULS_4',
        },
    }, {
        'url': 'http://www.puls4.com/pro-und-contra/wer-wird-prasident/Ganze-Folgen/Wer-wird-Praesident.-Norbert-Hofer',
        'only_matching': True,
    }, {
        'url': 'http://www.puls4.com/pro-und-contra/wer-wird-prasident/Ganze-Folgen/Wer-wird-Praesident-Analyse-des-Interviews-mit-Norbert-Hofer-416598',
        'only_matching': True,
    }]
    _TOKEN = 'puls4'
    _SALT = '01!kaNgaiNgah1Ie4AeSha'
    _CLIENT_NAME = ''

    def _real_extract(self, url):
        path = self._match_id(url)
        content_path = self._download_json(
            'http://www.puls4.com/api/json-fe/page/' + path, path)['content'][0]['url']
        media = self._download_json(
            'http://www.puls4.com' + content_path,
            content_path)['mediaCurrent']
        player_content = media['playerContent']
        info = self._extract_video_info(url, player_content['id'])
        info.update({
            'id': compat_str(media['objectId']),
            'title': player_content['title'],
            'description': media.get('description'),
            'thumbnail': media.get('previewLink'),
            'upload_date': unified_strdate(media.get('date')),
            'duration': parse_duration(player_content.get('duration')),
            'episode': player_content.get('episodePartName'),
            'show': media.get('channel'),
            'season_id': player_content.get('seasonId'),
            'uploader': player_content.get('sourceCompany'),
        })
        return info
