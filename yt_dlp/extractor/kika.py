from .common import InfoExtractor
from ..utils import (
    determine_ext,
    parse_duration,
    parse_iso8601,
    traverse_obj
)


class KikaIE(InfoExtractor):
    IE_DESC = 'KiKA.de'
    _VALID_URL = r'https?://(?:www\.)?kika\.de/(?:.*)/(?P<id>[a-z-]+-?\d+)'
    _GEO_COUNTRIES = ['DE']

    _TESTS = [{
        'url': 'https://www.kika.de/beutolomaeus-und-der-wahre-weihnachtsmann/videos/eins-der-neue-weihnachtsmann-102',
        'md5': '25ceea8790417f3c6dcf1d4342f8a97a',
        'info_dict': {
            'id': 'eins-der-neue-weihnachtsmann-102',
            'ext': 'mp4',
            'title': '1. Der neue Weihnachtsmann',
            'description': 'md5:61b1e6f32882e8ca2a0ddfd135d03c6b',
            'duration': 787,
            'timestamp': 1700584500,
            'upload_date': '20231121'
        }
    }, {
        'url': 'https://www.kika.de/kaltstart/videos/video92498',
        'md5': '710ece827e5055094afeb474beacb7aa',
        'info_dict': {
            'id': 'video92498',
            'ext': 'mp4',
            'title': '7. Wo ist Leo?',
            'description': 'md5:fb48396a5b75068bcac1df74f1524920',
            'duration': 436,
            'timestamp': 1702926876,
            'upload_date': '20231218'
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        doc = self._download_json(f'https://www.kika.de/_next-api/proxy/v1/videos/{video_id}', video_id)
        video_assets = self._download_json(doc['assets']['url'], video_id)

        subtitles = {}
        ttml_resource = video_assets.get('videoSubtitle')
        if ttml_resource:
            subtitles['de'] = [{
                'url': ttml_resource,
                'ext': 'ttml',
            }]
        webvtt_resource = video_assets.get('webvttUrl')
        if webvtt_resource:
            subtitles.setdefault('de', []).append({
                'url': webvtt_resource,
                'ext': 'vtt'
            })

        return {
            'id': video_id,
            'title': doc.get('title'),
            'description': doc.get('description'),
            'timestamp': parse_iso8601(doc.get('date')),
            'duration': parse_duration(doc.get('duration')),
            'formats': list(self._extract_formats(video_assets, video_id)),
            'subtitles': subtitles
        }

    def _extract_formats(self, media_info, video_id):
        for media in media_info['assets']:
            stream_url = media.get('url')
            if not stream_url:
                continue
            ext = determine_ext(stream_url)
            if ext == 'm3u8':
                yield from self._extract_m3u8_formats(
                    stream_url, video_id, 'mp4', m3u8_id='hls', fatal=False)
            else:
                yield {
                    'url': stream_url,
                    'format_id': ext,
                    **traverse_obj(media, {
                        'width': 'frameWidth',
                        'height': 'frameHeight',
                        'filesize': 'fileSize',
                        'abr': 'bitrateAudio',
                        'vbr': 'bitrateVideo'
                    })
                }
