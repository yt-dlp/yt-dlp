# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    int_or_none,
    parse_iso8601,
    try_get,
)


class TelegraafIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?telegraaf\.nl/video/(?P<id>\d+)'
    _TEST = {
        'url': 'https://www.telegraaf.nl/video/734366489/historisch-scheepswrak-slaat-na-100-jaar-los',
        'info_dict': {
            'id': 'gaMItuoSeUg2',
            'ext': 'mp4',
            'title': 'Historisch scheepswrak slaat na 100 jaar los',
            'description': 'md5:6f53b7c4f55596722ac24d6c0ec00cfb',
            'thumbnail': r're:^https?://.*\.jpg',
            'duration': 55,
            'timestamp': 1572805527,
            'upload_date': '20191103',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        article_id = self._match_id(url)

        video_id = self._download_json(
            'https://www.telegraaf.nl/graphql', article_id, query={
                'query': '''{
  article(uid: %s) {
    videos {
      videoId
    }
  }
}''' % article_id,
            })['data']['article']['videos'][0]['videoId']

        item = self._download_json(
            'https://content.tmgvideo.nl/playlist/item=%s/playlist.json' % video_id,
            video_id)['items'][0]
        title = item['title']

        formats = []
        locations = item.get('locations') or {}
        for location in locations.get('adaptive', []):
            manifest_url = location.get('src')
            if not manifest_url:
                continue
            ext = determine_ext(manifest_url)
            if ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    manifest_url, video_id, ext='mp4', m3u8_id='hls', fatal=False))
            elif ext == 'mpd':
                formats.extend(self._extract_mpd_formats(
                    manifest_url, video_id, mpd_id='dash', fatal=False))
            else:
                self.report_warning('Unknown adaptive format %s' % ext)
        for location in locations.get('progressive', []):
            src = try_get(location, lambda x: x['sources'][0]['src'])
            if not src:
                continue
            label = location.get('label')
            formats.append({
                'url': src,
                'width': int_or_none(location.get('width')),
                'height': int_or_none(location.get('height')),
                'format_id': 'http' + ('-%s' % label if label else ''),
            })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'description': item.get('description'),
            'formats': formats,
            'duration': int_or_none(item.get('duration')),
            'thumbnail': item.get('poster'),
            'timestamp': parse_iso8601(item.get('datecreated'), ' '),
        }
