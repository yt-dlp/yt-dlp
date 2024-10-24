import functools

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    float_or_none,
    int_or_none,
    url_or_none,
    urlencode_postdata,
)
from ..utils.traversal import traverse_obj


class IlPostIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?ilpost\.it/episodes/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://www.ilpost.it/episodes/1-avis-akvasas-ka/',
        'md5': '43649f002d85e1c2f319bb478d479c40',
        'info_dict': {
            'id': '2972047',
            'ext': 'mp3',
            'display_id': '1-avis-akvasas-ka',
            'title': '1. Avis akvasas ka',
            'url': 'https://www.ilpost.it/wp-content/uploads/2023/12/28/1703781217-l-invasione-pt1-v6.mp3',
            'timestamp': 1703835014,
            'upload_date': '20231229',
            'duration': 2495.0,
            'availability': 'public',
            'series_id': '235598',
            'description': '',
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        endpoint_metadata = self._search_json(
            r'var\s+ilpostpodcast\s*=', webpage, 'metadata', display_id)
        episode_id = endpoint_metadata['post_id']
        podcast_id = endpoint_metadata['podcast_id']
        podcast_metadata = self._download_json(
            endpoint_metadata['ajax_url'], display_id, data=urlencode_postdata({
                'action': 'checkpodcast',
                'cookie': endpoint_metadata['cookie'],
                'post_id': episode_id,
                'podcast_id': podcast_id,
            }))

        episode = traverse_obj(podcast_metadata, (
            'data', 'postcastList', lambda _, v: str(v['id']) == episode_id, {dict}), get_all=False)
        if not episode:
            raise ExtractorError('Episode could not be extracted')

        return {
            'id': episode_id,
            'display_id': display_id,
            'series_id': podcast_id,
            'vcodec': 'none',
            **traverse_obj(episode, {
                'title': ('title', {str}),
                'description': ('description', {str}),
                'url': ('podcast_raw_url', {url_or_none}),
                'thumbnail': ('image', {url_or_none}),
                'timestamp': ('timestamp', {int_or_none}),
                'duration': ('milliseconds', {functools.partial(float_or_none, scale=1000)}),
                'availability': ('free', {lambda v: 'public' if v else 'subscriber_only'}),
            }),
        }
