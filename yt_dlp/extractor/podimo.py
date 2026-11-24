import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    traverse_obj,
)


class PodimoIE(InfoExtractor):
    IE_NAME = 'podimo'
    _VALID_URL = r'https?://open\.podimo\.com/(?P<type>podcast|audiobook)/(?P<id>[a-f0-9\-]+)/?'

    def _get_graphql_json(self, video_id, query_name, variables, query):
        return self._download_json(
            f'https://open.podimo.com/graphql?queryName={query_name}',
            video_id, data=json.dumps({
                'operationName': query_name,
                'variables': variables,
                'query': query,
            }).encode(), headers=self._headers)

    def _get_podcast_audio_url(self, show_id, episode_id):
        return traverse_obj(self._get_graphql_json(
            episode_id, 'ShortLivedPodcastMediaUrlQuery',
            {'podcastId': show_id, 'episodeId': episode_id},
            '''query ShortLivedPodcastMediaUrlQuery($podcastId: String!, $episodeId: String!) {
                   podcastEpisodeStreamMediaById(podcastId: $podcastId, episodeId: $episodeId) {
                       url
                   }
               }'''), ('data', 'podcastEpisodeStreamMediaById', 'url'))

    def _get_audiobook_audio_url(self, book_id):
        return traverse_obj(self._get_graphql_json(
            book_id, 'ShortLivedAudiobookMediaUrlQuery',
            {'id': book_id},
            '''query ShortLivedAudiobookMediaUrlQuery($id: String!) {
                   audiobookAudioById(audiobookId: $id) {
                       url
                   }
               }'''), ('data', 'audiobookAudioById', 'url'))

    def _get_book_metadata(self, book_id):
        return traverse_obj(self._get_graphql_json(
            book_id, 'AudiobookResultsQuery',
            {'id': book_id},
            '''query AudiobookResultsQuery($id: String!) {
                   audiobookById(id: $id) {
                       id
                       title
                       authorNames
                       description
                       duration
                       coverImage { url }
                   }
               }'''), ('data', 'audiobookById'))

    def _get_podcast_episodes(self, show_id):
        episodes = []
        page = 0
        while True:
            result = traverse_obj(self._get_graphql_json(
                show_id, 'PodcastEpisodesResultsQuery',
                {
                    'podcastId': show_id,
                    'offset': page * 50,
                    'limit': 50,
                    'sorting': 'PUBLISHED_ASCENDING',
                },
                '''query PodcastEpisodesResultsQuery($podcastId: String!, $offset: Int, $limit: Int, $sorting: PodcastEpisodeSorting) {
                       podcastEpisodes(podcastId: $podcastId, offset: $offset, limit: $limit, converted: true, published: true, sorting: $sorting) {
                           id
                           podcastName
                           title
                       }
                   }'''), ('data', 'podcastEpisodes'))
            if not result:
                break
            episodes.extend(result)
            if len(result) < 50:
                break
            page += 1
        return episodes

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        content_type, content_id = mobj.group('type'), mobj.group('id')

        auth_cookie = traverse_obj(self._get_cookies('https://open.podimo.com'), ('pmo_auth', 'value'))
        self._headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/json',
            'apollographql-client-name': 'web-player',
            'apollographql-client-version': '1.0.0',
            'user-platform': 'web-player',
            'user-locale': 'en',
            'authorization': auth_cookie,
        }

        if content_type == 'podcast':
            entries = []
            podcast_name = None
            for episode in self._get_podcast_episodes(content_id):
                episode_id = episode.get('id')
                if not episode_id:
                    continue
                podcast_name = episode.get('podcastName') or podcast_name
                title = f'{podcast_name} - {episode.get("title")}'
                audio_url = self._get_podcast_audio_url(content_id, episode_id)
                if not audio_url:
                    continue
                entries.append({
                    'id': episode_id,
                    'title': title,
                    'formats': [{'url': audio_url}],
                })

            return {
                '_type': 'playlist',
                'id': content_id,
                'title': podcast_name,
                'entries': entries,
            }

        elif content_type == 'audiobook':
            metadata = self._get_book_metadata(content_id)
            return {
                'id': content_id,
                'title': metadata.get('title'),
                'description': metadata.get('description'),
                'author': ', '.join(metadata.get('authorNames') or []),
                'thumbnail': traverse_obj(metadata, ('coverImage', 'url')),
                'formats': [{
                    'url': self._get_audiobook_audio_url(content_id),
                }],
            }

        raise ExtractorError('Unsupported URL or internal error in PodimoIE')
