import base64
import re

from .common import InfoExtractor
from ..utils import ExtractorError, int_or_none, str_or_none, unified_strdate, urljoin


class FootballiaBaseIE(InfoExtractor):
    _BASE_URL = 'https://footballia.net'

    @staticmethod
    def _decode_b64_url(value):
        return base64.b64decode(re.sub(r'(?:\\[rn]|[\r\n\t ]+)', '', value)).decode('utf-8')

    # parsing as JSON since it exposes structured data for each video part
    def _extract_match_url_parts(self, webpage, video_id):
        playlist = self._search_json(
            r'\bvar\s+playlist\s*=', webpage, 'playlist', video_id,
            contains_pattern=r'\[(?s:.+)\]', default=[])

        parts = []
        for idx, entry in enumerate(playlist, start=1):
            encoded_url = entry.get('file')
            if not encoded_url:
                raise ExtractorError(f'Could not find video URL for part {idx}')
            image = entry.get('image')
            parts.append({
                'id': str_or_none(entry.get('mediaid')),
                'part_number': idx,
                'thumbnail': urljoin(self._BASE_URL, image),
                'url': self._decode_b64_url(encoded_url),
            })
        return parts

    def _extract_single_url_match(self, webpage, video_id):
        video_url = self._decode_b64_url(self._search_regex(
            r'new\s+Video\(\s*"([^"]+)"\s*\)', webpage, 'encoded video url'))
        return {
            'id': self._search_regex(r'\bmediaid\s*:\s*(\d+)', webpage, 'media id', default=video_id),
            'url': video_url,
        }

    def _extract_match_metadata(self, webpage):
        title = (
            self._og_search_title(webpage, default=None)
            or self._html_search_regex(r'<h1[^>]*>\s*([^<]+?)\s+full match\s*</h1>', webpage, 'title', default=None)
            or self._html_extract_title(webpage))

        home_team = self._search_regex(
            r'<[^>]+itemprop="homeTeam"[^>]*>[\s\S]+?<span[^>]+itemprop="name"[^>]*>([^<]+)',
            webpage, 'home team', default=None)

        away_team = self._search_regex(
            r'<[^>]+itemprop="awayTeam"[^>]*>[\s\S]+?<span[^>]+itemprop="name"[^>]*>([^<]+)',
            webpage, 'away team', default=None)

        # Synthesize a title from team names when the page does not provide one
        if not title and home_team and away_team:
            title = f'{home_team} vs. {away_team}'

        description = self._html_search_meta(['description', 'og:description', 'twitter:description'], webpage, default=None)

        thumbnail = (
            self._html_search_meta('og:image', webpage, default=None)
            or self._og_search_thumbnail(webpage)
        )
        competition = self._search_regex(
            r'<div[^>]+class="competition"[^>]*>[\s\S]*?<a[^>]*>([^<]+)</a>', webpage, 'competition', default=None)

        season = self._search_regex(
            r'<div[^>]+class="[^"]*\bcompetition\b[^"]*"[^>]*>[\s\S]*?</a>\s*([0-9]{4}(?:-[0-9]{4})?)',
            webpage, 'season', default=None)

        stage = self._search_regex(r'<div[^>]+class="stage"[^>]*>([^<]+)</div>', webpage, 'stage', default=None)

        location = self._search_regex(
            r'<div[^>]+class=["\'][^"\']*\bvenue\b[^"\']*["\'][^>]*>[\s\S]*?<span[^>]+itemprop=["\']name["\'][^>]*>([^<]+)</span>',
            webpage, 'location', default=None)

        match_date = self._search_regex(
            r'<div[^>]+class=["\'][^"\']*\bplaying_date\b[^"\']*["\'][^>]*content=["\']([^"\']+)["\']',
            webpage, 'match date', default=None)

        cast = re.findall(r'<tr class="(?:player|coaches)"[^>]*itemprop="competitor"[\s\S]*?'
                          r'<span[^>]*itemprop="name"[^>]*>([^<]+)', webpage)

        score = self._search_regex(
            r'(?s)<div[^>]+class=["\']result["\'][^>]*>.*?'
            r'<span[^>]+style=["\'][^"\']*display\s*:\s*none[^"\']*["\'][^>]*>\s*'
            r'(\d+)\s*:\s*(\d+)',
            webpage, 'match result', default=(None, None), group=(1, 2))

        info = {
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'home_team': home_team,
            'away_team': away_team,
            'home_score': int_or_none(score[0]),
            'away_score': int_or_none(score[1]),
            'series': competition,
            'season': season,
            'episode': stage,
            'location': location,
            'cast': list(dict.fromkeys(cast)) or None,
            'release_date': unified_strdate(match_date) if match_date else None,
        }
        return {k: v for k, v in info.items() if v is not None}

    def _build_video_entry(self, video_id, title, part_url, metadata, part_number=None):
        # Propagate match-level metadata to each part so output templates
        entry = {
            'id': video_id,
            'formats': [{
                'format_id': 'http-mp4',
                'url': part_url,
                'ext': 'mp4',
                'http_headers': {'Referer': f'{self._BASE_URL}/'},
            }],
            **metadata,
        }
        entry['title'] = f'{title} - Part {part_number}' if part_number else title
        return entry

    def _extract_match(self, url, video_id):
        webpage = self._download_webpage(url, video_id)

        if re.search(r'Sign\s+up\s+for\s+free', webpage):
            self.raise_login_required(
                'This match requires a Footballia account; '
                'use --cookies-from-browser or --cookies to authenticate',
                method='cookies')

        metadata = self._extract_match_metadata(webpage)
        title = metadata.get('title') or video_id

        parts = self._extract_match_url_parts(webpage, video_id)

        if parts:
            # Use first part thumbnail as fallback if page metadata lacks one
            if not metadata.get('thumbnail'):
                metadata['thumbnail'] = parts[0].get('thumbnail')

            # Single-part match: return as a single video, not a playlist
            if len(parts) == 1:
                part = parts[0]
                return self._build_video_entry(part['id'], title, part['url'], metadata)

            # Multi-part match (e.g., first/second half): return as multi_video
            entries = []
            for part in parts:
                entries.append(
                    self._build_video_entry(part['id'], title, part['url'], metadata, part['part_number']))

            return {
                '_type': 'multi_video',
                'id': video_id,
                'title': title,
                'entries': entries,
                **metadata,
            }

        # Fallback: legacy single-video page format
        single = self._extract_single_url_match(webpage, video_id)
        return self._build_video_entry(single['id'], title, single['url'], metadata)

    # Deduplicate match URLs while preserving their original order
    def _extract_playlist_entries(self, webpage):
        paths = re.findall(r'<td[^>]+class="match"[^>]*>[\s\S]*?href="(/[^"]+)"', webpage)
        unique_paths = dict.fromkeys(paths)
        return [
            self.url_result(f'{self._BASE_URL}{path}', ie=FootballiaIE)
            for path in unique_paths
        ]

    def _extract_playlist_page(self, url, playlist_id):
        webpage = self._download_webpage(url, playlist_id)
        title = (
            self._og_search_title(webpage, default=None)
            or self._html_search_regex(
                r'<div[^>]+class="search-results"[^>]*>\s*<h1>([^<]+)</h1>',
                webpage, 'titile', default=playlist_id)
        )
        description = self._og_search_description(webpage, default=None)
        thumbnail = self._og_search_thumbnail(webpage, default=None)
        entries = self._extract_playlist_entries(webpage)

        return self.playlist_result(entries, playlist_id, title, description, thumbnail=thumbnail)


class FootballiaIE(FootballiaBaseIE):
    # Single match extractor. Supports URLs in multiple languages
    # (en: /matches/, pt: /jogos-completos/, es: /partidos-completos/)
    _VALID_URL = r'https?://footballia\.net/(?:[a-z]{2}/)?(?:matches|jogos-completos|matchs-complets|ganze-spiele|partite-complete|partidos-completos)/(?P<id>[^/?#]+)'
    _TESTS = [{
        # Multi-part match (2 video files)
        'url': 'https://footballia.net/matches/fc-porto-fc-internazionale-champions-league-2022-2023',
        'info_dict': {
            'id': 'fc-porto-fc-internazionale-champions-league-2022-2023',
            'title': 'FC Porto vs. FC Internazionale',
            'description': 'md5:7e0aaf3c87cc1f70cc05f5b41bf65086',
            'thumbnail': r're:^https?://footballia\.net/cache/matches/.+\.png$',
            'home_team': 'FC Porto',
            'away_team': 'FC Internazionale',
            'series': 'Champions League',
            'season': '2022-2023',
            'episode': 'Round of 16, 2nd leg',
            'location': 'Estádio do Dragão (Porto)',
            'release_date': '20230314',
        },
        'playlist_count': 2,
        'skip': 'Requires authentication',
        'playlist': [{
            'info_dict': {
                'id': '51610',
                'ext': 'mp4',
                'title': 'FC Porto vs. FC Internazionale - Part 1',
            },
        }, {
            'info_dict': {
                'id': '51612',
                'ext': 'mp4',
                'title': 'FC Porto vs. FC Internazionale - Part 2',
            },
        }],
    }, {
        'url': 'https://footballia.net/pt/jogos-completos/fc-porto-fc-internazionale-champions-league-2022-2023',
        'only_matching': True,
    }, {
        'url': 'https://footballia.net/fr/matchs-complets/fc-porto-fc-internazionale-champions-league-2022-2023',
        'only_matching': True,
    }, {
        'url': 'https://footballia.net/es/partidos-completos/fc-porto-fc-internazionale-champions-league-2022-2023',
        'only_matching': True,
    }, {
        'url': 'https://footballia.net/de/ganze-spiele/fc-porto-fc-internazionale-champions-league-2022-2023',
        'only_matching': True,
    }, {
        'url': 'https://footballia.net/it/partite-complete/fc-porto-fc-internazionale-champions-league-2022-2023',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        return self._extract_match(url, self._match_id(url))


class FootballiaCompetitionIE(FootballiaBaseIE):
    # Competition page extractor (e.g., World Cup, Champions League).
    # Returns a playlist with all available matches of that competition.
    _VALID_URL = r'https?://footballia\.net/(?:[a-z]{2}/)?(?:competitions|competicoes|competiciones|competizioni|wettbewerbe)/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://footballia.net/competitions/world-cup',
        'info_dict': {
            'id': 'world-cup',
            'title': 'World Cup full matches',
            'description': 'Watch full World Cup football matches online on Footballia',
        },
        'playlist_mincount': 40,
        'skip': 'Requires authentication',
    }, {
        'url': 'https://footballia.net/pt/competicoes/world-cup',
        'only_matching': True,
    }, {
        'url': 'https://footballia.net/es/competiciones/world-cup',
        'only_matching': True,
    }, {
        'url': 'https://footballia.net/fr/competitions/world-cup',
        'only_matching': True,
    }, {
        'url': 'https://footballia.net/it/competizioni/world-cup',
        'only_matching': True,
    }, {
        'url': 'https://footballia.net/de/wettbewerbe/world-cup',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        return self._extract_playlist_page(url, self._match_id(url))


class FootballiaTeamIE(FootballiaBaseIE):
    # Team page extractor (e.g., Sporting CP, Barcelona).
    # Returns a playlist with all available matches of that team.
    _VALID_URL = r'https?://footballia\.net/(?:[a-z]{2}/)?(?:teams|equipas|equipos|equipes|squadre|vereine)/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://footballia.net/teams/fc-porto',
        'info_dict': {
            'id': 'fc-porto',
            'title': 'FC Porto full matches',
            'description': 'Watch full FC Porto football matches online on Footballia',
        },
        'playlist_mincount': 40,
        'skip': 'Requires authentication',
    }, {
        'url': 'https://footballia.net/pt/equipas/fc-porto',
        'only_matching': True,
    }, {
        'url': 'https://footballia.net/es/equipos/fc-porto',
        'only_matching': True,
    }, {
        'url': 'https://footballia.net/fr/equipes/fc-porto',
        'only_matching': True,
    }, {
        'url': 'https://footballia.net/it/squadre/fc-porto',
        'only_matching': True,
    }, {
        'url': 'https://footballia.net/de/vereine/fc-porto',
        'only_matching': True,
    },
    ]

    def _real_extract(self, url):
        return self._extract_playlist_page(url, self._match_id(url))


class FootballiaHeadToHeadIE(FootballiaBaseIE):
    # Head-to-head extractor: matches between two specific teams.
    # Unlike Competition and Team pages, the URL uses query params with
    # numeric team IDs rather than slugs in the path.
    _VALID_URL = r'https?://footballia\.net/(?:[a-z]{2}/)?(?:search_head_to_head|pesquisa-enfrentamentos|busqueda-enfrentamientos|chercher-rencontres|cerca-scontri|direkte-begegnung)\?(?P<id>[^#]+)'
    _TESTS = [{
        'url': 'https://footballia.net/search_head_to_head?team_one_id=104&team_one_name=CR+Flamengo&team_two_id=105&team_two_name=CR+Vasco+da+Gama&utf8=%E2%9C%93',
        'info_dict': {
            'id': 'h2h-104-105',
            'title': 'Watch full CR Flamengo vs CR Vasco da Gama football matches online on Footballia',
            'description': 'Watch full CR Flamengo vs CR Vasco da Gama football matches online on Footballia',
        },
        'playlist_mincount': 40,
        'skip': 'Requires authentication',
    }, {
        'url': 'https://footballia.net/search_head_to_head?team_one_id=104&team_two_id=105',
        'only_matching': True,
    }, {
        'url': 'https://footballia.net/pt/pesquisa-enfrentamentos?team_one_id=104&team_one_name=CR+Flamengo&team_two_id=105&team_two_name=CR+Vasco+da+Gama&utf8=%E2%9C%93',
        'only_matching': True,
    }, {
        'url': 'https://footballia.net/es/busqueda-enfrentamientos?team_one_id=104&team_two_id=105',
        'only_matching': True,
    }, {
        'url': 'https://footballia.net/fr/chercher-rencontres?team_one_id=104&team_two_id=105',
        'only_matching': True,
    }, {
        'url': 'https://footballia.net/it/cerca-scontri?team_one_id=104&team_two_id=105',
        'only_matching': True,
    }, {
        'url': 'https://footballia.net/de/direkte-begegnung?team_one_id=104&team_two_id=105',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        # Build a stable playlist_id from numeric team IDs; team name encoding
        # in the URL varies across locales but IDs are consistent.
        mobj = re.search(r'team_one_id=(\d+).*?team_two_id=(\d+)', url)
        playlist_id = f'h2h-{mobj.group(1)}-{mobj.group(2)}' if mobj else self._match_id(url)
        return self._extract_playlist_page(url, playlist_id)


class FootballiaPlayerIE(FootballiaBaseIE):
    # Player page extractor (e.g., Ronaldo, Pelé).
    # Returns a playlist of all matches the player appeared in.
    _VALID_URL = r'https?://footballia\.net/(?:[a-z]{2}/)?(?:players|jogadores|jugadores|joueurs|giocatori|spielern)/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://footballia.net/players/ronal-david-de-jesus-ogonaga',
        'info_dict': {
            'id': 'Ronal David de Jesús Ogonaga',
            'title': 'Ronal David de Jesús Ogonaga full matches',
            'description': 'Watch full Ronal David de Jesús Ogonaga football matches online on Footballia',
        },
        'playlist_mincount': 6,
        'skip': 'Requires authentication',
    }, {
        'url': 'https://footballia.net/pt/jogadores/ronal-david-de-jesus-ogonaga',
        'only_matching': True,
    }, {
        'url': 'https://footballia.net/es/jugadores/ronal-david-de-jesus-ogonaga',
        'only_matching': True,
    }, {
        'url': 'https://footballia.net/fr/joueurs/ronal-david-de-jesus-ogonaga',
        'only_matching': True,
    }, {
        'url': 'https://footballia.net/it/giocatori/ronal-david-de-jesus-ogonaga',
        'only_matching': True,
    }, {
        'url': 'https://footballia.net/de/spielern/ronal-david-de-jesus-ogonaga',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        return self._extract_playlist_page(url, self._match_id(url))
