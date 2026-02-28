#A simple videyhome.site extractor, only url replacement

from .common import InfoExtractor

class VideyHomeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?videyhome\.site/v/\?id=(?P<id>[a-zA-Z0-9_-]+)'
    
    _TESTS = [{
        'url': 'https://videyhome.site/v/?id=Tf4EKQJK1',
        'info_dict': {
            'id': 'Tf4EKQJK1',
            'ext': 'mp4',
            'title': 'Tf4EKQJK1',
        },
    }]

    def _real_extract(self, url):
        
        video_id = self._match_id(url)
        base_url = f'https://cdn.videy.co/{video_id}'

        formats = []

        formats.append({
            'format_id': 'mp4',
            'url': f'{base_url}.mp4',
            'ext': 'mp4',
            'quality': 1,
        })

        formats.append({
            'format_id': 'mov',
            'url': f'{base_url}.mov',
            'ext': 'mov',
            'quality': -1, 
        })

        return {
            'id': video_id,
            'title': video_id,
            'formats': formats,
        }
