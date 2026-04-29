from .common import InfoExtractor
from ..utils import int_or_none, url_or_none


class CamModelsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?cammodels\.com/cam/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.cammodels.com/cam/AutumnKnight/',
        'only_matching': True,
        'age_limit': 18,
    }]

    def _real_extract(self, url):
        user_id = self._match_id(url)

        manifest = self._download_json(
            f'https://manifest-server.naiadsystems.com/live/s:{user_id}.json', user_id)

        formats = []
        thumbnails = []
        for format_id, format_dict in manifest['formats'].items():
            if not isinstance(format_dict, dict):
                continue
            encodings = format_dict.get('encodings')
            if not isinstance(encodings, list):
                continue
            vcodec = format_dict.get('videoCodec')
            acodec = format_dict.get('audioCodec')
            for media in encodings:
                if not isinstance(media, dict):
                    continue
                media_url = url_or_none(media.get('location'))
                if not media_url:
                    continue

                format_id_list = [format_id]
                height = int_or_none(media.get('videoHeight'))
                if height is not None:
                    format_id_list.append(f'{height}p')
                f = {
                    'url': media_url,
                    'format_id': '-'.join(format_id_list),
                    'width': int_or_none(media.get('videoWidth')),
                    'height': height,
                    'vbr': int_or_none(media.get('videoKbps')),
                    'abr': int_or_none(media.get('audioKbps')),
                    'fps': int_or_none(media.get('fps')),
                    'vcodec': vcodec,
                    'acodec': acodec,
                }
                if 'rtmp' in format_id:
                    f['ext'] = 'flv'
                elif 'hls' in format_id:
                    f.update({
                        'ext': 'mp4',
                        # hls skips fragments, preferring rtmp
                        'quality': -10,
                    })
                else:
                    if format_id == 'jpeg':
                        thumbnails.append({
                            'url': f['url'],
                            'width': f['width'],
                            'height': f['height'],
                            'format_id': f['format_id'],
                        })
                    continue
                formats.append(f)

        return {
            'id': user_id,
            'title': user_id,
            'thumbnails': thumbnails,
            'is_live': True,
            'formats': formats,
            'age_limit': 18,
        }
