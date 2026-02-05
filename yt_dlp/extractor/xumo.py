from .common import InfoExtractor
from ..utils import (
    clean_html,
    determine_ext,
    int_or_none,
    mimetype2ext,
    unified_timestamp,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class XumoIE(InfoExtractor):
    _GEO_COUNTRIES = ['US']
    _VALID_URL = r'https?://play\.xumo\.com/(?:free-movies|networks/xumo-free-movies)/[\w-]+/(?P<id>[0-9A-Z]+)(/\d+)?'
    _TESTS = [{
        'url': 'https://play.xumo.com/free-movies/a-circus-tale-and-a-love-song/XM041I5U497VD3',
        'info_dict': {
            'id': 'XM041I5U497VD3',
            'ext': 'mp4',
            'title': 'A Circus Tale & A Love Song',
            'description': 'md5:3c3c079d10a0369d78e10ac96b4e68c9',
            'duration': 6887,
            'genres': 'count:2',
            'tags': 'count:7',
            'release_year': 2016,
            'thumbnail': r're:https?://.+\.jpg',
            'timestamp': 1706763600,
            'upload_date': '20240201',
        },
    }, {
        'url': 'https://play.xumo.com/networks/xumo-free-movies/99991299/XM08RIB78GYPVR/478646',
        'info_dict': {
            'id': 'XM08RIB78GYPVR',
            'ext': 'mp4',
            'title': 'Lone Star Shark',
            'description': 'md5:8062c5f5265882d31232bbaa8c8065a0',
            'duration': 3915,
            'genres': 'count:2',
            'tags': 'count:4',
            'release_year': 2025,
            'thumbnail': r're:https?://.+\.jpg',
            'timestamp': 1738386000,
            'upload_date': '20250201',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        query_params = [
            'connectorId', 'title', 'providers', 'descriptions',
            'runtime', 'originalReleaseYear', 'cuePoints', 'ratings',
            'hasCaptions', 'availableSince', 'genres', 'season:all',
            'episodes.episodeTitle', 'episodes.runtime', 'episodes.descriptions',
            'episodes.hasCaptions', 'episodes.ratings', 'keywords',
        ]
        asset = self._download_json(
            f'https://valencia-app-mds.xumo.com/v2/assets/asset/{video_id}.json',
            video_id, query={'f': query_params})

        formats, subtitles = [], {}
        for source in traverse_obj(asset, (
            'providers', ..., 'sources', lambda _, v: url_or_none(v['uri']),
        )):
            ext = mimetype2ext(source['produces'])
            manifest_url = source['uri']
            if ext == 'm3u8':
                fmts, subs = self._extract_m3u8_formats_and_subtitles(
                    manifest_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
            elif ext == 'mpd':
                fmts, subs = self._extract_mpd_formats_and_subtitles(
                    manifest_url, video_id, mpd_id='dash', fatal=False)
            else:
                self.report_warning(f'Unsupported stream type: {ext}')
                continue
            if source.get('drm'):
                for f in fmts:
                    f['has_drm'] = True

            formats.extend(fmts)
            subtitles = self._merge_subtitles(subtitles, subs)
        self._remove_duplicate_formats(formats)

        for caption in traverse_obj(asset, (
            'providers', ..., 'captions', lambda _, v: url_or_none(v['url']),
        )):
            lang = traverse_obj(caption, ('lang', {clean_html}, filter)) or 'und'
            caption_url = caption['url']
            subtitles.setdefault(lang, []).append({
                'ext': determine_ext(caption_url),
                'url': caption_url,
            })

        return {
            'id': video_id,
            'formats': formats,
            'subtitles': subtitles,
            'thumbnail': f'https://image.xumo.com/v1/assets/asset/{video_id}/1024x576.jpg',
            **traverse_obj(asset, {
                'title': ('title', {clean_html}),
                'description': ('descriptions', ('large', 'medium', 'small', 'tiny'), {clean_html}, filter, any),
                'duration': ('runtime', {int_or_none}),
                'genres': ('genres', ..., 'value', {clean_html}, filter),
                'release_year': ('originalReleaseYear', {int_or_none}),
                'tags': ('keywords', ..., {clean_html}, filter),
                'timestamp': ('availableSince', {unified_timestamp}),
            }),
        }
