from .common import InfoExtractor
from ..compat import compat_str
from ..utils import (
    int_or_none,
    float_or_none,
    unified_timestamp,
    url_or_none,
)


class VzaarIE(InfoExtractor):
    _VALID_URL = r'https?://(?:(?:www|view)\.)?vzaar\.com/(?:videos/)?(?P<id>\d+)'
    _EMBED_REGEX = [r'<iframe[^>]+src=["\'](?P<url>(?:https?:)?//(?:view\.vzaar\.com)/[0-9]+)']
    _TESTS = [{
        # HTTP and HLS
        'url': 'https://vzaar.com/videos/1152805',
        'md5': 'bde5ddfeb104a6c56a93a06b04901dbf',
        'info_dict': {
            'id': '1152805',
            'ext': 'mp4',
            'title': 'sample video (public)',
        },
    }, {
        'url': 'https://view.vzaar.com/27272/player',
        'md5': '3b50012ac9bbce7f445550d54e0508f2',
        'info_dict': {
            'id': '27272',
            'ext': 'mp3',
            'title': 'MP3',
        },
    }, {
        # hlsAes = true
        'url': 'https://view.vzaar.com/11379930/player',
        'info_dict': {
            'id': '11379930',
            'ext': 'mp4',
            'title': 'Videoaula',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        # with null videoTitle
        'url': 'https://view.vzaar.com/20313539/download',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        video_data = self._download_json(
            'http://view.vzaar.com/v2/%s/video' % video_id, video_id)

        title = video_data.get('videoTitle') or video_id

        formats = []

        source_url = url_or_none(video_data.get('sourceUrl'))
        if source_url:
            f = {
                'url': source_url,
                'format_id': 'http',
                'quality': 1,
            }
            if 'audio' in source_url:
                f.update({
                    'vcodec': 'none',
                    'ext': 'mp3',
                })
            else:
                f.update({
                    'width': int_or_none(video_data.get('width')),
                    'height': int_or_none(video_data.get('height')),
                    'ext': 'mp4',
                    'fps': float_or_none(video_data.get('fps')),
                })
            formats.append(f)

        video_guid = video_data.get('guid')
        usp = video_data.get('usp')
        if video_data.get('uspEnabled') and isinstance(video_guid, compat_str) and isinstance(usp, dict):
            hls_aes = video_data.get('hlsAes')
            qs = '&'.join('%s=%s' % (k, v) for k, v in usp.items())
            url_templ = 'http://%%s.vzaar.com/v5/usp%s/%s/%s.ism%%s?' % ('aes' if hls_aes else '', video_guid, video_id)
            m3u8_formats = self._extract_m3u8_formats(
                url_templ % ('fable', '/.m3u8') + qs, video_id, 'mp4', 'm3u8_native',
                m3u8_id='hls', fatal=False)
            if hls_aes:
                for f in m3u8_formats:
                    f['_decryption_key_url'] = url_templ % ('goose', '') + qs
            formats.extend(m3u8_formats)

        return {
            'id': video_id,
            'title': title,
            'thumbnail': self._proto_relative_url(video_data.get('poster')),
            'duration': float_or_none(video_data.get('videoDuration')),
            'timestamp': unified_timestamp(video_data.get('ts')),
            'formats': formats,
        }
