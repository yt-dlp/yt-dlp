import json

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
    try_get,
)


class TF1IE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?tf1\.fr/[^/]+/(?P<program_slug>[^/]+)/videos/(?P<id>[^/?&#]+)\.html'
    _TESTS = [{
        'url': 'https://www.tf1.fr/tmc/quotidien-avec-yann-barthes/videos/quotidien-premiere-partie-11-juin-2019.html',
        'info_dict': {
            'id': '13641379',
            'ext': 'mp4',
            'title': 'md5:f392bc52245dc5ad43771650c96fb620',
            'description': 'md5:a02cdb217141fb2d469d6216339b052f',
            'upload_date': '20190611',
            'timestamp': 1560273989,
            'duration': 1738,
            'series': 'Quotidien avec Yann Barthès',
            'tags': ['intégrale', 'quotidien', 'Replay'],
        },
        'params': {
            # Sometimes wat serves the whole file with the --test option
            'skip_download': True,
        },
    }, {
        'url': 'http://www.tf1.fr/tf1/koh-lanta/videos/replay-koh-lanta-22-mai-2015.html',
        'only_matching': True,
    }, {
        'url': 'http://www.tf1.fr/hd1/documentaire/videos/mylene-farmer-d-une-icone.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        program_slug, slug = self._match_valid_url(url).groups()
        video = self._download_json(
            'https://www.tf1.fr/graphql/web', slug, query={
                'id': '9b80783950b85247541dd1d851f9cc7fa36574af015621f853ab111a679ce26f',
                'variables': json.dumps({
                    'programSlug': program_slug,
                    'slug': slug,
                })
            })['data']['videoBySlug']
        wat_id = video['streamId']

        tags = []
        for tag in (video.get('tags') or []):
            label = tag.get('label')
            if not label:
                continue
            tags.append(label)

        decoration = video.get('decoration') or {}

        thumbnails = []
        for source in (try_get(decoration, lambda x: x['image']['sources'], list) or []):
            source_url = source.get('url')
            if not source_url:
                continue
            thumbnails.append({
                'url': source_url,
                'width': int_or_none(source.get('width')),
            })

        return {
            '_type': 'url_transparent',
            'id': wat_id,
            'url': 'wat:' + wat_id,
            'title': video.get('title'),
            'thumbnails': thumbnails,
            'description': decoration.get('description'),
            'timestamp': parse_iso8601(video.get('date')),
            'duration': int_or_none(try_get(video, lambda x: x['publicPlayingInfos']['duration'])),
            'tags': tags,
            'series': decoration.get('programLabel'),
            'season_number': int_or_none(video.get('season')),
            'episode_number': int_or_none(video.get('episode')),
        }
