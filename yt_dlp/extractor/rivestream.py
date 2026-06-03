from html import unescape
from urllib.parse import parse_qs, urlparse

from .common import InfoExtractor
from .streamimdb import StreamIMDbIE
from ..utils import (
    ExtractorError,
    int_or_none,
    url_or_none,
)


class RiveStreamIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rivestream\.xyz/watch\?(?P<query>[^#]+)'
    _TESTS = [{
        'url': 'https://www.rivestream.xyz/watch?type=movie&id=1430077',
        'only_matching': True,
    }, {
        'url': 'https://www.rivestream.xyz/watch?type=tv&id=1399&season=1&episode=1',
        'only_matching': True,
    }]

    _TMDB_API_KEY = 'addfba41d0cb5aba2ebaae12ac92b671'

    def _real_extract(self, url):
        url = unescape(url)
        query = parse_qs(urlparse(url).query)
        media_type = (query.get('type') or ['movie'])[0].lower()
        if media_type in ('tv', 'series', 'show', 'anime', 'cartoon'):
            media_type = 'tv'
        tmdb_id = (query.get('id') or [None])[0]
        if not tmdb_id:
            raise ExtractorError('Missing Rivestream media id', expected=True)
        if media_type not in ('movie', 'tv'):
            raise ExtractorError(f'Unsupported Rivestream media type: {media_type}', expected=True)

        metadata = self._download_json(
            'https://www.rivestream.xyz/api/backendfetch', tmdb_id,
            note='Downloading Rivestream metadata',
            query={
                'id': tmdb_id,
                'requestID': 'movieData' if media_type == 'movie' else 'tvData',
                'language': 'en-US',
            })
        imdb_id = metadata.get('imdb_id')
        if not imdb_id and media_type == 'tv':
            external_ids = self._download_json(
                f'https://api.themoviedb.org/3/tv/{tmdb_id}/external_ids', tmdb_id,
                note='Downloading Rivestream external ids',
                query={'api_key': self._TMDB_API_KEY})
            imdb_id = external_ids.get('imdb_id')
        if not imdb_id:
            raise ExtractorError('Rivestream metadata did not include an IMDb id', expected=True)

        poster = metadata.get('poster_path') or metadata.get('backdrop_path')
        season = (query.get('season') or [None])[0] or '1'
        episode = (query.get('episode') or [None])[0] or '1'
        streamimdb_type = 'movie' if media_type == 'movie' else 'tv'
        streamimdb_url = f'https://streamimdb.ru/embed/{streamimdb_type}/{imdb_id}'
        if streamimdb_type == 'tv':
            streamimdb_url = f'{streamimdb_url}?season={season}&episode={episode}'
        return {
            '_type': 'url_transparent',
            'url': streamimdb_url,
            'ie_key': StreamIMDbIE.ie_key(),
            'id': imdb_id,
            'display_id': tmdb_id,
            'title': metadata.get('title') or metadata.get('name') or metadata.get('original_title') or metadata.get('original_name'),
            'description': metadata.get('overview'),
            'thumbnail': url_or_none(f'https://image.tmdb.org/t/p/w1280{poster}') if poster else None,
            **({'season_number': int_or_none(season), 'episode_number': int_or_none(episode)} if streamimdb_type == 'tv' else {}),
        }
