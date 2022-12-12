from .common import InfoExtractor
from ..utils import (
    determine_ext,
    parse_duration,
    parse_iso8601,
    traverse_obj
)


class KikaIE(InfoExtractor):
    IE_DESC = 'KiKA.de'
    _VALID_URL = r'https?://(?:www\.)?kika\.de/(?:.*)/[a-z-]+-?(?P<id>\d+)'
    _GEO_COUNTRIES = ['DE']

    _TESTS = [{
        'url': 'https://www.kika.de/beutolomaeus-und-der-wahre-weihnachtsmann/videos/video59362',
        'md5': 'b163ac8872f0cea1eb075cae3c275935',
        'info_dict': {
            'id': '59362',
            'ext': 'mp4',
            'title': '1. Der neue Weihnachtsmann',
            'description': 'md5:61b1e6f32882e8ca2a0ddfd135d03c6b',
            'duration': 787,
            'uploader': 'KIKA',
            'timestamp': 1669914628,
            'upload_date': '20221201'
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        doc = self._download_json("https://www.kika.de/_next-api/proxy/v1/videos/video%s" % (video_id), video_id)
        video_assets = self._download_json(doc.get('assets').get('url'), video_id)
        formats = list(self._extract_formats(video_assets, video_id))

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
            'formats': formats,
            'subtitles': subtitles,
            'uploader': 'KIKA'
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
