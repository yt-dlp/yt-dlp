from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    float_or_none,
    parse_qs,
    unified_timestamp,
)


class ClypIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?clyp\.it/(?P<id>[a-z0-9]+)'
    _TESTS = [{
        'url': 'https://clyp.it/ojz2wfah',
        'md5': '1d4961036c41247ecfdcc439c0cddcbb',
        'info_dict': {
            'id': 'ojz2wfah',
            'ext': 'mp3',
            'title': 'Krisson80 - bits wip wip',
            'description': '#Krisson80BitsWipWip #chiptune\n#wip',
            'duration': 263.21,
            'timestamp': 1443515251,
            'upload_date': '20150929',
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
        self._sort_formats(formats)

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
