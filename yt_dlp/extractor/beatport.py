import re

from .common import InfoExtractor
from ..utils import int_or_none


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
        },
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        track_id = mobj.group('id')
        display_id = mobj.group('display_id')

        webpage = self._download_webpage(url, display_id)

        playables = self._parse_json(
            self._search_regex(
                r'window\.Playables\s*=\s*({.+?});', webpage,
                'playables info', flags=re.DOTALL),
            track_id)

        track = next(t for t in playables['tracks'] if t['id'] == int(track_id))

        title = ', '.join(a['name'] for a in track['artists']) + ' - ' + track['name']
        if track['mix']:
            title += ' (' + track['mix'] + ')'

        formats = []
        for ext, info in track['preview'].items():
            if not info['url']:
                continue
            fmt = {
                'url': info['url'],
                'ext': ext,
                'format_id': ext,
                'vcodec': 'none',
            }
            if ext == 'mp3':
                fmt['acodec'] = 'mp3'
                fmt['abr'] = 96
                fmt['asr'] = 44100
            elif ext == 'mp4':
                fmt['acodec'] = 'aac'
                fmt['abr'] = 96
                fmt['asr'] = 44100
            formats.append(fmt)

        images = []
        for name, info in track['images'].items():
            image_url = info.get('url')
            if name == 'dynamic' or not image_url:
                continue
            image = {
                'id': name,
                'url': image_url,
                'height': int_or_none(info.get('height')),
                'width': int_or_none(info.get('width')),
            }
            images.append(image)

        return {
            'id': str(track.get('id')) or track_id,
            'display_id': track.get('slug') or display_id,
            'title': title,
            'formats': formats,
            'thumbnails': images,
        }
