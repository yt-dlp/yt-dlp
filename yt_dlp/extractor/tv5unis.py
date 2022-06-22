from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_age_limit,
    smuggle_url,
    try_get,
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
    videoElement {
      ... on Video {
        mediaId
      }
    }
  }
}''' % (self._GQL_QUERY_NAME, self._gql_args(groups)),
            })['data'][self._GQL_QUERY_NAME]
        media_id = product['videoElement']['mediaId']

        return {
            '_type': 'url_transparent',
            'id': media_id,
            'title': product.get('title'),
            'url': smuggle_url('limelight:media:' + media_id, {'geo_countries': self._GEO_COUNTRIES}),
            'age_limit': parse_age_limit(try_get(product, lambda x: x['rating']['name'])),
            'tags': product.get('tags'),
            'series': try_get(product, lambda x: x['collection']['title']),
            'season_number': int_or_none(product.get('seasonNumber')),
            'episode_number': int_or_none(product.get('episodeNumber')),
            'ie_key': 'LimelightMedia',
        }


class TV5UnisVideoIE(TV5UnisBaseIE):
    IE_NAME = 'tv5unis:video'
    _VALID_URL = r'https?://(?:www\.)?tv5unis\.ca/videos/[^/]+/(?P<id>\d+)'
    _TEST = {
        'url': 'https://www.tv5unis.ca/videos/bande-annonces/71843',
        'md5': '3d794164928bda97fb87a17e89923d9b',
        'info_dict': {
            'id': 'a883684aecb2486cad9bdc7bbe17f861',
            'ext': 'mp4',
            'title': 'Watatatow',
            'duration': 10.01,
        }
    }
    _GQL_QUERY_NAME = 'productById'

    @staticmethod
    def _gql_args(groups):
        return 'id: %s' % groups


class TV5UnisIE(TV5UnisBaseIE):
    IE_NAME = 'tv5unis'
    _VALID_URL = r'https?://(?:www\.)?tv5unis\.ca/videos/(?P<id>[^/]+)(?:/saisons/(?P<season_number>\d+)/episodes/(?P<episode_number>\d+))?/?(?:[?#&]|$)'
    _TESTS = [{
        'url': 'https://www.tv5unis.ca/videos/watatatow/saisons/6/episodes/1',
        'md5': 'a479907d2e531a73e1f8dc48d6388d02',
        'info_dict': {
            'id': 'e5ee23a586c44612a56aad61accf16ef',
            'ext': 'mp4',
            'title': 'Je ne peux pas lui résister',
            'description': "Atys, le nouveau concierge de l'école, a réussi à ébranler la confiance de Mado en affirmant qu\'une médaille, ce n'est que du métal. Comme Mado essaie de lui prouver que ses valeurs sont solides, il veut la mettre à l'épreuve...",
            'subtitles': {
                'fr': 'count:1',
            },
            'duration': 1370,
            'age_limit': 8,
            'tags': 'count:3',
            'series': 'Watatatow',
            'season_number': 6,
            'episode_number': 1,
        },
    }, {
        'url': 'https://www.tv5unis.ca/videos/le-voyage-de-fanny',
        'md5': '9ca80ebb575c681d10cae1adff3d4774',
        'info_dict': {
            'id': '726188eefe094d8faefb13381d42bc06',
            'ext': 'mp4',
            'title': 'Le voyage de Fanny',
            'description': "Fanny, 12 ans, cachée dans un foyer loin de ses parents, s'occupe de ses deux soeurs. Devant fuir, Fanny prend la tête d'un groupe de huit enfants et s'engage dans un dangereux périple à travers la France occupée pour rejoindre la frontière suisse.",
            'subtitles': {
                'fr': 'count:1',
            },
            'duration': 5587.034,
            'tags': 'count:4',
        },
    }]
    _GQL_QUERY_NAME = 'productByRootProductSlug'

    @staticmethod
    def _gql_args(groups):
        args = 'rootProductSlug: "%s"' % groups[0]
        if groups[1]:
            args += ', seasonNumber: %s, episodeNumber: %s' % groups[1:]
        return args
