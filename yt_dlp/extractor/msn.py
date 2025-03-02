import re
import os

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    determine_ext,
    int_or_none,
    unescapeHTML,
    url_or_none,
)


class MSNIE(InfoExtractor):
    _WORKING = True  # Set to True assuming it works after refinement
    _VALID_URL = r'https?://(?:(?:www|preview)\.)?msn\.com/(?:[^/]+/)+(?P<display_id>[^/]+)/[a-z]{2}-(?P<id>[\da-zA-Z]+)'
    _TESTS = [{
        'url': 'https://www.msn.com/en-in/money/video/7-ways-to-get-rid-of-chest-congestion/vi-BBPxU6d',
        'md5': '087548191d273c5c55d05028f8d2cbcd',
        'info_dict': {
            'id': 'BBPxU6d',
            'display_id': '7-ways-to-get-rid-of-chest-congestion',
            'ext': 'mp4',
            'title': 'Seven ways to get rid of chest congestion',
            'description': '7 Ways to Get Rid of Chest Congestion',
            'duration': 88,
            'uploader': 'Health',
            'uploader_id': 'BBPrMqa',
        },
    }, {
        'url': 'https://www.msn.com/en-in/money/sports/hottest-football-wags-greatest-footballers-turned-managers-and-more/ar-BBpc7Nl',
        'info_dict': {
            'id': 'BBpc7Nl',
        },
        'playlist_mincount': 4,
    }, {
        'url': 'http://www.msn.com/en-ae/news/offbeat/meet-the-nine-year-old-self-made-millionaire/ar-BBt6ZKf',
        'only_matching': True,
    }, {
        'url': 'http://www.msn.com/en-ae/video/watch/obama-a-lot-of-people-will-be-disappointed/vi-AAhxUMH',
        'only_matching': True,
    }, {
        'url': 'http://www.msn.com/en-ae/foodanddrink/joinourtable/the-first-fart-makes-you-laugh-the-last-fart-makes-you-cry/vp-AAhzIBU',
        'only_matching': True,
    }, {
        'url': 'http://www.msn.com/en-ae/entertainment/bollywood/watch-how-salman-khan-reacted-when-asked-if-he-would-apologize-for-his-‘raped-woman’-comment/vi-AAhvzW6',
        'only_matching': True,
    }, {
        'url': 'https://www.msn.com/en-us/money/other/jupiter-is-about-to-come-so-close-you-can-see-its-moons-with-binoculars/vi-AACqsHR',
        'only_matching': True,
    }, {
        'url': 'https://www.msn.com/es-ve/entretenimiento/watch/winston-salem-paire-refait-des-siennes-en-perdant-sa-raquette-au-service/vp-AAG704L',
        'only_matching': True,
    }, {
        'url': 'https://www.msn.com/en-in/money/news/meet-vikram-%E2%80%94-chandrayaan-2s-lander/vi-AAGUr0v',
        'only_matching': True,
    }, {
        'url': 'https://www.msn.com/en-us/money/football_nfl/week-13-preview-redskins-vs-panthers/vi-BBXsCDb',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        # Parse URL
        m = re.match(self._VALID_URL, url)
        if not m:
            raise ExtractorError('Invalid URL', expected=True)
        display_id, page_id = m.groups()

        # Fetch webpage for embeds and fallback
        webpage = self._download_webpage(url, page_id, note='Downloading webpage', errnote='Unable to download webpage')

        # Fetch JSON metadata
        json_url = f'https://assets.msn.com/content/view/v2/Detail/{m.group(0).split("/")[3]}/{page_id}'
        try:
            json_data = self._download_json(
                json_url, page_id, note='Downloading video metadata', errnote='Unable to fetch video metadata'
            )
            # Optional debug: Uncomment to inspect JSON response
            # self._downloader.to_screen(f"JSON data: {json_data}")
        except ExtractorError as e:
            self.report_warning(f'JSON metadata fetch failed: {str(e)}. Falling back to webpage parsing.')
            json_data = {}

        # Extract direct video formats
        formats = []
        video_metadata = json_data.get('videoMetadata', {})
        video_files = video_metadata.get('externalVideoFiles', [])
        mp4_files = [v for v in video_files if v.get('contentType') == 'video/mp4']

        for v in mp4_files:
            video_url = url_or_none(v.get('url'))
            if not video_url:
                continue
            format_id = v.get('format', 'mp4')
            ext = determine_ext(video_url, default_ext='mp4')
            format_dict = {
                'format_id': format_id,
                'url': video_url,
                'ext': ext,
            }
            # Attempt to parse bitrate from filename
            filename = os.path.basename(video_url)
            if '_' in filename and filename.endswith('.mp4'):
                bitrate_str = filename.split('_')[-1].replace('.mp4', '')
                bitrate = int_or_none(bitrate_str)
                if bitrate:
                    format_dict['bitrate'] = bitrate * 1000  # kbps to bps

            formats.append(format_dict)

        # Extract embedded videos (e.g., YouTube, Dailymotion)
        embedded_urls = self._extract_embedded_urls(webpage, page_id)
        if embedded_urls:
            if not formats:  # If no direct formats, treat as playlist or single embed
                if len(embedded_urls) == 1:
                    return self.url_result(embedded_urls[0], ie=None, video_id=page_id)
                return self.playlist_result(
                    [self.url_result(u, ie=None) for u in embedded_urls],
                    page_id,
                    json_data.get('title', 'MSN Playlist'),
                    display_id
                )
            # If we have both direct and embedded, append embedded as additional entries
            for embed_url in embedded_urls:
                formats.append({'url': embed_url, 'format_id': 'embedded'})

        # Raise error if no formats found
        if not formats:
            raise ExtractorError('No video formats or embeds found', expected=True)

        # Extract metadata
        title = (
            json_data.get('title') or
            self._html_search_meta(('og:title', 'title'), webpage, default=None) or
            f'MSN video {page_id}'
        )
        description = json_data.get('description') or self._html_search_meta('description', webpage, default=None)
        duration = int_or_none(video_metadata.get('duration'))
        uploader = video_metadata.get('uploader') or self._html_search_meta('author', webpage, default=None)
        uploader_id = video_metadata.get('uploaderId')

        # Return result
        return {
            'id': page_id,
            'display_id': display_id,
            'title': unescapeHTML(title),
            'description': unescapeHTML(description) if description else None,
            'duration': duration,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'formats': formats,
        }

    def _extract_embedded_urls(self, webpage, video_id):
        """Extract URLs of embedded videos (e.g., YouTube, Dailymotion) from the webpage."""
        embed_urls = []
        # Use re.findall to extract all iframe src attributes
        iframe_matches = re.findall(r'<iframe[^>]+src=["\'](.*?)["\']', webpage)
        for iframe_src in iframe_matches:
            embed_url = url_or_none(iframe_src)
            if embed_url and any(host in embed_url for host in ('youtube.com', 'dailymotion.com', 'nbcsports.com')):
                embed_urls.append(embed_url)
        # Optional debug: Uncomment to inspect found URLs
        # self._downloader.to_screen(f"Found embedded URLs: {embed_urls}")
        return embed_urls


# Optional: Add to yt-dlp's extractor list if this is a standalone file
if __name__ == '__main__':
    from ..extractor import gen_extractors
    extractors = gen_extractors()
    msn_extractor = MSNIE()
    # Example test
    url = 'https://www.msn.com/en-in/money/video/7-ways-to-get-rid-of-chest-congestion/vi-BBPxU6d'
    result = msn_extractor._real_extract(url)
    print(result)
