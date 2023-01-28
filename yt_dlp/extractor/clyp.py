from .common import InfoExtractor
from ..utils import (
    float_or_none,
    parse_qs,
    unified_timestamp,
)


class ClypIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?clyp\.it/(?P<id>[a-z0-9]+)'
    _TESTS = [{
        'url': 'https://clyp.it/iynkjk4b',
        'md5': '0e4aed7114549d6798f342e4e0386a9d',
        'info_dict': {
            'id': 'iynkjk4b',
            'ext': 'mp3',
            'title': 'research',
            'description': '#Research',
            'duration': 51.278,
            'timestamp': 1435524981,
            'upload_date': '20150628',
        },
    }, {
        'url': 'https://clyp.it/b04p1odi?token=b0078e077e15835845c528a44417719d',
        'info_dict': {
            'id': 'b04p1odi',
            'ext': 'mp3',
            'title': 'GJ! (Reward Edit)',
            'description': 'Metal Resistance (THE ONE edition)',
            'duration': 177.789,
            'timestamp': 1528241278,
            'upload_date': '20180605',
        },
        'params': {
            'skip_download': True,
        },
    }, {
        'url': 'https://clyp.it/v42214lc',
        'md5': '4aca4dfc3236fb6d6ddc4ea08314f33f',
        'info_dict': {
            'id': 'v42214lc',
            'ext': 'wav',
            'title': 'i dont wanna go (old version)',
            'description': None,
            'duration': 113.528,
            'timestamp': 1607348505,
            'upload_date': '20201207',
        },
        'params': {
            'format': 'wavStreamUrl',
        },
    }]

    def _real_extract(self, url):
        audio_id = self._match_id(url)

        qs = parse_qs(url)
        token = qs.get('token', [None])[0]

        query = {}
        if token:
            query['token'] = token

        metadata = self._download_json(
            'https://api.clyp.it/%s' % audio_id, audio_id, query=query)

        formats = []
        for secure in ('', 'Secure'):
            for ext in ('Ogg', 'Mp3'):
                format_id = '%s%s' % (secure, ext)
                format_url = metadata.get('%sUrl' % format_id)
                if format_url:
                    formats.append({
                        'url': format_url,
                        'format_id': format_id,
                        'vcodec': 'none',
                    })

        page = self._download_webpage(url, video_id=audio_id)
        wav_url = self._html_search_regex(
            r'var\s*wavStreamUrl\s*=\s*["\'](?P<url>https?://[^\'"]+)', page, 'url', default='')
        if wav_url:
            formats.append({
                'url': wav_url,
                'format_id': 'wavStreamUrl',
                'vcodec': 'none',
            })

        title = metadata['Title']
        description = metadata.get('Description')
        duration = float_or_none(metadata.get('Duration'))
        timestamp = unified_timestamp(metadata.get('DateCreated'))

        return {
            'id': audio_id,
            'title': title,
            'description': description,
            'duration': duration,
            'timestamp': timestamp,
            'formats': formats,
        }
