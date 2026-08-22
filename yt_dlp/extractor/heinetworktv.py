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
    int_or_none,
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
            'episode': '‘Side Effects’ and ‘Identity Thief’',
            'episode_number': 1,
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
        # Remove empty parts; get last element.
        # This isn't necessarily a site-wide unique ID (we'll get that from the
        # page content), but it at least gives us something unique-ish to pass
        # to `_download_webpage`.
        item_id = next(filter(None, reversed(parts)))

        webpage = self._download_webpage(url, item_id)
        if not self._is_logged_in(webpage):
            logger.warning('You are not logged in. Some videos may be unavailable.')
        if self._is_collection(webpage):
            return self._extract_collection(webpage, url)
        else:
            return self._extract_single_video(webpage, url)

    def _extract_collection(self, webpage, url):
        if grid := get_element_html_by_class('group/collection', webpage):
            if linksHtml := get_elements_html_by_class('group/thumb', grid):
                urls = [extract_attributes(html).get('href') for html in linksHtml]

                return self.playlist_from_matches(
                    urls,
                    ie=HEINetworkTVIE,
                    playlist_id=self._path_components(url)[-1],
                    playlist_title=self._breadcrumbs(webpage)[-1],
                )

    def _extract_season_name_and_number(self, webpage):
        # expected breadcrumbs to be [series, season] for an episode page
        if (bc := self._breadcrumbs(webpage)) and len(bc) == 2:
            season_name = bc[-1]
            season_number_match = re.match(r'Season (?P<season>\d+)', season_name)
            if not season_number_match:
                return season_name, None
            return season_name, int_or_none(season_number_match.group('season'))
        return None, None

    def _extract_series_name(self, webpage):
        if (bc := self._breadcrumbs(webpage)) and len(bc) >= 1:
            return bc[0]

    def _path_components(self, url):
        return [p for p in urllib.parse.urlparse(url).path.split('/') if p]

    def _extract_video_id(self, webpage):
        _text, html = get_element_text_and_html_by_tag('hei-video', webpage)
        if html is None:
            return None
        attrs = extract_attributes(html)
        return attrs.get('data-episode-id')

    def _clean_episode_title(self, video_title):
        # ex: 1301 Episode Title
        if match := re.match(r'\d+\s+(?P<title>.+)', video_title):
            return match.group('title')

    def _episode_number(self, video_title, season_number):
        if season_number is None:
            return None
        # ex: 1301 -> season 13, episode 01
        match = re.match(fr'{re.escape(str(season_number))}(?P<episode_no>\d+)', video_title)
        if match:
            return int_or_none(match.group('episode_no'))

    def _extract_single_video(self, webpage, url):
        video_id = self._extract_video_id(webpage)
        formats, _subs = self._extract_m3u8_formats_and_subtitles(
            self._extract_video_src(webpage), video_id)
        season, season_number = self._extract_season_name_and_number(webpage)
        video_title = self._extract_video_title(webpage)

        return {
            'id': video_id,
            'title': video_title,
            'formats': formats,
            'release_date': self._air_date(webpage),
            'season': season,
            'season_number': season_number,
            'season_id': self._path_components(url)[-2],
            'series': self._extract_series_name(webpage),
            'episode': self._clean_episode_title(video_title),
            'episode_number': self._episode_number(video_title, season_number),
        }

    # General helpers

    def _is_logged_in(self, webpage):
        return get_element_by_attribute('href', '/my-account', webpage) is not None

    def _is_collection(self, webpage):
        return get_element_by_class('group/collection', webpage) is not None

    def _breadcrumbs(self, webpage):
        if breadcrumb_container := get_element_html_by_class('breadcrumbs', webpage):
            root = ElementTree.fromstring(breadcrumb_container)
            return [''.join(e.itertext()).strip() for e in root.findall('.//li')]

    # Single-video helpers

    def _extract_video_src(self, webpage):
        _, html = get_element_text_and_html_by_tag('castable-video', webpage)
        if html is None:
            return None
        attrs = extract_attributes(html)
        return attrs.get('src')

    def _extract_video_title(self, webpage):
        _, mux_video = get_element_text_and_html_by_tag('mux-video', webpage)
        if mux_video is None:
            return None
        attrs = extract_attributes(mux_video)
        return attrs.get('metadata-video-title')

    def _air_date(self, webpage):
        if episode_info_container := get_element_html_by_id('hei-episode-title', webpage):
            if release_date_str := get_element_by_class('text-sm', episode_info_container):
                if matches := re.match(r'\s+Air Date: (?P<date>[\w/]+)', release_date_str):
                    return unified_strdate(matches.group('date'), day_first=False)
