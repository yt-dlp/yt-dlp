import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    filter_dict,
    get_element_by_id,
    int_or_none,
    join_nonempty,
    js_to_json,
    qualities,
    url_or_none,
    urljoin,
)
from ..utils.traversal import traverse_obj


class KukuluLiveIE(InfoExtractor):
    _VALID_URL = r'https?://live\.erinn\.biz/live\.php\?h(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://live.erinn.biz/live.php?h675134569',
        'md5': 'e380fa6a47fc703d91cea913ab44ec2e',
        'info_dict': {
            'id': '675134569',
            'ext': 'mp4',
            'title': 'プロセカ',
            'description': 'テストも兼ねたプロセカ配信。',
            'timestamp': 1702689148,
            'upload_date': '20231216',
            'thumbnail': r're:^https?://.*',
        },
    }, {
        'url': 'https://live.erinn.biz/live.php?h102338092',
        'md5': 'dcf5167a934b1c60333461e13a81a6e2',
        'info_dict': {
            'id': '102338092',
            'ext': 'mp4',
            'title': 'Among Usで遊びます！！',
            'description': 'VTuberになりましたねんねこ㌨ですよろしくお願いします',
            'timestamp': 1704603118,
            'upload_date': '20240107',
            'thumbnail': r're:^https?://.*',
        },
    }, {
        'url': 'https://live.erinn.biz/live.php?h878049531',
        'only_matching': True,
    }]

    def _get_quality_meta(self, video_id, desc, code, force_h264=None):
        desc += ' (force_h264)' if force_h264 else ''
        qs = self._download_webpage(
            'https://live.erinn.biz/live.player.fplayer.php', video_id,
            f'Downloading {desc} quality metadata', f'Unable to download {desc} quality metadata',
            query=filter_dict({
                'hash': video_id,
                'action': f'get{code}liveByAjax',
                'force_h264': force_h264,
            }))
        return urllib.parse.parse_qs(qs)

    def _add_quality_formats(self, formats, quality_meta):
        vcodec = traverse_obj(quality_meta, ('vcodec', 0, {str}))
        quality = traverse_obj(quality_meta, ('now_quality', 0, {str}))
        quality_priority = qualities(('low', 'h264', 'high'))(quality)
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
                'format_id': join_nonempty(quality, 'audioonly'),
                'url': quality_meta['hlsaddr_audioonly'][0],
                'ext': 'm4a',
                'vcodec': 'none',
                'quality': quality_priority,
            })

    def _real_extract(self, url):
        video_id = self._match_id(url)
        html = self._download_webpage(url, video_id)

        if '>タイムシフトが見つかりませんでした。<' in html:
            raise ExtractorError('This stream has expired', expected=True)

        title = clean_html(
            get_element_by_id('livetitle', html.replace('<SPAN', '<span').replace('SPAN>', 'span>')))
        description = self._html_search_meta('Description', html)
        thumbnail = self._html_search_meta(['og:image', 'twitter:image'], html)

        if self._search_regex(r'(var\s+timeshift\s*=\s*false)', html, 'is livestream', default=False):
            formats = []
            for (desc, code) in [('high', 'Z'), ('low', 'ForceLow')]:
                quality_meta = self._get_quality_meta(video_id, desc, code)
                self._add_quality_formats(formats, quality_meta)
                if desc == 'high' and traverse_obj(quality_meta, ('vcodec', 0)) == 'HEVC':
                    self._add_quality_formats(
                        formats, self._get_quality_meta(video_id, desc, code, force_h264='1'))

            return {
                'id': video_id,
                'title': title,
                'description': description,
                'thumbnail': thumbnail,
                'is_live': True,
                'formats': formats,
            }

        # VOD extraction
        player_html = self._download_webpage(
            'https://live.erinn.biz/live.timeshift.fplayer.php', video_id,
            'Downloading player html', 'Unable to download player html', query={'hash': video_id})

        sources = traverse_obj(self._search_json(
            r'var\s+fplayer_source\s*=', player_html, 'stream data', video_id,
            contains_pattern=r'\[(?s:.+)\]', transform_source=js_to_json), lambda _, v: v['file'])

        def entries(segments, playlist=True):
            for i, segment in enumerate(segments, 1):
                yield {
                    'id': f'{video_id}_{i}' if playlist else video_id,
                    'title': f'{title} (Part {i})' if playlist else title,
                    'description': description,
                    'timestamp': traverse_obj(segment, ('time_start', {int_or_none})),
                    'thumbnail': thumbnail,
                    'formats': [{
                        'url': urljoin('https://live.erinn.biz', segment['file']),
                        'ext': 'mp4',
                        'protocol': 'm3u8_native',
                    }],
                }

        if len(sources) == 1:
            return next(entries(sources, playlist=False))

        return self.playlist_result(entries(sources), video_id, title, description, multi_video=True)
