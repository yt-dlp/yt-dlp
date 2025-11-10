import logging
import re
import urllib.parse
from xml.etree import ElementTree

from .common import InfoExtractor
from ..utils import (
    extract_attributes,
    get_element_by_attribute,
    get_element_by_class,
    get_element_html_by_class,
    get_element_html_by_id,
    get_element_text_and_html_by_tag,
    get_elements_html_by_class,
    unified_strdate,
)

logger = logging.getLogger(__name__)


class HEINetworkTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?heinetwork\.tv/(?:[\w\-/]+)'
    _TESTS = [{
        # requires cookies
        'url': 'https://www.heinetwork.tv/on-cinema-at-the-cinema/season-2/side-effects-and-identity-thief/',
        'md5': 'd10a28af64c3c34a69baa3f38a8c760b',
        'info_dict': {
            'id': '52',
            'title': '201 ‘Side Effects’ and ‘Identity Thief’',
            'ext': 'mp4',
            'release_date': '20130207',
            'season': 'Season 2',
            'season_number': 2,
            'season_id': 'season-2',
            'series': 'On Cinema at the Cinema',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://www.heinetwork.tv/on-cinema-at-the-cinema/season-2/',
        'playlist_mincount': 12,
        'info_dict': {
            'id': 'season-2',
            'title': 'Season 2',
        },
    }, {
        'url': 'https://www.heinetwork.tv/on-cinema-at-the-cinema/',
        'playlist_mincount': 16,
        'info_dict': {
            'id': 'on-cinema-at-the-cinema',
            'title': 'On Cinema at the Cinema',
        },
    }]

    def _real_extract(self, url):
        parts = urllib.parse.urlparse(url).path.split('/')
        # remove empty parts; get last element
        item_id = next(filter(None, reversed(parts)))

        webpage = self._download_webpage(url, item_id)
        if not self._is_logged_in(webpage):
            logger.warning('You are not logged in. Some videos may be unavailable.')
        if self._is_collection(webpage):
            return self._extract_collection(webpage, url)
        else:
            return self._extract_single_video(webpage, url)

    def _extract_collection(self, webpage, url):
        grid = get_element_html_by_class('group/collection', webpage)
        linksHtml = get_elements_html_by_class('group/thumb', grid)
        urls = [extract_attributes(html)['href'] for html in linksHtml]

        return self.playlist_from_matches(
            urls,
            ie=HEINetworkTVIE,
            playlist_id=self._path_components(url)[-1],
            playlist_title=self._breadcrumbs(webpage)[-1],
        )

    def _extract_season_name_and_number(self, webpage):
        bc = self._breadcrumbs(webpage)
        if len(bc) != 2:
            return None, None
        season_name = bc[-1]
        season_number_match = re.match(r'Season (\d+)', season_name)
        if not season_number_match:
            return season_name, None
        return season_name, int(season_number_match.group(1))

    def _extract_series_name(self, webpage):
        bc = self._breadcrumbs(webpage)
        if len(bc) < 1:
            return None
        return bc[0]

    def _path_components(self, url):
        return [p for p in urllib.parse.urlparse(url).path.split('/') if p]

    def _extract_video_id(self, webpage):
        _text, html = get_element_text_and_html_by_tag('hei-video', webpage)
        attrs = extract_attributes(html)
        return attrs['data-episode-id']

    def _extract_single_video(self, webpage, url):
        path_components = self._path_components(url)
        video_id = self._extract_video_id(webpage)
        video_src = self._extract_video_src(webpage)
        formats, _subs = self._extract_m3u8_formats_and_subtitles(video_src, video_id)
        air_date = self._air_date(webpage)
        season, season_number = self._extract_season_name_and_number(webpage)
        series = self._extract_series_name(webpage)

        return {
            'id': video_id,
            'title': self._extract_video_title(webpage),
            'formats': formats,
            'release_date': air_date,
            'season': season,
            'season_number': season_number,
            'season_id': path_components[-2],
            'series': series,
        }

    # General helpers

    def _is_logged_in(self, webpage):
        return get_element_by_attribute('href', '/my-account', webpage) is not None

    def _is_collection(self, webpage):
        return get_element_by_class('group/collection', webpage) is not None

    def _breadcrumbs(self, webpage):
        breadcrumb_container = get_element_html_by_class('breadcrumbs', webpage)
        root = ElementTree.fromstring(breadcrumb_container)
        return [''.join(e.itertext()).strip() for e in root.findall('.//li')]

    # Single-video helpers

    def _extract_video_src(self, webpage):
        _, html = get_element_text_and_html_by_tag('castable-video', webpage)
        attrs = extract_attributes(html)
        return attrs['src']

    def _extract_video_title(self, webpage):
        _, mux_video = get_element_text_and_html_by_tag('mux-video', webpage)
        attrs = extract_attributes(mux_video)
        if 'metadata-video-title' not in attrs:
            return None
        return attrs['metadata-video-title']

    def _air_date(self, webpage):
        episode_info_container = get_element_html_by_id('hei-episode-title', webpage)
        release_date_str = get_element_by_class('text-sm', episode_info_container)
        matches = re.match(r'\s+Air Date: (?P<date>[\w/]+)', release_date_str)
        return unified_strdate(matches.group('date'), day_first=False)
