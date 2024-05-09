import re

from .wistia import WistiaBaseIE
from ..utils import (
    clean_html,
    get_elements_html_by_class
)


class ThirtyDaySingerBase(WistiaBaseIE):
    _INDEX_EXTRACTION_RE = r'/tutorial/[\w-]+/(?P<index>[\w-]+)'

    def _extract_for_url(self, url):
        lesson_index = re.search(self._INDEX_EXTRACTION_RE, url).group('index')
        webpage = self._download_webpage(url, lesson_index)
        match = next(self._extract_wistia_async_embed(webpage))
        embed_config = self._download_embed_config('medias', match.group('id'), url)

        embed_infojson = self._extract_media(embed_config)
        webpage_infojson = self._extract_webpage_data(webpage)

        return {**embed_infojson, **webpage_infojson}

    def _extract_webpage_data(self, webpage):
        title = self._html_search_regex(r'<h1>([^<]+)</h1>', webpage, 'title')
        fallback_title = self._html_extract_title(webpage)
        description = self._html_search_meta('description', webpage, fatal=False)

        return {
            'title': title or fallback_title,
            'description': clean_html(self._format_html_list(description))
        }

    # The site makes extensive use of HTML lists for formatting and `clean_html`
    # doesn't handle them well. This is needed to keep lists readable.
    def _format_html_list(self, html):
        replacements = {
            '<ul>': '<br>',
            '</ul': '<br>',
            '<li>': '<br>- ',
            '</li>': ''
        }

        for k, v in replacements.items():
            html = html.replace(k, v)

        return html


class ThirtyDaySingerIE(ThirtyDaySingerBase):
    _VALID_URL = r'https?://www\.30daysinger\.com/tutorial/[\w-]+/[\w-]+'

    _TESTS = [{
        'url': 'https://www.30daysinger.com/tutorial/30-day-beginner-course-with-jonathan-estabrooks/1',
        'md5': '56bb11529b9777899b27b599d4b16cf6',
        'info_dict': {
            'id': 'tegd38l3d5',
            'ext': 'mp4',
            'thumbnail': 'http://embed.wistia.com/deliveries/c26a85cb98e32efa8a5e12a0576e63355af66230.jpg',
            'upload_date': '20190608',
            'description': 'md5:d3291de8988be57b1d3e411126ba4d33',
            'duration': 344.22,
            'timestamp': 1559952526,
            'title': 'Welcome to 30 Day Singer'
        }
    }]

    def _real_extract(self, url):
        return self._extract_for_url(url)


class ThirtyDaySingerPlaylistIE(ThirtyDaySingerBase):
    _URI_BASE = 'https://www.30daysinger.com'
    _VALID_URL = r'https?://www\.30daysinger\.com/tutorial/(?P<playlist_id>[\w-]+)/?(?:$|[#?])'

    _TESTS = [{
        'url': 'https://www.30daysinger.com/tutorial/30-day-beginner-course-with-jonathan-estabrooks',
        'info_dict': {
            'id': '30-day-beginner-course-with-jonathan-estabrooks',
            'description': 'md5:8cf6d6c7c377895653c9cde9dfc4104f',
            'title': '30 Day Beginner Course with Jonathan Estabrooks',
        },
        'playlist_count': 1,
        'expected_warnings': ['This video is for premium members only']
    }]

    def _real_extract(self, url):
        playlist_id = self._match_valid_url(url).group('playlist_id')
        webpage = self._download_webpage(url, playlist_id)
        playlist_attrs = self._extract_webpage_data(webpage)

        entries = []
        for html_element in get_elements_html_by_class('playlist-item-link', webpage):
            href = self._search_regex(r'href="([^"]+)"', html_element, 'href')

            if not href:
                continue
            # Often _some_ content is free so we should still download that but warn the user
            # when we encounter premium content.
            # NOTE: this only applies to the playlist extractor, not the single video extractor
            if 'upgrade' in href:
                self.report_warning('This video is for premium members only')
                continue

            entries.append(self._extract_for_url(self._URI_BASE + href))

        return self.playlist_result(entries, playlist_id, playlist_attrs['title'], playlist_attrs['description'])
