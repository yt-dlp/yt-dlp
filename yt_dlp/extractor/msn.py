import os
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    traverse_obj,
    url_or_none,
)


class MSNIE(InfoExtractor):
    _WORKING = True
    _VALID_URL = r'https?://(?:(?:www|preview)\.)?msn\.com/(?:[^/]+/)+(?P<display_id>[^/]+)/[a-z]{2}-(?P<id>[\da-zA-Z]+)'
    _TESTS = [{
        # Single video with detailed metadata (fictional URL for demonstration)
        'url': 'https://www.msn.com/en-in/money/video/7-ways-to-get-rid-of-chest-congestion/vi-BBPxU6d',
        'info_dict': {
            'id': 'BBPxU6d',
            'display_id': '7-ways-to-get-rid-of-chest-congestion',
            'title': 'Seven ways to get rid of chest congestion',
            'description': '7 Ways to Get Rid of Chest Congestion',
            'uploader': 'Health',
            'ext': 'mp4',
            'duration': 88,
        },
    }, {
        'url': 'https://www.msn.com/en-gb/video/news/president-macron-interrupts-trump-over-ukraine-funding/vi-AA1zMcD7',
        'info_dict': {
            'id': 'AA1zMcD7',
            'display_id': 'president-macron-interrupts-trump-over-ukraine-funding',
            'title': 'President Macron interrupts Trump over Ukraine funding',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://www.msn.com/en-gb/video/watch/films-success-saved-adam-pearsons-acting-career/vi-AA1znZGE?ocid=hpmsn',
        'info_dict': {
            'id': 'AA1znZGE',
            'display_id': 'films-success-saved-adam-pearsons-acting-career',
            'title': "Films' success saved Adam Pearson's acting career",
            'ext': 'mp4',
        },
    }, {
        'url': 'https://www.msn.com/en-gb/video/entertainment/5-easiest-vegetables-to-grow-at-home/vi-BB1khyxn?ocid=hpmsn',
        'info_dict': {
            'id': 'BB1khyxn',
            'display_id': '5-easiest-vegetables-to-grow-at-home',
            'title': '5 Easiest Vegetables to Grow at Home',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://www.msn.com/en-us/entertainment/news/rock-frontman-replacements-you-might-not-know-happened/vi-AA1yLVcD',
        'info_dict': {
            'id': 'AA1yLVcD',
            'display_id': 'rock-frontman-replacements-you-might-not-know-happened',
            'title': 'Rock Frontman Replacements You Might Not Know Happened',
            'ext': 'mp4',
        },
    }, {
        'url': 'https://www.msn.com/en-us/video/peopleandplaces/gene-hackman-s-unseen-legacy-a-humble-artist-a-community-man-a-hollywood-icon/vi-AA1A6v68',
        'info_dict': {
            'id': 'AA1A6v68',
            'display_id': 'gene-hackman-s-unseen-legacy-a-humble-artist-a-community-man-a-hollywood-icon',
            'title': 'Gene Hackman’s unseen legacy: a humble artist, a community man, a Hollywood icon',
            'ext': 'mp4',
        },
    }, {
        # Placeholder for playlist test case (replace with actual URL)
        'url': 'https://www.msn.com/en-gb/news/world/top-5-political-moments/ar-AA1abcde',
        'info_dict': {
            'id': 'AA1abcde',
        },
        'playlist_mincount': 3,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        display_id = mobj.group('display_id')
        page_id = mobj.group('id')

        webpage = self._download_webpage(url, page_id, note='Downloading webpage')
        locale = mobj.group(0).split('/')[3]  # Extract locale (e.g., 'en-gb')
        json_url = f'https://assets.msn.com/content/view/v2/Detail/{locale}/{page_id}'
        json_data = self._download_json(json_url, page_id, note='Downloading JSON metadata', fatal=False) or {}

        if page_id.startswith('vi-'):
            # Single video extraction
            video_id = page_id[3:]  # Remove 'vi-' prefix
            video_metadata = traverse_obj(json_data, 'videoMetadata', default={})
            video_files = traverse_obj(video_metadata, 'externalVideoFiles', default=[])

            formats = []
            for v in video_files:
                if v.get('contentType') != 'video/mp4':
                    continue
                video_url = url_or_none(v.get('url'))
                if not video_url:
                    continue
                format_id = v.get('format', 'mp4')
                ext = determine_ext(video_url, default_ext='mp4')
                format_dict = {'format_id': format_id, 'url': video_url, 'ext': ext}
                filename = os.path.basename(video_url)
                if '_' in filename and filename.endswith('.mp4'):
                    bitrate_str = filename.split('_')[-1].replace('.mp4', '')
                    if bitrate := int_or_none(bitrate_str):
                        format_dict['bitrate'] = bitrate * 1000
                formats.append(format_dict)

            if not formats:
                raise ExtractorError('No video formats found', expected=True)

            title = traverse_obj(json_data, 'title') or self._html_search_meta('title', webpage)
            description = traverse_obj(json_data, 'description') or self._html_search_meta('description', webpage)
            duration = int_or_none(traverse_obj(video_metadata, 'duration'))
            uploader = traverse_obj(video_metadata, 'uploader') or self._html_search_meta('author', webpage)
            uploader_id = traverse_obj(video_metadata, 'uploaderId')

            return {
                'id': video_id,
                'display_id': display_id,
                'title': title,
                'description': description,
                'duration': duration,
                'uploader': uploader,
                'uploader_id': uploader_id,
                'formats': formats,
            }

        elif page_id.startswith('ar-'):
            # Placeholder playlist extraction logic (for future use)
            playlist_id = page_id[3:]  # Remove 'ar-' prefix
            embed_urls = self._extract_embedded_urls(json_data, webpage, playlist_id)
            if embed_urls:
                entries = [self.url_result(url) for url in embed_urls]
                return self.playlist_result(entries, playlist_id)
            else:
                self._downloader.report_warning('No embedded videos found in article')

        else:
            raise ExtractorError('Unknown URL type')

    def _extract_embedded_urls(self, json_data, webpage, video_id):
        """Extract embedded video URLs from JSON or webpage for playlists (placeholder)."""
        embed_urls = []
        # Placeholder: Check JSON for embedded video URLs (adjust key as needed)
        source_href = traverse_obj(json_data, ('videoMetadata', 'sourceHref'))
        if source_href and (embed_url := url_or_none(source_href)):
            embed_urls.append(embed_url)
        # Fallback to iframe parsing
        if not embed_urls:
            iframe_matches = re.findall(r'<iframe[^>]+src=["\'](.*?)["\']', webpage)
            for iframe_src in iframe_matches:
                if embed_url := url_or_none(iframe_src):
                    if any(host in embed_url for host in ('youtube.com', 'dailymotion.com', 'msn.com')):
                        embed_urls.append(embed_url)
        return embed_urls
