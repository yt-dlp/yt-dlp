import re

from .common import InfoExtractor


class RDSITIE(InfoExtractor):
    IE_NAME = 'rds.it'
    _VALID_URL = r'https?://(?:www\.)?rds\.(?:it|radio)'
    _TESTS = [{
        'url': 'https://rds.it',
        'info_dict': {
            'id': 'rds',
            'ext': 'mp4',
            'title': r're:RDS',
            'description': 'Radio Dimensione Suono',
            'is_live': True,
            'track_id': int,
            'track': str,
            'thumbnail': r're:https://web\.rds\.it/',
            'concurrent_view_count': int,
            'live_status': 'is_live',
            'like_count': int,
        },
    }]
    _PATH_CODECS = {
        'rds': 'mp3',
        'rds_aac': 'aac',
        'rds_aac64': 'aac',
    }

    def _real_extract(self, url):
        sources = self._download_json('https://icecast.rds.radio/status-json.xsl', 'rds', 'Downloading JSON status')['icestats']['source']
        current_song = self._download_json('https://cdnapi.rds.it/v2/site/get_player_info', 'rds', 'Downloading JSON player')['song_status']['current_song']
        formats = self._extract_m3u8_formats('https://stream.rdstv.radio/index.m3u8', 'rds', m3u8_id='hls-rdstv')
        listeners = 0

        for s in sources:
            if s['server_name'] == 'RDS':
                if s.get('listeners'):
                    listeners += s['listeners']
                path = re.search(r'[^/]+$', s['listenurl']).group(0)
                formats.append({
                    'format_id': f'https-{path}',
                    'url': f'https://icstream.rds.radio/{path}',
                    'abr': s['bitrate'],
                    'acodec': self._PATH_CODECS.get(path),
                    'ext': self._PATH_CODECS.get(path),
                    'vcodec': 'none',
                    'format_note': 'HLS without m3u8',
                    'language': 'it',
                    'preference': -10,
                })
        # The codecs in the index are wrong
        mp3_formats = self._extract_m3u8_formats('https://stream.rds.radio/audio/rds.stream/index.m3u8', 'rds', 'mp3', quality=0, m3u8_id='hls-rds')
        for fmt in mp3_formats:
            fmt['acodec'] = 'mp3'
        formats.extend(mp3_formats)
        aac_formats = self._extract_m3u8_formats('https://stream.rds.radio/audio/rds.stream_aac/index.m3u8', 'rds', 'aac', m3u8_id='hls-rds_aac')
        for fmt in aac_formats:
            fmt['acodec'] = 'aac'
        formats.extend(aac_formats)
        aac64_formats = self._extract_m3u8_formats('https://stream.rds.radio/audio/rds.stream_aac64/index.m3u8', 'rds', 'aac', m3u8_id='hls-rds_aac')
        for fmt in aac64_formats:
            fmt['acodec'] = 'aac'
        formats.extend(aac64_formats)

        return {
            'id': 'rds',
            'title': 'RDS',
            'description': 'Radio Dimensione Suono',
            'is_live': True,
            'formats': formats,
            'concurrent_view_count': listeners,
            'thumbnail': current_song.get('cover'),
            'track': current_song.get('title'),
            'track_id': current_song.get('id'),
            'artists': current_song.get('artists').split(', ') if current_song.get('artists') else None,
            'like_count': current_song.get('likes'),
        }
