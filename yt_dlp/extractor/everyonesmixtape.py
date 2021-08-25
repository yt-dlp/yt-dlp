from __future__ import unicode_literals


from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    sanitized_Request,
)


class EveryonesMixtapeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?everyonesmixtape\.com/#/mix/(?P<id>[0-9a-zA-Z]+)(?:/(?P<songnr>[0-9]))?$'

    _TESTS = [{
        'url': 'http://everyonesmixtape.com/#/mix/m7m0jJAbMQi/5',
        'info_dict': {
            'id': '5bfseWNmlds',
            'ext': 'mp4',
            'title': "Passion Pit - \"Sleepyhead\" (Official Music Video)",
            'uploader': 'FKR.TV',
            'uploader_id': 'frenchkissrecords',
            'description': "Music video for \"Sleepyhead\" from Passion Pit's debut EP Chunk Of Change.\nBuy on iTunes: https://itunes.apple.com/us/album/chunk-of-change-ep/id300087641\n\nDirected by The Wilderness.\n\nhttp://www.passionpitmusic.com\nhttp://www.frenchkissrecords.com",
            'upload_date': '20081015'
        },
        'params': {
            'skip_download': True,  # This is simply YouTube
        }
    }, {
        'url': 'http://everyonesmixtape.com/#/mix/m7m0jJAbMQi',
        'info_dict': {
            'id': 'm7m0jJAbMQi',
            'title': 'Driving',
        },
        'playlist_count': 24
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        playlist_id = mobj.group('id')

        pllist_url = 'http://everyonesmixtape.com/mixtape.php?a=getMixes&u=-1&linked=%s&explore=' % playlist_id
        pllist_req = sanitized_Request(pllist_url)
        pllist_req.add_header('X-Requested-With', 'XMLHttpRequest')

        playlist_list = self._download_json(
            pllist_req, playlist_id, note='Downloading playlist metadata')
        try:
            playlist_no = next(playlist['id']
                               for playlist in playlist_list
                               if playlist['code'] == playlist_id)
        except StopIteration:
            raise ExtractorError('Playlist id not found')

        pl_url = 'http://everyonesmixtape.com/mixtape.php?a=getMix&id=%s&userId=null&code=' % playlist_no
        pl_req = sanitized_Request(pl_url)
        pl_req.add_header('X-Requested-With', 'XMLHttpRequest')
        playlist = self._download_json(
            pl_req, playlist_id, note='Downloading playlist info')

        entries = [{
            '_type': 'url',
            'url': t['url'],
            'title': t['title'],
        } for t in playlist['tracks']]

        if mobj.group('songnr'):
            songnr = int(mobj.group('songnr')) - 1
            return entries[songnr]

        playlist_title = playlist['mixData']['name']
        return {
            '_type': 'playlist',
            'id': playlist_id,
            'title': playlist_title,
            'entries': entries,
        }
