import functools
import math

from .common import InfoExtractor
from ..utils import (
    InAdvancePagedList,
    clean_html,
    float_or_none,
    int_or_none,
    str_or_none,
    traverse_obj,
    unified_strdate,
    url_or_none,
)


class OmnyFMShowIE(InfoExtractor):
    IE_NAME = 'omnyfm:show'
    _VALID_URL = r'https?://omny\.fm/shows/(?P<id>[^/]+)'
    _EMBED_REGEX = [r'<iframe[^>]+?src=(["\'])(?P<url>https?://omny\.fm/shows/.+?)\1']
    _PAGE_SIZE = 10
    _TESTS = [{
        'url': 'https://omny.fm/shows/league-leaders',
        'info_dict': {
            'id': 'bbe146d4-9bee-4763-b785-ad830009a23f',
            'title': 'League Leaders with Nicole Livingstone',
        },
        'playlist_mincount': 15,
    }, {
        'url': 'https://omny.fm/shows/afl-daily',
        'only_matching': True,
    }]

    def _fetch_page(self, org_id, playlist_id, page):
        return self._download_json(f'https://api.omny.fm/orgs/{org_id}/programs/{playlist_id}/clips?cursor={page}&pageSize={self._PAGE_SIZE}', f'{playlist_id}_{page}')

    def _entries(self, org_id, playlist_id, first_page_data, page):
        data = first_page_data if not page else self._fetch_page(org_id, playlist_id, page + 1)
        for clip in data.get('Clips', {}):
            yield traverse_obj(clip, {
                'id': ('Id', {str_or_none}),
                'title': ('Title', {str_or_none}),
                'description': ('Description', {clean_html}),
                'thumbnail': (('ImageUrl', 'ArtworkUrl'), {url_or_none}, any),
                'duration': ('DurationSeconds', {float_or_none}),
                'url': ('AudioUrl', {url_or_none}),
                'season_number': ('Season', {int_or_none}),
                'episode_number': ('Episode', {int_or_none}),
                'timestamp': ('PublishedUtc', {unified_strdate}, {int_or_none}),
                'filesize': ('PublishedAudioSizeInBytes', {int}),
            })

    def _real_extract(self, url):
        display_id = self._match_id(url)
        page_url = 'https://omny.fm/shows/' + display_id
        webpage = self._download_webpage(page_url, display_id)

        data = self._search_nextjs_data(webpage, display_id)
        org_id = traverse_obj(data, ('props', 'pageProps', 'program', 'OrganizationId', {str_or_none}))
        playlist_id = traverse_obj(data, ('props', 'pageProps', 'program', 'Id', {str_or_none}))
        playlist_count = traverse_obj(data, ('props', 'pageProps', 'program', 'DefaultPlaylist', 'NumberOfClips', {int_or_none}))
        title = traverse_obj(data, ('props', 'pageProps', 'program', 'Name', {str_or_none}))
        first_page_data = traverse_obj(data, ('props', 'pageProps', 'clips', {dict}))
        total_pages = math.ceil(playlist_count / self._PAGE_SIZE)

        return self.playlist_result(InAdvancePagedList(
            functools.partial(self._entries, org_id, playlist_id, first_page_data),
            total_pages, self._PAGE_SIZE), playlist_id, title)
