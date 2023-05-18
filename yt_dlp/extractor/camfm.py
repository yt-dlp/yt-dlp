from re import finditer
from urllib.parse import urljoin

from .common import InfoExtractor
from ..utils import join_nonempty, unified_timestamp


class CamFMBaseIE(InfoExtractor):
    def _absolute_url(self, path, root='https://camfm.co.uk'):
        return urljoin(root, path)


class CamFMShowIE(CamFMBaseIE):
    _VALID_URL = r'https://(?:www\.)?camfm\.co\.uk/shows/(?P<id>[^/]+)/?'
    _TESTS = [{
        'playlist_mincount': 0,
        'url': 'https://camfm.co.uk/shows/soul-mining/',
        'info_dict': {
            'id': 'soul-mining',
            'thumbnail': 'md5:6a873091f92c936f23bdcce80f75e66a',
            'title': 'Soul Mining',
            'description': 'Telling the stories of jazz, funk and soul from all corners of the world.',
        },
    }]

    def _real_extract(self, url):
        show_id = self._match_id(url)
        page = self._download_webpage(url, show_id)
        episodes = finditer(r"javascript:popup\('(/player/[^']+)', 'listen'", page)
        urls = [self._absolute_url(m.group(1)) for m in episodes]

        return {
            '_type': 'playlist',
            'id': show_id,
            'entries': [self.url_result(i, CamFMEpisodeIE) for i in urls],
            'thumbnail': self._absolute_url(self._search_regex(
                r'<img[^>]+class="thumb-expand"[^>]+src="([^"]+)"', page, 'thumbnail', fatal=False)),
            'title': self._html_search_regex('<h1>([^<]+)</h1>', page, 'title', fatal=False),
            'description': self._html_search_regex('<div class="small-12 medium-8 cell">\n(.*)',
                                                   page, 'description', fatal=False),
        }


class CamFMEpisodeIE(CamFMBaseIE):
    _VALID_URL = r'https://(?:www\.)?camfm\.co\.uk/player/(?P<id>[^/]+)/?'
    _TESTS = [{
        'url': 'https://camfm.co.uk/player/43336',
        'skip': 'Episode will expire - don\'t actually know when, but it will go eventually',
        'info_dict': {
            'id': '43336',
            'title': 'AITAA: Am I the Agony Aunt? - 19:00 Tue 16/05/2023',
            'ext': 'mp3',
            'upload_date': '20230516',
            'description': 'md5:f165144f94927c0f1bfa2ee6e6ab7bbf',
            'timestamp': 1684263600,
            'series': 'AITAA: Am I the Agony Aunt?',
            'thumbnail': 'md5:5980a831360d0744c3764551be3d09c1',
            'categories': ['Entertainment'],
        }
    }]

    def _real_extract(self, url):
        episode_id = self._match_id(url)
        page = self._download_webpage(url, episode_id)
        audios = self._parse_html5_media_entries('https://audio.camfm.co.uk', page, episode_id)
        formats = []
        for i in audios:
            formats.extend(i['formats'])

        series = self._html_search_regex(r'<div[^>]+class="caption">\n\s*(.+)', page, 'title', fatal=False)
        date = self._html_search_regex('>Aired at ([^<]+)<', page, 'air date', fatal=False)
        title = join_nonempty(series, date, delim=' - ')

        return {
            'id': episode_id,
            'title': title,
            'formats': formats,
            'timestamp': unified_timestamp(date),  # this will be off by an hour when DST is in effect
            # https://www.gov.uk/when-do-the-clocks-change - too annoying to calculate, will just treat as UTC
            # it'll be right half the time at least
            'series': series,
            'description': self._html_search_regex(r'>Aired at [^<]+<.*\n\s*(.*)', page, 'description', fatal=False),
            'thumbnail': self._absolute_url(self._search_regex(r'<div[^>]+class="cover-art"[^>]+style="[^"]+url\(\'([^\']+)\'\)[^>]+>',
                                            page, 'thumbnail', fatal=False)),
            'categories': [self._html_search_regex(r'<span[^>]+class="label"[^>]+>([^<]+)<', page, 'category', fatal=False)],
            'was_live': True,
        }
