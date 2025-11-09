import logging
import re
from abc import ABC, abstractmethod
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


class HEINetworkTVVideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?heinetwork\.tv/(?P<series>[\w-]+)/(?P<season>[\w-]+)/(?P<id>[\w-]+)'
    _TESTS = [{
        # requires cookies
        'url': 'https://www.heinetwork.tv/on-cinema-at-the-cinema/season-2/side-effects-and-identity-thief/',
        'md5': 'd10a28af64c3c34a69baa3f38a8c760b',
        'info_dict': {
            'id': 'side-effects-and-identity-thief',
            'title': '201 ‘Side Effects’ and ‘Identity Thief’',
            'ext': 'mp4',
            'release_date': '20130207',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _is_logged_in(self, webpage):
        return get_element_by_attribute('href', '/my-account', webpage) is not None

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

    def _real_extract(self, url):
        if not self._is_logged_in(self._download_webpage('https://www.heinetwork.tv/', None)):
            logger.warning('You are not logged in. Some videos may be unavailable.')

        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        video_src = self._extract_video_src(webpage)
        formats, _subs = self._extract_m3u8_formats_and_subtitles(video_src, video_id)
        air_date = self._air_date(webpage)

        return {
            'id': video_id,
            'title': self._extract_video_title(webpage),
            'formats': formats,
            'release_date': air_date,
        }


def _breadcrumbs(webpage):
    breadcrumb_container = get_element_html_by_class('breadcrumbs', webpage)
    root = ElementTree.fromstring(breadcrumb_container)
    return [e.text.strip() for e in root.findall('.//li')]


class HEINetworkTVCollectionIE(InfoExtractor, ABC):
    """Base class for HEINetworkTV collection extractors, which appear to have the same webpage structure"""

    @abstractmethod
    def _playlist_item_extractor(self):
        pass

    def _title(self, webpage):
        return _breadcrumbs(webpage)[-1]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        grid = get_element_html_by_class('grid', webpage)
        linksHtml = get_elements_html_by_class('group/thumb', grid)
        urls = [extract_attributes(html)['href'] for html in linksHtml]

        return self.playlist_from_matches(
            urls,
            ie=self._playlist_item_extractor(),
            playlist_id=display_id,
            playlist_title=self._title(webpage),
        )


class HEINetworkTVSeasonIE(HEINetworkTVCollectionIE):
    _VALID_URL = r'https?://(?:www\.)?heinetwork\.tv/(?P<series>[\w-]+)/(?P<id>[\w-]+)'
    _TESTS = [{
        # requires cookies
        'url': 'https://www.heinetwork.tv/on-cinema-at-the-cinema/season-2/',
        'playlist_mincount': 12,
        'info_dict': {
            'id': 'season-2',
            'title': 'Season 2',
        },
    }]

    def _playlist_item_extractor(self):
        return HEINetworkTVVideoIE


class HEINetworkTVSeriesIE(HEINetworkTVCollectionIE):
    _VALID_URL = r'https?://(?:www\.)?heinetwork\.tv/(?P<id>[\w-]+)'
    _TESTS = [{
        # requires cookies
        'url': 'https://www.heinetwork.tv/on-cinema-at-the-cinema/',
        'playlist_mincount': 16,
        'info_dict': {
            'id': 'on-cinema-at-the-cinema',
            'title': 'On Cinema at the Cinema',
        },
    }]

    def _playlist_item_extractor(self):
        return HEINetworkTVSeasonIE
