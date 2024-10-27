from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    mimetype2ext,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class VidlyIE(InfoExtractor):
    _VALID_URL = r'https?://(?:vid\.ly/|(?:s\.)?vid\.ly/embeded\.html\?(?:[^#]+&)?link=)(?P<id>\w+)'
    _EMBED_REGEX = [r'<script[^>]+\bsrc=[\'"](?P<url>(?:https?:)?//vid\.ly/\w+/embed[^\'"]+)',
                    r'<iframe[^>]+\bsrc=[\'"](?P<url>(?:https?:)?//(?:s\.)?vid\.ly/embeded\.html\?(?:[^#\'"]+&)?link=\w+[^\'"]+)']
    _TESTS = [{
        # JWPlayer 7, Embeds forbidden
        'url': 'https://vid.ly/2i3o9j/embed',
        'info_dict': {
            'id': '2i3o9j',
            'ext': 'mp4',
            'title': '2i3o9j',
            'thumbnail': r're:https://\w+\.cloudfront\.net/',
        },
    }, {
        # JWPlayer 6
        'url': 'http://s.vid.ly/embeded.html?link=jw_test&new=1&autoplay=true&controls=true',
        'info_dict': {
            'id': 'jw_test',
            'ext': 'mp4',
            'title': '2x8m8t',
            'thumbnail': r're:https://\w+\.cloudfront\.net/',
        },
    }, {
        # Vidlyplayer
        'url': 'https://vid.ly/7x0e6l',
        'info_dict': {
            'id': '7x0e6l',
            'ext': 'mp4',
            'title': '7x0e6l',
        },
    }]
    _WEBPAGE_TESTS = [{
        'url': 'https://www.petfinder.com/dog/gus-57378930/tn/ooltewah/furever-furkids-rescue-tn592/',
        'info_dict': {
            'id': 'w8p5b0',
            'ext': 'mp4',
            'title': 'w8p5b0',
            'thumbnail': r're:https://\w+\.cloudfront\.net/',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        embed_script = self._download_webpage(
            f'https://vid.ly/{video_id}/embed', video_id, headers={'Referer': 'https://vid.ly/'})
        player = self._search_json(r'initCallback\(', embed_script, 'player', video_id)

        player_type = player.get('player') or ''
        if player_type.startswith('jwplayer'):
            return self._parse_jwplayer_data(player['config'], video_id)
        elif not player_type.startswith('vidly'):
            raise ExtractorError(f'Unknown player type {player_type!r}')

        formats = []
        ext = mimetype2ext(traverse_obj(player, ('config', 'type')))
        for source, fid in [('source', 'sd'), ('source_hd', 'hd')]:
            if traverse_obj(player, ('config', source, {url_or_none})):
                formats.append({
                    'url': player['config'][source],
                    'format_id': f'http-{fid}',
                    'ext': ext,
                })
        # Has higher quality formats
        formats.extend(self._extract_m3u8_formats(
            f'https://d3fenhwk93s16g.cloudfront.net/{video_id}/hls.m3u8', video_id,
            fatal=False, note='Requesting higher quality m3u8 formats',
            errnote='No higher quality m3u8 formats found') or [])

        return {
            'id': video_id,
            'title': video_id,
            'formats': formats,
        }
