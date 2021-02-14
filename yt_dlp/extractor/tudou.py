# coding: utf-8

from __future__ import unicode_literals

from .common import InfoExtractor


class TudouPlaylistIE(InfoExtractor):
    IE_NAME = 'tudou:playlist'
    _VALID_URL = r'https?://(?:www\.)?tudou\.com/listplay/(?P<id>[\w-]{11})\.html'
    _TESTS = [{
        'url': 'http://www.tudou.com/listplay/zzdE77v6Mmo.html',
        'info_dict': {
            'id': 'zzdE77v6Mmo',
        },
        'playlist_mincount': 209,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        playlist_data = self._download_json(
            'http://www.tudou.com/tvp/plist.action?lcode=%s' % playlist_id, playlist_id)
        entries = [self.url_result(
            'http://www.tudou.com/programs/view/%s' % item['icode'],
            'Tudou', item['icode'],
            item['kw']) for item in playlist_data['items']]
        return self.playlist_result(entries, playlist_id)


class TudouAlbumIE(InfoExtractor):
    IE_NAME = 'tudou:album'
    _VALID_URL = r'https?://(?:www\.)?tudou\.com/album(?:cover|play)/(?P<id>[\w-]{11})'
    _TESTS = [{
        'url': 'http://www.tudou.com/albumplay/v5qckFJvNJg.html',
        'info_dict': {
            'id': 'v5qckFJvNJg',
        },
        'playlist_mincount': 45,
    }]

    def _real_extract(self, url):
        album_id = self._match_id(url)
        album_data = self._download_json(
            'http://www.tudou.com/tvp/alist.action?acode=%s' % album_id, album_id)
        entries = [self.url_result(
            'http://www.tudou.com/programs/view/%s' % item['icode'],
            'Tudou', item['icode'],
            item['kw']) for item in album_data['items']]
        return self.playlist_result(entries, album_id)
