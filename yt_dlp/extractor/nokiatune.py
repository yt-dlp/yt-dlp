from .common import InfoExtractor


class NokiaTuneIE(InfoExtractor):
    _VALID_URL = r'https?://nokiatune\.audiodraft\.com/entry/(?P<id>\d+)'

    _TESTS = [{
        'url': 'http://nokiatune.audiodraft.com/entry/5874',
        'info_dict': {
            'id': '5874',
            'title': 'Playing: Hula Hula Calls',
            'uploader': 'unclemaki',
            'ext': 'mp3'
        }
    }]

    def _real_extract(self, url):
        id = self._match_id(url)
        webpage = self._download_webpage(url, id)
        play_entry_id = self._search_regex(r'(player_entry_\d+)', webpage, id, 'play entry id')

        data_json = self._download_json('http://nokiatune.audiodraft.com/ajax_player/entryinfo', id,
                                        headers={
                                            'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                            'X-Requested-With': 'XMLHttpRequest'
                                        }, data=f'id={play_entry_id}'.encode())

        return {
            'id': id,
            'title': data_json.get('player_text'),
            'url': data_json['path'],
            'vcodec': 'none',
            'ext': 'mp3',
            'uploader': self._search_regex(r'"artist"[^>]*>([^<]+)', webpage, id, fatal=False)
        }
