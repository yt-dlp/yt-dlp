from .common import InfoExtractor


class AsportIE(InfoExtractor):
    _VALID_URL = r'https?://(?P<domain>rollstuhlsport\.asport\.tv|(?:www\.|cheerleading\.)?sportpassaustria\.at|(?:www\.)?sportaustriafinals\.tv|video\.stv-fsg\.ch|(?:www\.)?swissleague\.tv|(?:www\.)?volleyballarena\.tv)/event/(?P<id>\d+)/[0-9a-z-]*'

    _TESTS = [{
        'url': 'https://video.stv-fsg.ch/event/58367/lausanne-2025-schlussfeier-highlight-clip-rts',
        'info_dict': {
            'id': '58367',
            'ext': 'mp4',
            'title': 'Lausanne 2025 | Schlussfeier | Highlight-Clip RTS',
            'description': 'md5:42c0254e199462c1390149f8ab5a8e6b',
            'duration': 86.0,
            'thumbnail': 'https://video.stv-fsg.ch/assets/images/events/7/6/58367/68584f18_219907_lausanne-2025-schlussfeie.jpeg',
            'timestamp': 1750587300,
            'upload_date': '20250622',
        },
    }, {
        'url': 'https://www.sportpassaustria.at/event/66588/schach-im-turm',
        'info_dict': {
            'id': '66588',
            'ext': 'mp4',
            'title': 'Schach im Turm | 07.12.2025',
            'description': 'md5:29eaa4b667286b777b30f8fdd601e51c',
            'duration': 16178.0,
            'thumbnail': 'https://sportpassaustria.at/assets/images/events/8/8/66588/693019a9__schach-im-turm.jpeg',
            'timestamp': 1765103400,
            'upload_date': '20251207',
        },
    }, {
        'url': 'https://volleyballarena.tv/event/60678/viteos-nuc-volley-dudingen',
        'only_matching': True,
    }, {
        'url': 'https://cheerleading.sportpassaustria.at/event/40868/team-austria-senior-double-pom-finale-icu-world-cheerleading-championships-2024',
        'only_matching': True,
    }, {
        'url': 'https://rollstuhlsport.asport.tv/event/44759/game-4-portugal-lettland',
        'only_matching': True,
    }, {
        'url': 'https://sportaustriafinals.tv/event/58392/wakeboard-stieber-neuer-sieger-flemme-machts-erneut-saf25',
        'only_matching': True,
    }, {
        'url': 'https://swissleague.tv/event/67102/ehc-basel-ehc-visp',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        domain, video_id = self._match_valid_url(url).group('domain', 'id')

        webpage = self._download_webpage(url, video_id)
        json_ld_data = self._search_json_ld(webpage, video_id)

        player_data = self._download_json(f'https://{domain}/api/v1/event/{video_id}/playout', video_id)
        formats, subtitles = self._extract_m3u8_formats_and_subtitles(player_data['hlsUrl'], video_id)

        return {
            'id': video_id,
            **json_ld_data,
            'formats': formats,
            'subtitles': subtitles,
        }
