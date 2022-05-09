from .common import InfoExtractor
from ..utils import int_or_none


class HypemIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?hypem\.com/track/(?P<id>[0-9a-z]{5})'
    _TEST = {
        'url': 'http://hypem.com/track/1v6ga/BODYWORK+-+TAME',
        'md5': 'b9cc91b5af8995e9f0c1cee04c575828',
        'info_dict': {
            'id': '1v6ga',
            'ext': 'mp3',
            'title': 'Tame',
            'uploader': 'BODYWORK',
            'timestamp': 1371810457,
            'upload_date': '20130621',
        }
    }

    def _real_extract(self, url):
        track_id = self._match_id(url)

        response = self._download_webpage(url, track_id)

        track = self._parse_json(self._html_search_regex(
            r'(?s)<script\s+type="application/json"\s+id="displayList-data">(.+?)</script>',
            response, 'tracks'), track_id)['tracks'][0]

        track_id = track['id']
        title = track['song']

        final_url = self._download_json(
            'http://hypem.com/serve/source/%s/%s' % (track_id, track['key']),
            track_id, 'Downloading metadata', headers={
                'Content-Type': 'application/json'
            })['url']

        return {
            'id': track_id,
            'url': final_url,
            'ext': 'mp3',
            'title': title,
            'uploader': track.get('artist'),
            'duration': int_or_none(track.get('time')),
            'timestamp': int_or_none(track.get('ts')),
            'track': title,
        }
