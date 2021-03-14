# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..compat import (
    compat_parse_qs,
    compat_urllib_parse_urlparse,
)
from ..utils import (
    clean_html,
    float_or_none,
    int_or_none,
    parse_iso8601,
    strip_or_none,
    try_get,
)


class SportDeutschlandIE(InfoExtractor):
    _VALID_URL = r'https?://sportdeutschland\.tv/(?P<id>(?:[^/]+/)?[^?#/&]+)'
    _TESTS = [{
        'url': 'https://sportdeutschland.tv/badminton/re-live-deutsche-meisterschaften-2020-halbfinals?playlistId=0',
        'info_dict': {
            'id': '5318cac0275701382770543d7edaf0a0',
            'ext': 'mp4',
            'title': 'Re-live: Deutsche Meisterschaften 2020 - Halbfinals - Teil 1',
            'duration': 16106.36,
        },
        'params': {
            'noplaylist': True,
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'https://sportdeutschland.tv/badminton/re-live-deutsche-meisterschaften-2020-halbfinals?playlistId=0',
        'info_dict': {
            'id': 'c6e2fdd01f63013854c47054d2ab776f',
            'title': 'Re-live: Deutsche Meisterschaften 2020 - Halbfinals',
            'description': 'md5:5263ff4c31c04bb780c9f91130b48530',
            'duration': 31397,
        },
        'playlist_count': 2,
    }, {
        'url': 'https://sportdeutschland.tv/freeride-world-tour-2021-fieberbrunn-oesterreich',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        data = self._download_json(
            'https://backend.sportdeutschland.tv/api/permalinks/' + display_id,
            display_id, query={'access_token': 'true'})
        asset = data['asset']
        title = (asset.get('title') or asset['label']).strip()
        asset_id = asset.get('id') or asset.get('uuid')
        info = {
            'id': asset_id,
            'title': title,
            'description': clean_html(asset.get('body') or asset.get('description')) or asset.get('teaser'),
            'duration': int_or_none(asset.get('seconds')),
        }
        videos = asset.get('videos') or []
        if len(videos) > 1:
            playlist_id = compat_parse_qs(compat_urllib_parse_urlparse(url).query).get('playlistId', [None])[0]
            if playlist_id:
                if self._downloader.params.get('noplaylist'):
                    videos = [videos[int(playlist_id)]]
                    self.to_screen('Downloading just a single video because of --no-playlist')
                else:
                    self.to_screen('Downloading playlist %s - add --no-playlist to just download video' % asset_id)

            def entries():
                for i, video in enumerate(videos, 1):
                    video_id = video.get('uuid')
                    video_url = video.get('url')
                    if not (video_id and video_url):
                        continue
                    formats = self._extract_m3u8_formats(
                        video_url.replace('.smil', '.m3u8'), video_id, 'mp4', fatal=False)
                    if not formats:
                        continue
                    yield {
                        'id': video_id,
                        'formats': formats,
                        'title': title + ' - ' + (video.get('label') or 'Teil %d' % i),
                        'duration': float_or_none(video.get('duration')),
                    }
            info.update({
                '_type': 'multi_video',
                'entries': entries(),
            })
        else:
            formats = self._extract_m3u8_formats(
                videos[0]['url'].replace('.smil', '.m3u8'), asset_id, 'mp4')
            section_title = strip_or_none(try_get(data, lambda x: x['section']['title']))
            info.update({
                'formats': formats,
                'display_id': asset.get('permalink'),
                'thumbnail': try_get(asset, lambda x: x['images'][0]),
                'categories': [section_title] if section_title else None,
                'view_count': int_or_none(asset.get('views')),
                'is_live': asset.get('is_live') is True,
                'timestamp': parse_iso8601(asset.get('date') or asset.get('published_at')),
            })
        return info
