import re

from yt_dlp.extractor.common import InfoExtractor


class JutsuIE(InfoExtractor):
    # Regex to match URLs for full series pages or individual episodes/films
    _VALID_URL = (
        r'https?://(?:www\.)?jut\.su/(?P<id>[^/]+)'
        r'(?:/(?:season-(?P<season>\d+)/)?(?P<episode>(?:episode|film)-(?P<epnum>\d+))\.html)?/?'
    )

    _TESTS = [
        {
            'url': 'https://jut.su/apocalypse-hotel/',
            'playlist_mincount': 1,
            'info_dict': {
                'id': 'apocalypse-hotel',
                'title': 'Отель в Апокалипсис',
            },
        },
        {
            'url': 'https://jut.su/apocalypse-hotel/episode-4.html',
            'info_dict': {
                'id': 'episode-4',
                'title': 'Отель в Апокалипсис 4 серия',
            },
        },
    ]

    def _extract_episode(self, url, video_id, season=None, episode_number=None, episode_page=None):
        # Download the episode page if not provided
        if episode_page is None:
            episode_page = self._download_webpage(
                url,
                video_id,
                note=f'Downloading episode page {url}',
                headers={
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0',
                },
            )

        # Extract episode title from <h1> tag
        episode_title = self._html_search_regex(
            r'<h1[^>]*>\s*<span[^>]*>\s*(?:<i>\s*Смотреть\s*</i>)?\s*(.+?)\s*</span>',
            episode_page,
            'episode title',
            fatal=False,
        ) or video_id

        # Headers used for downloading video files
        video_headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0',
            'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
        }

        # Extract video sources from <source> tags
        sources = re.findall(
            r'<source[^>]+src="([^"]+?)"[^>]*label="([^"]+)?"', episode_page
        )

        formats = []
        for src, label in sources:
            height = int(label.rstrip('p')) if label and label.endswith('p') else None
            formats.append({
                'url': src,
                'format_id': label,
                'height': height,
                'ext': 'mp4',
                'http_headers': video_headers,
            })

        if not formats:
            self.report_warning(f'No video formats found in {url}')
            return None

        # Use the last part of the URL as unique episode ID
        ep_id = url.rstrip('/').split('/')[-1].replace('.html', '')
        return {
            'id': ep_id,
            'title': episode_title,
            'formats': formats,
        }

    def _real_extract(self, url):
        # Parse the URL with regex and extract metadata
        mobj = self._match_valid_url(url)
        video_id = mobj.group('id')
        season = mobj.group('season')
        episode_number = mobj.group('epnum')

        # If this is a single episode or film page
        if episode_number:
            return self._extract_episode(url, video_id, season, episode_number)

        # Otherwise treat it as a playlist (series page)
        webpage = self._download_webpage(
            url,
            video_id,
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0',
            },
        )

        # Try to extract series title from <title> tag
        title = self._html_search_regex(
            r'<title>\s*(.+?)\s*(?:все\s+серии|смотреть онлайн)?\s*</title>',
            webpage,
            'title',
            fatal=False,
        ) or video_id

        entries = []
        # Find all episode links from buttons on the page
        episode_links = re.finditer(
            r'<a[^>]+href="([^"]+)"[^>]*class="[^\"]*short-btn[^\"]*(?:black|green)[^\"]*video[^\"]*"[^>]*>'
            r'(?:<i>[^<]*</i>)?[^<]*(\d+)\s*(?:серия|фильм)</a>',
            webpage,
        )

        for ep_link in episode_links:
            episode_url = ep_link.group(1)
            if not episode_url.startswith('http'):
                episode_url = 'https://jut.su' + episode_url if episode_url.startswith('/') else 'https://jut.su/' + episode_url

            episode_page = self._download_webpage(
                episode_url,
                video_id,
                note=f'Downloading episode page {episode_url}',
                headers={
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0',
                },
            )

            info = self._extract_episode(episode_url, video_id, episode_page=episode_page)
            if info:
                entries.append(info)

        return {
            '_type': 'playlist',
            'id': video_id,
            'title': title,
            'entries': entries,
        }
