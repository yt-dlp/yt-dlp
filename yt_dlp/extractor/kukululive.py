from .common import InfoExtractor
from ..utils import ExtractorError
from ..compat import compat_parse_qs


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
            errnote=f'Unable to download {description} quality metadata'
        )
        return compat_parse_qs(qs)

    def _add_quality_formats(self, formats, quality_meta):
        vcodec = quality_meta.get('vcodec')[0]
        quality = quality_meta.get('now_quality')[0]
        quality_priority = {
            'high': 3,
            'h264': 2,
            'low': 1,
        }
        formats.extend([
            {
                'format_id': quality,
                'url': quality_meta.get('hlsaddr')[0],
                'ext': 'mp4',
                'vcodec': vcodec,
                'quality': quality_priority[quality],
            },
            {
                'format_id': f'{quality}-rtmp',
                'url': quality_meta.get('streamaddr')[0],
                'ext': 'mp4',
                'vcodec': vcodec,
                'quality': quality_priority[quality] - 5,
            },
            {
                'format_id': f'{quality}-audioonly',
                'url': quality_meta.get('hlsaddr_audioonly')[0],
                'ext': 'aac',
                'vcodec': 'none',
                'quality': quality_priority[quality] - 10,
            },
        ])

    def _real_extract(self, url):
        video_id = self._match_id(url)
        html = self._download_webpage(
            url, video_id,
            note='Downloading html',
            errnote='Unable to download html'
        )

        # https://regex101.com/r/SNbBwa/1
        title = self._search_regex(r'<SPAN id=\"livetitle\">([^<]+)</SPAN>', html, 'title', fatal=False)
        description = self._html_search_meta('Description', html)
        thumbnail_url = self._html_search_meta(['og:image', 'twitter:image'], html)
        thumbnails = [{'url': thumbnail_url}]

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
                'id': str(video_id),
                'title': title,
                'description': description,
                'thumbnails': thumbnails,
                'is_live': True,
                'formats': formats,
            }

        if is_vod:
            player_html = self._download_webpage(
                'https://live.erinn.biz/live.timeshift.fplayer.php', video_id,
                query={'hash': video_id},
                note='Downloading player html',
                errnote='Unable to download player html'
            )

            # https://regex101.com/r/3AXpSA/3
            sources = self._search_regex(r'var fplayer_source = ([^;]+)', player_html, 'sources')
            sources_json = self._parse_json(sources.replace('.mp4",', '.mp4"'), video_id)

            formats = []
            for source in sources_json:
                path = source.get('file')
                formats.append({
                    'url': f'https://live.erinn.biz{path}',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                })

            return {
                'id': str(video_id),
                'title': title,
                'description': description,
                'timestamp': sources_json[0].get('time_start'),
                'thumbnails': thumbnails,
                'formats': formats,
            }

        raise ExtractorError('Cannot parse live stream or VOD', expected=True)
