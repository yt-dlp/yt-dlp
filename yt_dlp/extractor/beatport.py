import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import int_or_none, ExtractorError


class BeatportIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.|pro\.)?beatport\.com/track/(?P<display_id>[^/]+)/(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://beatport.com/track/synesthesia-original-mix/5379371',
        'md5': 'b3c34d8639a2f6a7f734382358478887',
        'info_dict': {
            'id': '5379371',
            'display_id': 'synesthesia-original-mix',
            'ext': 'mp4',
            'title': 'Froxic - Synesthesia (Original Mix)',
        },
    }, {
        'url': 'https://beatport.com/track/love-and-war-original-mix/3756896',
        'md5': 'e44c3025dfa38c6577fbaeb43da43514',
        'info_dict': {
            'id': '3756896',
            'display_id': 'love-and-war-original-mix',
            'ext': 'mp3',
            'title': 'Wolfgang Gartner - Love & War (Original Mix)',
        },
    }, {
        'url': 'https://beatport.com/track/birds-original-mix/4991738',
        'md5': 'a1fd8e8046de3950fd039304c186c05f',
        'info_dict': {
            'id': '4991738',
            'display_id': 'birds-original-mix',
            'ext': 'mp4',
            'title': "Tos, Middle Milk, Mumblin' Johnsson - Birds (Original Mix)",
        }
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        track_id = mobj.group('id')
        display_id = mobj.group('display_id')

        webpage = self._download_webpage(url, display_id)

        try:
            playables_json = self._search_regex(
                r'window\.Playables\s*=\s*({.+?})\s*;', webpage,
                'playables info', default='{}', flags=re.DOTALL)
            playables = self._parse_json(playables_json, track_id)
        except re.error:
            raise ExtractorError('Failed to extract playables information. The page structure may have changed.')

        if not playables or 'tracks' not in playables:
            raise ExtractorError('No playable tracks found in the extracted information.')

        track = next((t for t in playables['tracks'] if t['id'] == int(track_id)), None)
        if not track:
            raise ExtractorError(f'No track with ID {track_id} found.')

        title = ', '.join(a['name'] for a in track['artists']) + ' - ' + track['name']
        if track.get('mix'):
            title += ' (' + track['mix'] + ')'

        formats = []
        for ext, info in track.get('preview', {}).items():
            url = info.get('url')
            if url:
                fmt = {
                    'url': url,
                    'ext': ext,
                    'format_id': ext,
                    'vcodec': 'none',
                    'acodec': 'mp3' if ext == 'mp3' else 'aac',
                    'abr': 96,
                    'asr': 44100
                }
                formats.append(fmt)

        images = [{'id': name, 'url': info['url'], 'height': int_or_none(info.get('height')), 'width': int_or_none(info.get('width'))}
                  for name, info in track.get('images', {}).items() if name != 'dynamic' and info.get('url')]

        return {
            'id': compat_str(track.get('id', track_id)),
            'display_id': track.get('slug', display_id),
            'title': title,
            'formats': formats,
            'thumbnails': images
        }