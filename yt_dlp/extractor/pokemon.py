# coding: utf-8
from __future__ import unicode_literals


from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    extract_attributes,
    int_or_none,
    js_to_json,
    merge_dicts,
)


class PokemonIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pokemon\.com/[a-z]{2}(?:.*?play=(?P<id>[a-z0-9]{32})|/(?:[^/]+/)+(?P<display_id>[^/?#&]+))'
    _TESTS = [{
        'url': 'https://www.pokemon.com/us/pokemon-episodes/20_30-the-ol-raise-and-switch/',
        'md5': '2fe8eaec69768b25ef898cda9c43062e',
        'info_dict': {
            'id': 'afe22e30f01c41f49d4f1d9eab5cd9a4',
            'ext': 'mp4',
            'title': 'The Ol’ Raise and Switch!',
            'description': 'md5:7db77f7107f98ba88401d3adc80ff7af',
        },
        'add_id': ['LimelightMedia'],
    }, {
        # no data-video-title
        'url': 'https://www.pokemon.com/fr/episodes-pokemon/films-pokemon/pokemon-lascension-de-darkrai-2008',
        'info_dict': {
            'id': 'dfbaf830d7e54e179837c50c0c6cc0e1',
            'ext': 'mp4',
            'title': "Pokémon : L'ascension de Darkrai",
            'description': 'md5:d1dbc9e206070c3e14a06ff557659fb5',
        },
        'add_id': ['LimelightMedia'],
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'http://www.pokemon.com/uk/pokemon-episodes/?play=2e8b5c761f1d4a9286165d7748c1ece2',
        'only_matching': True,
    }, {
        'url': 'http://www.pokemon.com/fr/episodes-pokemon/18_09-un-hiver-inattendu/',
        'only_matching': True,
    }, {
        'url': 'http://www.pokemon.com/de/pokemon-folgen/01_20-bye-bye-smettbo/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id, display_id = self._match_valid_url(url).groups()
        webpage = self._download_webpage(url, video_id or display_id)
        video_data = extract_attributes(self._search_regex(
            r'(<[^>]+data-video-id="%s"[^>]*>)' % (video_id if video_id else '[a-z0-9]{32}'),
            webpage, 'video data element'))
        video_id = video_data['data-video-id']
        title = video_data.get('data-video-title') or self._html_search_meta(
            'pkm-title', webpage, ' title', default=None) or self._search_regex(
            r'<h1[^>]+\bclass=["\']us-title[^>]+>([^<]+)', webpage, 'title')
        return {
            '_type': 'url_transparent',
            'id': video_id,
            'url': 'limelight:media:%s' % video_id,
            'title': title,
            'description': video_data.get('data-video-summary'),
            'thumbnail': video_data.get('data-video-poster'),
            'series': 'Pokémon',
            'season_number': int_or_none(video_data.get('data-video-season')),
            'episode': title,
            'episode_number': int_or_none(video_data.get('data-video-episode')),
            'ie_key': 'LimelightMedia',
        }


class PokemonWatchIE(InfoExtractor):
    _VALID_URL = r'https?://watch\.pokemon\.com/[a-z]{2}-[a-z]{2}/(?:#/)?player(?:\.html)?\?id=(?P<id>[a-z0-9]{32})'
    _API_URL = 'https://www.pokemon.com/api/pokemontv/v2/channels/{0:}'
    _TESTS = [{
        'url': 'https://watch.pokemon.com/en-us/player.html?id=8309a40969894a8e8d5bc1311e9c5667',
        'md5': '62833938a31e61ab49ada92f524c42ff',
        'info_dict': {
            'id': '8309a40969894a8e8d5bc1311e9c5667',
            'ext': 'mp4',
            'title': 'Lillier and the Staff!',
            'description': 'md5:338841b8c21b283d24bdc9b568849f04',
        }
    }, {
        'url': 'https://watch.pokemon.com/en-us/#/player?id=3fe7752ba09141f0b0f7756d1981c6b2',
        'only_matching': True
    }, {
        'url': 'https://watch.pokemon.com/de-de/player.html?id=b3c402e111a4459eb47e12160ab0ba07',
        'only_matching': True
    }]

    def _extract_media(self, channel_array, video_id):
        for channel in channel_array:
            for media in channel.get('media'):
                if media.get('id') == video_id:
                    return media
        return None

    def _real_extract(self, url):
        video_id = self._match_id(url)

        info = {
            '_type': 'url',
            'id': video_id,
            'url': 'limelight:media:%s' % video_id,
            'ie_key': 'LimelightMedia',
        }

        # API call can be avoided entirely if we are listing formats
        if self.get_param('listformats', False):
            return info

        webpage = self._download_webpage(url, video_id)
        build_vars = self._parse_json(self._search_regex(
            r'(?s)buildVars\s*=\s*({.*?})', webpage, 'build vars'),
            video_id, transform_source=js_to_json)
        region = build_vars.get('region')
        channel_array = self._download_json(self._API_URL.format(region), video_id)
        video_data = self._extract_media(channel_array, video_id)

        if video_data is None:
            raise ExtractorError(
                'Video %s does not exist' % video_id, expected=True)

        info['_type'] = 'url_transparent'
        images = video_data.get('images')

        return merge_dicts(info, {
            'title': video_data.get('title'),
            'description': video_data.get('description'),
            'thumbnail': images.get('medium') or images.get('small'),
            'series': 'Pokémon',
            'season_number': int_or_none(video_data.get('season')),
            'episode': video_data.get('title'),
            'episode_number': int_or_none(video_data.get('episode')),
        })
