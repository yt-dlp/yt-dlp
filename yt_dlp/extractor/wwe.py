import re

from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    try_get,
    unescapeHTML,
    url_or_none,
    urljoin,
)


class WWEBaseIE(InfoExtractor):
    _SUBTITLE_LANGS = {
        'English': 'en',
        'Deutsch': 'de',
    }

    def _extract_entry(self, data, url, video_id=None):
        video_id = compat_str(video_id or data['nid'])
        title = data['title']

        formats = self._extract_m3u8_formats(
            data['file'], video_id, 'mp4', entry_protocol='m3u8_native',
            m3u8_id='hls')

        description = data.get('description')
        thumbnail = urljoin(url, data.get('image'))
        series = data.get('show_name')
        episode = data.get('episode_name')

        subtitles = {}
        tracks = data.get('tracks')
        if isinstance(tracks, list):
            for track in tracks:
                if not isinstance(track, dict):
                    continue
                if track.get('kind') != 'captions':
                    continue
                track_file = url_or_none(track.get('file'))
                if not track_file:
                    continue
                label = track.get('label')
                lang = self._SUBTITLE_LANGS.get(label, label) or 'en'
                subtitles.setdefault(lang, []).append({
                    'url': track_file,
                })

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'series': series,
            'episode': episode,
            'formats': formats,
            'subtitles': subtitles,
        }


class WWEIE(WWEBaseIE):
    _VALID_URL = r'https?://(?:[^/]+\.)?wwe\.com/(?:[^/]+/)*videos/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.wwe.com/videos/daniel-bryan-vs-andrade-cien-almas-smackdown-live-sept-4-2018',
        'md5': '92811c6a14bfc206f7a6a9c5d9140184',
        'info_dict': {
            'id': '40048199',
            'ext': 'mp4',
            'title': 'Daniel Bryan vs. Andrade "Cien" Almas: SmackDown LIVE, Sept. 4, 2018',
            'description': 'md5:2d7424dbc6755c61a0e649d2a8677f67',
            'thumbnail': r're:^https?://.*\.jpg$',
        }
    }, {
        'url': 'https://de.wwe.com/videos/gran-metalik-vs-tony-nese-wwe-205-live-sept-4-2018',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        landing = self._parse_json(
            self._html_search_regex(
                r'(?s)Drupal\.settings\s*,\s*({.+?})\s*\)\s*;',
                webpage, 'drupal settings'),
            display_id)['WWEVideoLanding']

        data = landing['initialVideo']['playlist'][0]
        video_id = landing.get('initialVideoId')

        info = self._extract_entry(data, url, video_id)
        info['display_id'] = display_id
        return info


class WWEPlaylistIE(WWEBaseIE):
    _VALID_URL = r'https?://(?:[^/]+\.)?wwe\.com/(?:[^/]+/)*(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.wwe.com/shows/raw/2018-11-12',
        'info_dict': {
            'id': '2018-11-12',
        },
        'playlist_mincount': 11,
    }, {
        'url': 'http://www.wwe.com/article/walk-the-prank-wwe-edition',
        'only_matching': True,
    }, {
        'url': 'https://www.wwe.com/shows/wwenxt/article/matt-riddle-interview',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if WWEIE.suitable(url) else super(WWEPlaylistIE, cls).suitable(url)

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        entries = []
        for mobj in re.finditer(
                r'data-video\s*=\s*(["\'])(?P<data>{.+?})\1', webpage):
            video = self._parse_json(
                mobj.group('data'), display_id, transform_source=unescapeHTML,
                fatal=False)
            if not video:
                continue
            data = try_get(video, lambda x: x['playlist'][0], dict)
            if not data:
                continue
            try:
                entry = self._extract_entry(data, url)
            except Exception:
                continue
            entry['extractor_key'] = WWEIE.ie_key()
            entries.append(entry)

        return self.playlist_result(entries, display_id)
