import re
import urllib

from .common import InfoExtractor
from ..utils import ExtractorError


class AnimeSamaIE(InfoExtractor):
    IE_DESC = 'anime-sama.* season pages (playlist of episodes)'
    _VALID_URL = r'https?://(?:www\.)?anime\-sama\.(?:tv|si|to|org|fr|eu)/catalogue/(?P<slug>[^/]+)/(?P<season>saison(?P<season_num>\d+))/(?P<lang>vostfr|vf)/?'

    _TESTS = [
        {
            'url': 'https://anime-sama.tv/catalogue/one-piece/saison9/vostfr/',
            'only_matching': True,
        },
        {
            'url': 'https://anime-sama.tv/catalogue/naruto/saison1/vostfr/',
            'only_matching': True,
        },
        {
            'url': 'https://anime-sama.fr/catalogue/one-piece/saison9/vf/',
            'only_matching': True,
        },
    ]

    def _download_episodes_js(self, webpage_url: str, video_id: str) -> str:
        webpage = self._download_webpage(webpage_url, video_id)
        # The site references episodes.js with a cache buster: episodes.js?filever=123456
        js_path = self._search_regex(
            (r'(episodes\.js\?filever=\d+)', r'(episodes\.js)'),
            webpage, 'episodes js', default=None,
        )
        if not js_path:
            raise ExtractorError('episodes.js not found on the page', expected=True)
        episodes_js_url = urllib.parse.urljoin(webpage_url if webpage_url.endswith('/') else webpage_url + '/', js_path)
        return self._download_webpage(episodes_js_url, video_id, note='Downloading episodes.js')

    @staticmethod
    def _parse_players_from_js(episodes_js: str) -> list[list[str]]:
        # Find eps arrays: eps1 = ['host1ep1', 'host2ep1', ...]; eps2 = [...]
        # We need to zip these arrays per-index to obtain players per episode
        arrays = re.findall(r'eps(\d+)\s*=\s*\[([\s\S]+?)\]', episodes_js)
        lists: list[list[str]] = []
        for _idx, arr_content in arrays:
            links = re.findall(r"'(https?://[^']+)'", arr_content)
            # Normalize some legacy domains
            links = [link.replace('vidmoly.to', 'vidmoly.net') for link in links]
            lists.append(links)
        if not lists:
            return []
        max_len = max((len(l) for l in lists), default=0)
        episodes_players: list[list[str]] = []
        for i in range(max_len):
            ep_players: list[str] = []
            for l in lists:
                if i < len(l):
                    ep_players.append(l[i])
            if len(ep_players) >= 2:
                # swap first two players as done in the reference project
                ep_players[0], ep_players[1] = ep_players[1], ep_players[0]
            if ep_players:
                episodes_players.append(ep_players)
        return episodes_players

    def _real_extract(self, url):
        m = self._match_valid_url(url)
        slug = m.group('slug')
        season = m.group('season')
        season_num = m.group('season_num')
        lang = m.group('lang')
        playlist_id = f'{slug}-{season}-{lang}'
        playlist_title = f'{slug} {season} {lang}'

        episodes_js = self._download_episodes_js(url, playlist_id)
        episodes_players = self._parse_players_from_js(episodes_js)

        if not episodes_players:
            raise ExtractorError('No episodes found for this season/language', expected=True)

        entries = []
        for idx, players in enumerate(episodes_players, start=1):
            # Prefer non-vidmoly players as yt-dlp currently has no dedicated extractor for vidmoly embeds.
            # Logic adapted from the downloader in concat.txt (Players.sort_and_filter/ban):
            #  - filter banned hosts (here: vidmoly)
            #  - keep original order otherwise
            if not players:
                continue
            non_vidmoly = [
                p for p in players
                if 'vidmoly' not in ((urllib.parse.urlparse(p).hostname or '').lower())
            ]
            if non_vidmoly:
                player_url = non_vidmoly[0]
            else:
                # No alternative available; keep behavior but warn so the user can adjust with --playlist-items
                self.report_warning(
                    f'Episode {idx}: only vidmoly players found; falling back to vidmoly (may be unsupported)',
                )
                player_url = players[0]

            title = f'{slug} {season} Episode {idx} ({lang.upper()})'
            entry = self.url_result(player_url, video_title=title)
            entry.update({
                'series': slug.replace('-', ' '),
                'season_number': int(season_num) if season_num else None,
                'episode_number': idx,
                'season': season,
                'episode': f'Episode {idx}',
                'language': lang,
            })
            entries.append(entry)

        return self.playlist_result(entries, playlist_id=playlist_id, playlist_title=playlist_title)
