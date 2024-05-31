import urllib.parse

from .common import InfoExtractor
from ..utils import unified_strdate


class UrortIE(InfoExtractor):
    _WORKING = False
    IE_DESC = 'NRK P3 Urørt'
    _VALID_URL = r'https?://(?:www\.)?urort\.p3\.no/#!/Band/(?P<id>[^/]+)$'

    _TEST = {
        'url': 'https://urort.p3.no/#!/Band/Gerilja',
        'md5': '5ed31a924be8a05e47812678a86e127b',
        'info_dict': {
            'id': '33124-24',
            'ext': 'mp3',
            'title': 'The Bomb',
            'thumbnail': r're:^https?://.+\.jpg',
            'uploader': 'Gerilja',
            'uploader_id': 'Gerilja',
            'upload_date': '20100323',
        },
        'params': {
            'matchtitle': '^The Bomb$',  # To test, we want just one video
        }
    }

    def _real_extract(self, url):
        playlist_id = self._match_id(url)

        fstr = urllib.parse.quote("InternalBandUrl eq '%s'" % playlist_id)
        json_url = 'http://urort.p3.no/breeze/urort/TrackDTOViews?$filter=%s&$orderby=Released%%20desc&$expand=Tags%%2CFiles' % fstr
        songs = self._download_json(json_url, playlist_id)
        entries = []
        for s in songs:
            formats = [{
                'tbr': f.get('Quality'),
                'ext': f['FileType'],
                'format_id': '%s-%s' % (f['FileType'], f.get('Quality', '')),
                'url': 'http://p3urort.blob.core.windows.net/tracks/%s' % f['FileRef'],
                'quality': 3 if f['FileType'] == 'mp3' else 2,
            } for f in s['Files']]
            e = {
                'id': '%d-%s' % (s['BandId'], s['$id']),
                'title': s['Title'],
                'uploader_id': playlist_id,
                'uploader': s.get('BandName', playlist_id),
                'thumbnail': 'http://urort.p3.no/cloud/images/%s' % s['Image'],
                'upload_date': unified_strdate(s.get('Released')),
                'formats': formats,
            }
            entries.append(e)

        return {
            '_type': 'playlist',
            'id': playlist_id,
            'title': playlist_id,
            'entries': entries,
        }
