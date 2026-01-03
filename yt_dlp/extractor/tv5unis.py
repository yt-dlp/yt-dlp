from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    parse_age_limit,
    traverse_obj,
    try_get,
    url_or_none,
)


class TV5UnisBaseIE(InfoExtractor):
    _GEO_COUNTRIES = ['CA']

    def _real_extract(self, url):
        groups = self._match_valid_url(url).groups()
        product = self._download_json(
            'https://api.tv5unis.ca/graphql', groups[0], query={
                'query': '''{
  %s(%s) {
    collection {
      title
    }
    episodeNumber
    rating {
      name
    }
    seasonNumber
    tags
    title
    summary
    videoElement {
      ... on Video {
        mediaId
        encodings {
          hls {
            url
          }
        }
      }
    }
  }
}''' % (self._GQL_QUERY_NAME, self._gql_args(groups)),  # noqa: UP031
            })['data'][self._GQL_QUERY_NAME]
        video = product['videoElement']
        if video is None:
            raise ExtractorError('No video element found')

        return {
            '_type': 'url_transparent',
            'id': video['mediaId'],
            'title': product.get('title'),
            'description': product.get('summary'),
            'url': traverse_obj(video, ('encodings', 'hls', 'url'), expected_type=url_or_none),
            'age_limit': parse_age_limit(try_get(product, lambda x: traverse_obj(x, ('rating', 'name'), expected_type=str))),
            'tags': product.get('tags'),
            'series': try_get(product, lambda x: traverse_obj(x, ('collection', 'title'), expected_type=str)),
            'season_number': int_or_none(product.get('seasonNumber')),
            'episode_number': int_or_none(product.get('episodeNumber')),
            'ie_key': 'Generic',
        }


class TV5UnisVideoIE(TV5UnisBaseIE):
    IE_NAME = 'tv5unis:video'
    _VALID_URL = r'https?://(?:www\.)?tv5unis\.ca/videos/[^/]+/(?P<id>\d+)'
    _TEST = {
        'url': 'https://www.tv5unis.ca/videos/bande-annonces/144041',
        'md5': '24a247c96119d77fe1bae8b440457dfa',
        'info_dict': {
            'id': '56862325352147149dce0ae139afced6',
            'ext': 'mp4',
            'title': 'Antigone',
            'description': "En aidant son frère à s'évader de prison, Antigone confronte les autorités : la police, le système judiciaire et pénal ainsi que le père de son ami Hémon. L'adolescente brillante au parcours jusque là sans tache voit l'étau se resserrer autour d'elle. Mais à la loi des hommes, elle substitue son propre sens de la justice, dicté par l'amour et la solidarité.",
            'duration': 61,
            'tags': 'count:0',
        },
    }
    _GQL_QUERY_NAME = 'productById'

    @staticmethod
    def _gql_args(groups):
        return f'id: {groups[0]}'


class TV5UnisIE(TV5UnisBaseIE):
    IE_NAME = 'tv5unis'
    _VALID_URL = r'https?://(?:www\.)?tv5unis\.ca/videos/(?P<id>[^/]+)(?:/saisons/(?P<season_number>\d+)/episodes/(?P<episode_number>\d+))?/?(?:[?#&]|$)'
    _TESTS = [{
        'url': 'https://www.tv5unis.ca/videos/watatatow/saisons/11/episodes/1',
        'md5': '43beebd47eefb1c5caf9a47a3fc35589',
        'info_dict': {
            'id': '2c06e4af20f0417b86c2536825287690',
            'ext': 'mp4',
            'title': "L'homme éléphant",
            'description': "Paul-André et Jean-Yves, le père d'Ariane, préparent la chambre de Vincent qui doit sortir de l'hôpital. Ariane se réjouit d'accueillir son cousin chez elle. Geneviève, Danny et Martin décide de souligner l'anniversaire de Ben. Stéphanie ne comprend pas l'indifférence de Michel quand elle parle du feu au Spot.",
            'subtitles': {
                'fr': 'count:1',
            },
            'duration': 1369,
            'age_limit': 8,
            'tags': 'count:4',
            'series': 'Watatatow',
            'season': 'Season 11',
            'season_number': 11,
            'episode': 'Episode 1',
            'episode_number': 1,
        },
    }, {
        'url': 'https://www.tv5unis.ca/videos/boite-a-savon',
        'md5': '7898e868e8c540f03844660e0aab6bbe',
        'info_dict': {
            'id': '4de6d0c6467b4511a0c04b92037a9f15',
            'ext': 'mp4',
            'title': 'Boîte à savon',
            'description': "Dans le petit village de Broche-à-foin, une bande de jeunes se regroupent pour disputer l'annuelle course de boîtes à savon sur la plus haute montagne de la ville. Hubert, 10 ans, tentera pour la première fois de gagner la course pour séduire Anouk Sauvages, celle qui fait battre son coeur.",
            'subtitles': {
                'fr': 'count:1',
            },
            'duration': 987,
            'tags': 'count:5',
        },
    }]
    _GQL_QUERY_NAME = 'productByRootProductSlug'

    @staticmethod
    def _gql_args(groups):
        args = f'rootProductSlug: "{groups[0]}"'
        if groups[1]:
            args += ', seasonNumber: {}, episodeNumber: {}'.format(*groups[1:])
        return args
