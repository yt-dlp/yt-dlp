import functools
import re

from .common import InfoExtractor
from .jwplatform import JWPlatformIE
from ..utils import (
    ExtractorError,
    OnDemandPagedList,
    extract_attributes,
    get_element_by_class,
    get_element_html_by_class,
)


class HollywoodReporterIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?hollywoodreporter\.com/video/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.hollywoodreporter.com/video/chris-pine-michelle-rodriguez-dungeons-dragons-cast-directors-on-what-it-took-to-make-film-sxsw-2023/',
        'info_dict': {
            'id': 'zH4jZaR5',
            'ext': 'mp4',
            'title': 'md5:a9a1c073770a32f178955997712c4bd9',
            'description': 'The cast and directors of \'Dungeons & Dragons: Honor Among Thieves\' talk about their new film.',
            'thumbnail': 'https://cdn.jwplayer.com/v2/media/zH4jZaR5/poster.jpg?width=720',
            'upload_date': '20230312',
            'timestamp': 1678586423,
            'duration': 242.0,
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        data = extract_attributes(get_element_html_by_class('vlanding-video-card__link', webpage) or '')
        video_id = data['data-video-showcase-trigger']
        showcase_type = data['data-video-showcase-type']

        if showcase_type == 'jwplayer':
            return self.url_result(f'jwplatform:{video_id}', JWPlatformIE)
        elif showcase_type == 'youtube':
            return self.url_result(video_id, 'Youtube')
        else:
            raise ExtractorError(f'Unsupported showcase type "{showcase_type}"')


class HollywoodReporterPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?hollywoodreporter\.com/vcategory/(?P<slug>[\w-]+)-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://www.hollywoodreporter.com/vcategory/heat-vision-breakdown-57822/',
        'playlist_mincount': 109,
        'info_dict': {
            'id': '57822',
            'title': 'heat-vision-breakdown',
        },
    }]

    def _fetch_page(self, slug, pl_id, page):
        page += 1
        webpage = self._download_webpage(
            f'https://www.hollywoodreporter.com/vcategory/{slug}-{pl_id}/page/{page}/',
            pl_id, note=f'Downloading playlist page {page}')
        section = get_element_by_class('video-playlist-river', webpage) or ''

        for url in re.findall(r'<a[^>]+href="([^"]+)"[^>]+class="c-title__link', section):
            yield self.url_result(url, HollywoodReporterIE)

    def _real_extract(self, url):
        slug, pl_id = self._match_valid_url(url).group('slug', 'id')
        return self.playlist_result(
            OnDemandPagedList(functools.partial(self._fetch_page, slug, pl_id), 15), pl_id, slug)
