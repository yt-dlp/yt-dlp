from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    get_element_by_id,
    urljoin,
    js_to_json,
    traverse_obj,
    int_or_none,
    url_or_none,
)
from urllib.parse import parse_qs


class KukuluLiveIE(InfoExtractor):
    _VALID_URL = r'https?://live\.erinn\.biz/live\.php\?h(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://live.erinn.biz/live.php?h675134569',
        'only_matching': True,
    }]

    def _get_quality_meta(self, video_id, desc, code, force_h264=''):
        description = desc if force_h264 == '' else f'{desc} (force_h264)'
        qs = self._download_webpage(
            'https://live.erinn.biz/live.player.fplayer.php', video_id,
            query={
                'hash': video_id,
                'action': f'get{code}liveByAjax',
                'force_h264': force_h264,
            },
            note=f'Downloading {description} quality metadata',
            errnote=f'Unable to download {description} quality metadata')
        return parse_qs(qs)

    def _add_quality_formats(self, formats, quality_meta):
        vcodec = traverse_obj(quality_meta, ('vcodec', 0))
        quality = traverse_obj(quality_meta, ('now_quality', 0))
        quality_priority = {
            'high': 3,
            'h264': 2,
            'low': 1,
        }.get(quality, 0)
        if traverse_obj(quality_meta, ('hlsaddr', 0, {url_or_none})):
            formats.append({
                'format_id': quality,
                'url': quality_meta['hlsaddr'][0],
                'ext': 'mp4',
                'vcodec': vcodec,
                'quality': quality_priority,
            })
        if traverse_obj(quality_meta, ('hlsaddr_audioonly', 0, {url_or_none})):
            formats.append({
                'format_id': f'{quality}-audioonly',
                'url': quality_meta['hlsaddr_audioonly'][0],
                'ext': 'm4a',
                'vcodec': 'none',
                'quality': quality_priority,
            })

    def _real_extract(self, url):
        video_id = self._match_id(url)
        html = self._download_webpage(url, video_id)

        title = clean_html(get_element_by_id('livetitle', html.replace('<SPAN', '<span').replace('SPAN>', 'span>')))
        description = self._html_search_meta('Description', html)
        thumbnail = self._html_search_meta(['og:image', 'twitter:image'], html)

        is_live_stream = 'var timeshift = false;' in html
        is_vod = 'var timeshift = true;' in html

        if is_live_stream:
            qualities = [
                ('high', 'Z'),
                ('low', 'ForceLow'),
            ]
            formats = []
            for (desc, code) in qualities:
                quality_meta = self._get_quality_meta(video_id, desc, code)
                self._add_quality_formats(formats, quality_meta)
                if desc == 'high' and quality_meta.get('vcodec')[0] == 'HEVC':
                    h264_meta = self._get_quality_meta(video_id, desc, code, force_h264='1')
                    self._add_quality_formats(formats, h264_meta)

            return {
                'id': video_id,
                'title': title,
                'description': description,
                'thumbnail': thumbnail,
                'is_live': True,
                'formats': formats,
            }

        if is_vod:
            player_html = self._download_webpage(
                'https://live.erinn.biz/live.timeshift.fplayer.php', video_id,
                query={'hash': video_id},
                note='Downloading player html',
                errnote='Unable to download player html')

            sources_json = self._search_json(
                r'var\s+fplayer_source\s*=', player_html, 'stream data', video_id,
                contains_pattern=r'\[(?s:.+)\]', transform_source=js_to_json)

            def _parse_segment(segment, id, title):
                path = segment.get('file')
                if not path:
                    return None
                formats = [{
                    'url': urljoin('https://live.erinn.biz', path),
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                }]
                return {
                    'id': id,
                    'title': title,
                    'description': description,
                    'timestamp': traverse_obj(segment, ('time_start', {int_or_none})),
                    'thumbnail': thumbnail,
                    'formats': formats,
                }

            is_playlist = len(sources_json) > 1
            if is_playlist:
                entries = []
                for i, segment in enumerate(sources_json):
                    entry = _parse_segment(segment, f'{video_id}_{i}', f'{title} (Part {i + 1})')
                    if not entry:
                        continue
                    entries.append(entry)
                return self.playlist_result(entries, video_id, title, description, multi_video=True)
            else:
                return _parse_segment(sources_json[0], video_id, title)

        raise ExtractorError('Could not detect media type')
