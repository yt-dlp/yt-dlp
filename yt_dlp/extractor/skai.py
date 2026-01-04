from .common import InfoExtractor
from ..utils import (
    clean_html,
    js_to_json,
    unified_strdate,
)


class SkaiIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?skai(?:tv)?\.gr/(?:tv/)?episode/(?P<id>[^/?#]+(?:/[^/?#]+)*)'
    _TESTS = [{
        'url': 'https://www.skai.gr/tv/episode/seires/tote-vs-tora/2025-12-17-21',
        'info_dict': {
            'id': '341062',
            'display_id': 'seires/tote-vs-tora/2025-12-17-21',
            'ext': 'mp4',
            'title': 'Τότε και Τώρα | Ρεβεγιόν',
            'description': 'md5:6179421f18544d662363579899387431',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20251217',
        },
        'params': {
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        data = self._search_json(
            r'var\s+data\s*=\s*(?={"episode")', webpage, 'player data', display_id,
            transform_source=js_to_json)

        episodes = data.get('episode') or []
        if not episodes:
            raise self.raise_login_required('This video is potentially for subscribers only or not found')

        # Usually there's only one episode in the 'episode' list for the main player
        episode = episodes[0]
        video_id = episode.get('id') or display_id
        title = episode.get('title') or self._og_search_title(webpage)
        description = clean_html(episode.get('descr')) or self._og_search_description(webpage)
        thumbnail = episode.get('img') or self._og_search_thumbnail(webpage)

        # media_type_id logic from player.js
        # 2: VOD (mp4), 4: YouTube
        media_type_id = episode.get('media_type_id')
        media_item_file = episode.get('media_item_file')

        if media_type_id == '4':
            return self.url_result(f'https://www.youtube.com/watch?v={media_item_file}', 'Youtube')

        if not media_item_file:
            raise self.raise_login_required('No video file found')

        if media_item_file.endswith('.mp4'):
            # Construct m3u8 URL
            if media_item_file.startswith('/'):
                pre = 'https://videostream.skai.gr/skaivod/_definst_/mp4:skai'
            else:
                pre = 'https://videostream.skai.gr/skaivod/_definst_/mp4:skai/'
            m3u8_url = pre + media_item_file + '/chunklist.m3u8'
            formats = self._extract_m3u8_formats(m3u8_url, video_id, 'mp4', m3u8_id='hls')
        else:
            # Fallback for other files if any
            if media_item_file.startswith('/'):
                video_url = 'https://download.skai.gr' + media_item_file
            else:
                video_url = 'https://download.skai.gr/' + media_item_file
            formats = [{'url': video_url}]

        # Try to get upload date from JSON-LD or 'start' field
        json_ld = self._search_json_ld(webpage, video_id, default={})
        upload_date = unified_strdate(json_ld.get('uploadDate') or episode.get('start'))

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'formats': formats,
            'upload_date': upload_date,
        }
