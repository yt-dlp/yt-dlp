from urllib.parse import parse_qs, urlparse

from .common import InfoExtractor
from .streamimdb import StreamIMDbIE
from ..utils import (
    ExtractorError,
    url_or_none,
)


class RiveStreamIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?rivestream\.xyz/watch\?(?P<query>[^#]+)'
    _TESTS = [{
        'url': 'https://www.rivestream.xyz/watch?type=movie&id=1430077',
        'only_matching': True,
    }]

    _TMDB_API_KEY = 'addfba41d0cb5aba2ebaae12ac92b671'

    def _real_extract(self, url):
        query = parse_qs(urlparse(url).query)
        media_type = (query.get('type') or ['movie'])[0]
        tmdb_id = (query.get('id') or [None])[0]
        if not tmdb_id:
            raise ExtractorError('Missing Rivestream media id', expected=True)
        if media_type != 'movie':
            raise ExtractorError('Only Rivestream movie URLs are supported for now', expected=True)

        metadata = self._download_json(
            f'https://api.themoviedb.org/3/movie/{tmdb_id}', tmdb_id,
            note='Downloading Rivestream metadata',
            query={
                'language': 'en-US',
                'api_key': self._TMDB_API_KEY,
            })
        imdb_id = metadata.get('imdb_id')
        if not imdb_id:
            raise ExtractorError('Rivestream metadata did not include an IMDb id', expected=True)

        poster = metadata.get('poster_path') or metadata.get('backdrop_path')
        return {
            '_type': 'url_transparent',
            'url': f'https://streamimdb.ru/embed/movie/{imdb_id}',
            'ie_key': StreamIMDbIE.ie_key(),
            'id': imdb_id,
            'display_id': tmdb_id,
            'title': metadata.get('title') or metadata.get('original_title'),
            'description': metadata.get('overview'),
            'thumbnail': url_or_none(f'https://image.tmdb.org/t/p/w1280{poster}') if poster else None,
        }
