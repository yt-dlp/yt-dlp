import json
from socket import timeout

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_iso8601,
)


class DTubeIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?d\.tube/(?:#!/)?v/(?P<uploader_id>[0-9a-z.-]+)/(?P<id>[0-9a-z]{8})'
    _TEST = {
        'url': 'https://d.tube/#!/v/broncnutz/x380jtr1',
        'md5': '9f29088fa08d699a7565ee983f56a06e',
        'info_dict': {
            'id': 'x380jtr1',
            'ext': 'mp4',
            'title': 'Lefty 3-Rings is Back Baby!! NCAA Picks',
            'description': 'md5:60be222088183be3a42f196f34235776',
            'uploader_id': 'broncnutz',
            'upload_date': '20190107',
            'timestamp': 1546854054,
        },
        'params': {
            'format': '480p',
        },
    }

    def _real_extract(self, url):
        uploader_id, video_id = self._match_valid_url(url).groups()
        result = self._download_json('https://api.steemit.com/', video_id, data=json.dumps({
            'jsonrpc': '2.0',
            'method': 'get_content',
            'params': [uploader_id, video_id],
        }).encode())['result']

        metadata = json.loads(result['json_metadata'])
        video = metadata['video']
        content = video['content']
        info = video.get('info', {})
        title = info.get('title') or result['title']

        def canonical_url(h):
            if not h:
                return None
            return 'https://video.dtube.top/ipfs/' + h

        formats = []
        for q in ('240', '480', '720', '1080', ''):
            video_url = canonical_url(content.get('video%shash' % q))
            if not video_url:
                continue
            format_id = (q + 'p') if q else 'Source'
            try:
                self.to_screen('%s: Checking %s video format URL' % (video_id, format_id))
                self._downloader._opener.open(video_url, timeout=5).close()
            except timeout:
                self.to_screen(
                    '%s: %s URL is invalid, skipping' % (video_id, format_id))
                continue
            formats.append({
                'format_id': format_id,
                'url': video_url,
                'height': int_or_none(q),
                'ext': 'mp4',
            })

        return {
            'id': video_id,
            'title': title,
            'description': content.get('description'),
            'thumbnail': canonical_url(info.get('snaphash')),
            'tags': content.get('tags') or metadata.get('tags'),
            'duration': info.get('duration'),
            'formats': formats,
            'timestamp': parse_iso8601(result.get('created')),
            'uploader_id': uploader_id,
        }
