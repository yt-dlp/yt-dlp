from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    url_or_none,
)
from ..utils.traversal import subs_list_to_dict, traverse_obj


class MonsterSirenHypergryphMusicIE(InfoExtractor):
    IE_NAME = 'monstersiren'
    IE_DESC = '塞壬唱片'
    _API_BASE = 'https://monster-siren.hypergryph.com/api'
    _VALID_URL = r'https?://monster-siren\.hypergryph\.com/music/(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://monster-siren.hypergryph.com/music/514562',
        'info_dict': {
            'id': '514562',
            'ext': 'wav',
            'title': 'Flame Shadow',
            'album': 'Flame Shadow',
            'artists': ['塞壬唱片-MSR'],
            'description': 'md5:19e2acfcd1b65b41b29e8079ab948053',
            'thumbnail': r're:https?://web\.hycdn\.cn/siren/pic/.+\.jpg',
        },
    }, {
        'url': 'https://monster-siren.hypergryph.com/music/514518',
        'info_dict': {
            'id': '514518',
            'ext': 'wav',
            'title': 'Heavenly Me (Instrumental)',
            'album': 'Heavenly Me',
            'artists': ['塞壬唱片-MSR', 'AIYUE blessed : 理名'],
            'description': 'md5:ce790b41c932d1ad72eb791d1d8ae598',
            'thumbnail': r're:https?://web\.hycdn\.cn/siren/pic/.+\.jpg',
        },
    }]

    def _real_extract(self, url):
        audio_id = self._match_id(url)
        song = self._download_json(f'{self._API_BASE}/song/{audio_id}', audio_id)
        if traverse_obj(song, 'code') != 0:
            msg = traverse_obj(song, ('msg', {str}, filter))
            raise ExtractorError(
                msg or 'API returned an error response', expected=bool(msg))

        album = None
        if album_id := traverse_obj(song, ('data', 'albumCid', {str})):
            album = self._download_json(
                f'{self._API_BASE}/album/{album_id}/detail', album_id, fatal=False)

        return {
            'id': audio_id,
            'vcodec': 'none',
            **traverse_obj(song, ('data', {
                'title': ('name', {str}),
                'artists': ('artists', ..., {str}),
                'subtitles': ({'url': 'lyricUrl'}, all, {subs_list_to_dict(lang='en')}),
                'url': ('sourceUrl', {url_or_none}),
            })),
            **traverse_obj(album, ('data', {
                'album': ('name', {str}),
                'description': ('intro', {clean_html}),
                'thumbnail': ('coverUrl', {url_or_none}),
            })),
        }
