# coding: utf-8
from __future__ import unicode_literals


from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    int_or_none,
    str_or_none,
    try_get,
)


class PalcoMP3BaseIE(InfoExtractor):
    _GQL_QUERY_TMPL = '''{
  artist(slug: "%s") {
    %s
  }
}'''
    _ARTIST_FIELDS_TMPL = '''music(slug: "%%s") {
      %s
    }'''
    _MUSIC_FIELDS = '''duration
      hls
      mp3File
      musicID
      plays
      title'''

    def _call_api(self, artist_slug, artist_fields):
        return self._download_json(
            'https://www.palcomp3.com.br/graphql/', artist_slug, query={
                'query': self._GQL_QUERY_TMPL % (artist_slug, artist_fields),
            })['data']

    def _parse_music(self, music):
        music_id = compat_str(music['musicID'])
        title = music['title']

        formats = []
        hls_url = music.get('hls')
        if hls_url:
            formats.append({
                'url': hls_url,
                'protocol': 'm3u8_native',
                'ext': 'mp4',
            })
        mp3_file = music.get('mp3File')
        if mp3_file:
            formats.append({
                'url': mp3_file,
            })

        return {
            'id': music_id,
            'title': title,
            'formats': formats,
            'duration': int_or_none(music.get('duration')),
            'view_count': int_or_none(music.get('plays')),
        }

    def _real_initialize(self):
        self._ARTIST_FIELDS_TMPL = self._ARTIST_FIELDS_TMPL % self._MUSIC_FIELDS

    def _real_extract(self, url):
        artist_slug, music_slug = self._match_valid_url(url).groups()
        artist_fields = self._ARTIST_FIELDS_TMPL % music_slug
        music = self._call_api(artist_slug, artist_fields)['artist']['music']
        return self._parse_music(music)


class PalcoMP3IE(PalcoMP3BaseIE):
    IE_NAME = 'PalcoMP3:song'
    _VALID_URL = r'https?://(?:www\.)?palcomp3\.com(?:\.br)?/(?P<artist>[^/]+)/(?P<id>[^/?&#]+)'
    _TESTS = [{
        'url': 'https://www.palcomp3.com/maiaraemaraisaoficial/nossas-composicoes-cuida-bem-dela/',
        'md5': '99fd6405b2d8fd589670f6db1ba3b358',
        'info_dict': {
            'id': '3162927',
            'ext': 'mp3',
            'title': 'Nossas Composições - CUIDA BEM DELA',
            'duration': 210,
            'view_count': int,
        }
    }]

    @classmethod
    def suitable(cls, url):
        return False if PalcoMP3VideoIE.suitable(url) else super(PalcoMP3IE, cls).suitable(url)


class PalcoMP3ArtistIE(PalcoMP3BaseIE):
    IE_NAME = 'PalcoMP3:artist'
    _VALID_URL = r'https?://(?:www\.)?palcomp3\.com(?:\.br)?/(?P<id>[^/?&#]+)'
    _TESTS = [{
        'url': 'https://www.palcomp3.com.br/condedoforro/',
        'info_dict': {
            'id': '358396',
            'title': 'Conde do Forró',
        },
        'playlist_mincount': 188,
    }]
    _ARTIST_FIELDS_TMPL = '''artistID
    musics {
      nodes {
        %s
      }
    }
    name'''

    @classmethod
    def suitable(cls, url):
        return False if PalcoMP3IE._match_valid_url(url) else super(PalcoMP3ArtistIE, cls).suitable(url)

    def _real_extract(self, url):
        artist_slug = self._match_id(url)
        artist = self._call_api(artist_slug, self._ARTIST_FIELDS_TMPL)['artist']

        def entries():
            for music in (try_get(artist, lambda x: x['musics']['nodes'], list) or []):
                yield self._parse_music(music)

        return self.playlist_result(
            entries(), str_or_none(artist.get('artistID')), artist.get('name'))


class PalcoMP3VideoIE(PalcoMP3BaseIE):
    IE_NAME = 'PalcoMP3:video'
    _VALID_URL = r'https?://(?:www\.)?palcomp3\.com(?:\.br)?/(?P<artist>[^/]+)/(?P<id>[^/?&#]+)/?#clipe'
    _TESTS = [{
        'url': 'https://www.palcomp3.com/maiaraemaraisaoficial/maiara-e-maraisa-voce-faz-falta-aqui-ao-vivo-em-vicosa-mg/#clipe',
        'add_ie': ['Youtube'],
        'info_dict': {
            'id': '_pD1nR2qqPg',
            'ext': 'mp4',
            'title': 'Maiara e Maraisa - Você Faz Falta Aqui - DVD Ao Vivo Em Campo Grande',
            'description': 'md5:7043342c09a224598e93546e98e49282',
            'upload_date': '20161107',
            'uploader_id': 'maiaramaraisaoficial',
            'uploader': 'Maiara e Maraisa',
        }
    }]
    _MUSIC_FIELDS = 'youtubeID'

    def _parse_music(self, music):
        youtube_id = music['youtubeID']
        return self.url_result(youtube_id, 'Youtube', youtube_id)
