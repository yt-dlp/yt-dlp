# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import (
    compat_parse_qs,
    compat_urllib_request,
)
from ..utils import (
    ExtractorError,
)


class ScreencastIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?screencast\.com/t/(?P<id>[a-zA-Z0-9]+)'
    _TESTS = [{
        'url': 'http://www.screencast.com/t/3ZEjQXlT',
        'md5': '917df1c13798a3e96211dd1561fded83',
        'info_dict': {
            'id': '3ZEjQXlT',
            'ext': 'm4v',
            'title': 'Color Measurement with Ocean Optics Spectrometers',
            'description': 'md5:240369cde69d8bed61349a199c5fb153',
            'thumbnail': r're:^https?://.*\.(?:gif|jpg)$',
        }
    }, {
        'url': 'http://www.screencast.com/t/V2uXehPJa1ZI',
        'md5': 'e8e4b375a7660a9e7e35c33973410d34',
        'info_dict': {
            'id': 'V2uXehPJa1ZI',
            'ext': 'mov',
            'title': 'The Amadeus Spectrometer',
            'description': 're:^In this video, our friends at.*To learn more about Amadeus, visit',
            'thumbnail': r're:^https?://.*\.(?:gif|jpg)$',
        }
    }, {
        'url': 'http://www.screencast.com/t/aAB3iowa',
        'md5': 'dedb2734ed00c9755761ccaee88527cd',
        'info_dict': {
            'id': 'aAB3iowa',
            'ext': 'mp4',
            'title': 'Google Earth Export',
            'description': 'Provides a demo of a CommunityViz export to Google Earth, one of the 3D viewing options.',
            'thumbnail': r're:^https?://.*\.(?:gif|jpg)$',
        }
    }, {
        'url': 'http://www.screencast.com/t/X3ddTrYh',
        'md5': '669ee55ff9c51988b4ebc0877cc8b159',
        'info_dict': {
            'id': 'X3ddTrYh',
            'ext': 'wmv',
            'title': 'Toolkit 6 User Group Webinar (2014-03-04) - Default Judgment and First Impression',
            'description': 'md5:7b9f393bc92af02326a5c5889639eab0',
            'thumbnail': r're:^https?://.*\.(?:gif|jpg)$',
        }
    }, {
        'url': 'http://screencast.com/t/aAB3iowa',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        video_url = self._html_search_regex(
            r'<embed name="Video".*?src="([^"]+)"', webpage,
            'QuickTime embed', default=None)

        if video_url is None:
            flash_vars_s = self._html_search_regex(
                r'<param name="flashVars" value="([^"]+)"', webpage, 'flash vars',
                default=None)
            if not flash_vars_s:
                flash_vars_s = self._html_search_regex(
                    r'<param name="initParams" value="([^"]+)"', webpage, 'flash vars',
                    default=None)
                if flash_vars_s:
                    flash_vars_s = flash_vars_s.replace(',', '&')
            if flash_vars_s:
                flash_vars = compat_parse_qs(flash_vars_s)
                video_url_raw = compat_urllib_request.quote(
                    flash_vars['content'][0])
                video_url = video_url_raw.replace('http%3A', 'http:')

        if video_url is None:
            video_meta = self._html_search_meta(
                'og:video', webpage, default=None)
            if video_meta:
                video_url = self._search_regex(
                    r'src=(.*?)(?:$|&)', video_meta,
                    'meta tag video URL', default=None)

        if video_url is None:
            video_url = self._html_search_regex(
                r'MediaContentUrl["\']\s*:(["\'])(?P<url>(?:(?!\1).)+)\1',
                webpage, 'video url', default=None, group='url')

        if video_url is None:
            video_url = self._html_search_meta(
                'og:video', webpage, default=None)

        if video_url is None:
            raise ExtractorError('Cannot find video')

        title = self._og_search_title(webpage, default=None)
        if title is None:
            title = self._html_search_regex(
                [r'<b>Title:</b> ([^<]+)</div>',
                 r'class="tabSeperator">></span><span class="tabText">(.+?)<',
                 r'<title>([^<]+)</title>'],
                webpage, 'title')
        thumbnail = self._og_search_thumbnail(webpage)
        description = self._og_search_description(webpage, default=None)
        if description is None:
            description = self._html_search_meta('description', webpage)

        return {
            'id': video_id,
            'url': video_url,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
        }
