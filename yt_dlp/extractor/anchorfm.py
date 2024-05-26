from .common import InfoExtractor
from ..utils import (
    clean_html,
    float_or_none,
    int_or_none,
    str_or_none,
    traverse_obj,
    unified_timestamp,
)


class AnchorFMEpisodeIE(InfoExtractor):
    _VALID_URL = r'https?://anchor\.fm/(?P<channel_name>\w+)/(?:embed/)?episodes/[\w-]+-(?P<episode_id>\w+)'
    _EMBED_REGEX = [rf'<iframe[^>]+\bsrc=[\'"](?P<url>{_VALID_URL})']
    _TESTS = [{
        'url': 'https://anchor.fm/lovelyti/episodes/Chrisean-Rock-takes-to-twitter-to-announce-shes-pregnant--Blueface-denies-he-is-the-father-e1tpt3d',
        'info_dict': {
            'id': 'e1tpt3d',
            'ext': 'mp3',
            'title': ' Chrisean Rock takes to twitter to announce she\'s pregnant, Blueface denies he is the father!',
            'description': 'md5:207d167de3e28ceb4ddc1ebf5a30044c',
            'thumbnail': 'https://s3-us-west-2.amazonaws.com/anchor-generated-image-bank/production/podcast_uploaded_nologo/1034827/1034827-1658438968460-5f3bfdf3601e8.jpg',
            'duration': 624.718,
            'uploader': 'Lovelyti ',
            'uploader_id': '991541',
            'channel': 'lovelyti',
            'modified_date': '20230121',
            'modified_timestamp': 1674285178,
            'release_date': '20230121',
            'release_timestamp': 1674285179,
            'episode_id': 'e1tpt3d',
        }
    }, {
        # embed url
        'url': 'https://anchor.fm/apakatatempo/embed/episodes/S2E75-Perang-Bintang-di-Balik-Kasus-Ferdy-Sambo-dan-Ismail-Bolong-e1shjqd',
        'info_dict': {
            'id': 'e1shjqd',
            'ext': 'mp3',
            'title': 'S2E75 Perang Bintang di Balik Kasus Ferdy Sambo dan Ismail Bolong',
            'description': 'md5:9e95ad9293bf00178bf8d33e9cb92c41',
            'duration': 1042.008,
            'thumbnail': 'https://s3-us-west-2.amazonaws.com/anchor-generated-image-bank/production/podcast_uploaded_episode400/2627805/2627805-1671590688729-4db3882ac9e4b.jpg',
            'release_date': '20221221',
            'release_timestamp': 1671595916,
            'modified_date': '20221221',
            'modified_timestamp': 1671590834,
            'channel': 'apakatatempo',
            'uploader': 'Podcast Tempo',
            'uploader_id': '2585461',
            'season': 'Season 2',
            'season_number': 2,
            'episode_id': 'e1shjqd',
        }
    }]

    _WEBPAGE_TESTS = [{
        'url': 'https://podcast.tempo.co/podcast/192/perang-bintang-di-balik-kasus-ferdy-sambo-dan-ismail-bolong',
        'info_dict': {
            'id': 'e1shjqd',
            'ext': 'mp3',
            'release_date': '20221221',
            'duration': 1042.008,
            'season': 'Season 2',
            'modified_timestamp': 1671590834,
            'uploader_id': '2585461',
            'modified_date': '20221221',
            'description': 'md5:9e95ad9293bf00178bf8d33e9cb92c41',
            'season_number': 2,
            'title': 'S2E75 Perang Bintang di Balik Kasus Ferdy Sambo dan Ismail Bolong',
            'release_timestamp': 1671595916,
            'episode_id': 'e1shjqd',
            'thumbnail': 'https://s3-us-west-2.amazonaws.com/anchor-generated-image-bank/production/podcast_uploaded_episode400/2627805/2627805-1671590688729-4db3882ac9e4b.jpg',
            'uploader': 'Podcast Tempo',
            'channel': 'apakatatempo',
        }
    }]

    def _real_extract(self, url):
        channel_name, episode_id = self._match_valid_url(url).group('channel_name', 'episode_id')
        api_data = self._download_json(f'https://anchor.fm/api/v3/episodes/{episode_id}', episode_id)

        return {
            'id': episode_id,
            'title': traverse_obj(api_data, ('episode', 'title')),
            'url': traverse_obj(api_data, ('episode', 'episodeEnclosureUrl'), ('episodeAudios', 0, 'url')),
            'ext': 'mp3',
            'vcodec': 'none',
            'thumbnail': traverse_obj(api_data, ('episode', 'episodeImage')),
            'description': clean_html(traverse_obj(api_data, ('episode', ('description', 'descriptionPreview')), get_all=False)),
            'duration': float_or_none(traverse_obj(api_data, ('episode', 'duration')), 1000),
            'modified_timestamp': unified_timestamp(traverse_obj(api_data, ('episode', 'modified'))),
            'release_timestamp': int_or_none(traverse_obj(api_data, ('episode', 'publishOnUnixTimestamp'))),
            'episode_id': episode_id,
            'uploader': traverse_obj(api_data, ('creator', 'name')),
            'uploader_id': str_or_none(traverse_obj(api_data, ('creator', 'userId'))),
            'season_number': int_or_none(traverse_obj(api_data, ('episode', 'podcastSeasonNumber'))),
            'channel': channel_name or traverse_obj(api_data, ('creator', 'vanitySlug')),
        }
