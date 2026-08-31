from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    join_nonempty,
    make_archive_id,
    parse_age_limit,
    remove_end,
)
from ..utils.traversal import traverse_obj


class TV5UnisBaseIE(InfoExtractor):
    _GEO_COUNTRIES = ['CA']
    _GEO_BYPASS = False

    def _real_extract(self, url):
        groups = self._match_valid_url(url).groups()
        product = self._download_json(
            'https://api.tv5unis.ca/graphql', groups[0], query={
                'query': '''{
  %s(%s) {
    title
    summary
    tags
    duration
    seasonNumber
    episodeNumber
    collection {
      title
    }
    rating {
      name
    }
    videoElement {
      __typename
      ... on Video {
        mediaId
        encodings {
          hls {
            url
          }
        }
      }
      ... on RestrictedVideo {
        code
        reason
      }
    }
  }
}''' % (self._GQL_QUERY_NAME, self._gql_args(groups)),  # noqa: UP031
            })['data'][self._GQL_QUERY_NAME]

        video = product['videoElement']
        if video is None:
            raise ExtractorError('This content is no longer available', expected=True)

        if video.get('__typename') == 'RestrictedVideo':
            code = video.get('code')
            if code == 1001:
                self.raise_geo_restricted(countries=self._GEO_COUNTRIES)
            reason = video.get('reason')
            raise ExtractorError(join_nonempty(
                'This video is restricted',
                code is not None and f', error code {code}',
                reason and f': {remove_end(reason, ".")}',
                delim=''))

        media_id = video['mediaId']
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(
            video['encodings']['hls']['url'], media_id, 'mp4')

        return {
            'id': media_id,
            '_old_archive_ids': [make_archive_id('LimelightMedia', media_id)],
            'formats': formats,
            'subtitles': subtitles,
            **traverse_obj(product, {
                'title': ('title', {str}),
                'description': ('summary', {str}),
                'tags': ('tags', ..., {str}),
                'duration': ('duration', {int_or_none}),
                'season_number': ('seasonNumber', {int_or_none}),
                'episode_number': ('episodeNumber', {int_or_none}),
                'series': ('collection', 'title', {str}),
                'age_limit': ('rating', 'name', {parse_age_limit}),
            }),
        }


class TV5UnisVideoIE(TV5UnisBaseIE):
    IE_NAME = 'tv5unis:video'
    _VALID_URL = r'https?://(?:www\.)?tv5(?:unis|plus)\.ca/videos/[^/?#]+/(?P<id>\d+)'
    _TESTS = [{
        # Old URL schema
        'url': 'https://www.tv5unis.ca/videos/bande-annonces/144041',
        'md5': '24a247c96119d77fe1bae8b440457dfa',
        'info_dict': {
            'id': '56862325352147149dce0ae139afced6',
            '_old_archive_ids': ['limelightmedia 56862325352147149dce0ae139afced6'],
            'ext': 'mp4',
            'title': 'Antigone',
            'description': r"re:En aidant son frère .+ dicté par l'amour et la solidarité.",
            'duration': 61,
        },
    }, {
        # New URL schema
        'url': 'https://www.tv5plus.ca/videos/bande-annonces/144041',
        'md5': '24a247c96119d77fe1bae8b440457dfa',
        'info_dict': {
            'id': '56862325352147149dce0ae139afced6',
            '_old_archive_ids': ['limelightmedia 56862325352147149dce0ae139afced6'],
            'ext': 'mp4',
            'title': 'Antigone',
            'description': r"re:En aidant son frère .+ dicté par l'amour et la solidarité.",
            'duration': 61,
        },
    }, {
        # Old URL schema
        'url': 'https://www.tv5unis.ca/videos/bande-annonces/151334',
        'md5': '9f936acc942469a663670ec35b42e4d3',
        'info_dict': {
            'id': '320ed8e5a5b542608a97537b80b4c72c',
            '_old_archive_ids': ['limelightmedia 320ed8e5a5b542608a97537b80b4c72c'],
            'ext': 'mp4',
            'title': 'U-Hauling : Algorithmes amoureux',
            'subtitles': {
                'fr': 'count:1',
            },
            'description': r"re:Deux ans après qu'Iris ait brisé son coeur, .+ Ash apprend l'amour à l'ère des applications.",
            'duration': 30,
            'season': 'Season 2',
            'season_number': 2,
        },
    }, {
        # New URL schema
        'url': 'https://www.tv5plus.ca/videos/bande-annonces/151334',
        'md5': '9f936acc942469a663670ec35b42e4d3',
        'info_dict': {
            'id': '320ed8e5a5b542608a97537b80b4c72c',
            '_old_archive_ids': ['limelightmedia 320ed8e5a5b542608a97537b80b4c72c'],
            'ext': 'mp4',
            'title': 'U-Hauling : Algorithmes amoureux',
            'description': r"re:Deux ans après qu'Iris ait brisé son coeur, .+ Ash apprend l'amour à l'ère des applications.",
            'subtitles': {
                'fr': 'count:1',
            },
            'duration': 30,
            'season': 'Season 2',
            'season_number': 2,
        },
    }]
    _GQL_QUERY_NAME = 'productById'

    @staticmethod
    def _gql_args(groups):
        return f'id: {groups[0]}'


class TV5UnisIE(TV5UnisBaseIE):
    IE_NAME = 'tv5unis'
    _VALID_URL = r'https?://(?:www\.)?tv5(?:unis|plus)\.ca/videos/(?P<id>[^/?#]+)(?:/saisons/(?P<season_number>\d+)/episodes/(?P<episode_number>\d+))?/?(?:[?#&]|$)'
    _TESTS = [{
        # geo-restricted to Canada; xff is ineffective
        # Old URL schema
        'url': 'https://www.tv5unis.ca/videos/watatatow/saisons/11/episodes/1',
        'md5': '43beebd47eefb1c5caf9a47a3fc35589',
        'info_dict': {
            'id': '2c06e4af20f0417b86c2536825287690',
            '_old_archive_ids': ['limelightmedia 2c06e4af20f0417b86c2536825287690'],
            'ext': 'mp4',
            'title': "L'homme éléphant",
            'description': r're:Paul-André et Jean-Yves, .+ quand elle parle du feu au Spot.',
            'subtitles': {
                'fr': 'count:1',
            },
            'duration': 1440,
            'age_limit': 8,
            'tags': 'count:4',
            'series': 'Watatatow',
            'season': 'Season 11',
            'season_number': 11,
            'episode': 'Episode 1',
            'episode_number': 1,
        },
    }, {
        # geo-restricted to Canada; xff is ineffective
        # Old URL schema
        'url': 'https://www.tv5unis.ca/videos/boite-a-savon',
        'md5': '7898e868e8c540f03844660e0aab6bbe',
        'info_dict': {
            'id': '4de6d0c6467b4511a0c04b92037a9f15',
            '_old_archive_ids': ['limelightmedia 4de6d0c6467b4511a0c04b92037a9f15'],
            'ext': 'mp4',
            'title': 'Boîte à savon',
            'description': r're:Dans le petit village de Broche-à-foin, .+ celle qui fait battre son coeur.',
            'subtitles': {
                'fr': 'count:1',
            },
            'duration': 1200,
            'tags': 'count:5',
        },
    }, {
        # geo-restricted to Canada; xff is ineffective
        # New URL schema
        'url': 'https://www.tv5plus.ca/videos/watatatow/saisons/11/episodes/1',
        'md5': '43beebd47eefb1c5caf9a47a3fc35589',
        'info_dict': {
            'id': '2c06e4af20f0417b86c2536825287690',
            '_old_archive_ids': ['limelightmedia 2c06e4af20f0417b86c2536825287690'],
            'ext': 'mp4',
            'title': "L'homme éléphant",
            'description': r're:Paul-André et Jean-Yves, .+ quand elle parle du feu au Spot.',
            'subtitles': {
                'fr': 'count:1',
            },
            'duration': 1440,
            'age_limit': 8,
            'tags': 'count:4',
            'series': 'Watatatow',
            'season': 'Season 11',
            'season_number': 11,
            'episode': 'Episode 1',
            'episode_number': 1,
        },
    }, {
        # geo-restricted to Canada; xff is ineffective
        # New URL schema
        'url': 'https://www.tv5plus.ca/videos/boite-a-savon',
        'md5': '7898e868e8c540f03844660e0aab6bbe',
        'info_dict': {
            'id': '4de6d0c6467b4511a0c04b92037a9f15',
            '_old_archive_ids': ['limelightmedia 4de6d0c6467b4511a0c04b92037a9f15'],
            'ext': 'mp4',
            'title': 'Boîte à savon',
            'description': r're:Dans le petit village de Broche-à-foin, .+ celle qui fait battre son coeur.',
            'subtitles': {
                'fr': 'count:1',
            },
            'duration': 1200,
            'tags': 'count:5',
        },
    }, {
        # geo-restricted to Canada; xff is ineffective
        # Old URL schema
        'url': 'https://www.tv5unis.ca/videos/fem/saisons/2/episodes/1',
        'md5': '448c013860af06bdaa8529d3d5adfcb7',
        'info_dict': {
            'id': '3640952a1f734451bb62785dd21fca67',
            '_old_archive_ids': ['limelightmedia 3640952a1f734451bb62785dd21fca67'],
            'ext': 'mp4',
            'title': 'Épisode 1',
            'description': r're:À Lanak, Zav et Uriel travaillent toujours .+ mais elle est confrontée aux démons de son passé.',
            'subtitles': {
                'fr': 'count:1',
            },
            'duration': 1440,
            'age_limit': 8,
            'tags': 'count:5',
            'series': 'FEM',
            'season': 'Season 2',
            'season_number': 2,
            'episode': 'Episode 1',
            'episode_number': 1,
        },
    }, {
        # geo-restricted to Canada; xff is ineffective
        # New URL schema
        'url': 'https://www.tv5plus.ca/videos/fem/saisons/2/episodes/1',
        'md5': '448c013860af06bdaa8529d3d5adfcb7',
        'info_dict': {
            'id': '3640952a1f734451bb62785dd21fca67',
            '_old_archive_ids': ['limelightmedia 3640952a1f734451bb62785dd21fca67'],
            'ext': 'mp4',
            'title': 'Épisode 1',
            'description': r're:À Lanak, Zav et Uriel travaillent toujours .+ mais elle est confrontée aux démons de son passé.',
            'subtitles': {
                'fr': 'count:1',
            },
            'duration': 1440,
            'age_limit': 8,
            'tags': 'count:5',
            'series': 'FEM',
            'season': 'Season 2',
            'season_number': 2,
            'episode': 'Episode 1',
            'episode_number': 1,
        },
    }, {
        # NOT geo-restricted to Canada
        # Old URL schema
        'url': 'https://www.tv5unis.ca/videos/en-therapie-avec-mon-chat/saisons/3/episodes/1',
        'md5': 'af6718402850fe066021b21668730c8d',
        'info_dict': {
            'id': 'dcd82c76fbc64216b2e075394bf0f87d',
            '_old_archive_ids': ['limelightmedia dcd82c76fbc64216b2e075394bf0f87d'],
            'ext': 'mp4',
            'title': 'Chuck et des nouvelles d\'Inouk',
            'description': r're:Entre pleurs de bébé et bruits d\'aspirateur, .+ Ils songent à adopter un nouveau compagnon.',
            'subtitles': {
                'fr': 'count:1',
            },
            'duration': 1440,
            'tags': 'count:4',
            'series': 'En thérapie avec mon chat',
            'season': 'Season 3',
            'season_number': 3,
            'episode': 'Episode 1',
            'episode_number': 1,
        },
    }, {
        # NOT geo-restricted to Canada
        # New URL schema
        'url': 'https://www.tv5plus.ca/videos/en-therapie-avec-mon-chat/saisons/3/episodes/1',
        'md5': 'af6718402850fe066021b21668730c8d',
        'info_dict': {
            'id': 'dcd82c76fbc64216b2e075394bf0f87d',
            '_old_archive_ids': ['limelightmedia dcd82c76fbc64216b2e075394bf0f87d'],
            'ext': 'mp4',
            'title': 'Chuck et des nouvelles d\'Inouk',
            'description': r're:Entre pleurs de bébé et bruits d\'aspirateur, .+ Ils songent à adopter un nouveau compagnon.',
            'subtitles': {
                'fr': 'count:1',
            },
            'duration': 1440,
            'tags': 'count:4',
            'series': 'En thérapie avec mon chat',
            'season': 'Season 3',
            'season_number': 3,
            'episode': 'Episode 1',
            'episode_number': 1,
        },
    }]
    _GQL_QUERY_NAME = 'productByRootProductSlug'

    @staticmethod
    def _gql_args(groups):
        args = f'rootProductSlug: "{groups[0]}"'
        if groups[1]:
            args += ', seasonNumber: {}, episodeNumber: {}'.format(*groups[1:])
        return args
