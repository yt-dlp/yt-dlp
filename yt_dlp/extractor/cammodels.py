from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    url_or_none,
)


class CamModelsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?cammodels\.com/cam/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://www.cammodels.com/cam/AutumnKnight/',
        'only_matching': True,
        'age_limit': 18
    }]

    def _real_extract(self, url):
        user_id = self._match_id(url)

        webpage = self._download_webpage(
            url, user_id, headers=self.geo_verification_headers())

        manifest_root = self._html_search_regex(
            r'manifestUrlRoot=([^&\']+)', webpage, 'manifest', default=None)

        if not manifest_root:
            ERRORS = (
                ("I'm offline, but let's stay connected", 'This user is currently offline'),
                ('in a private show', 'This user is in a private show'),
                ('is currently performing LIVE', 'This model is currently performing live'),
            )
            for pattern, message in ERRORS:
                if pattern in webpage:
                    error = message
                    expected = True
                    break
            else:
                error = 'Unable to find manifest URL root'
                expected = False
            raise ExtractorError(error, expected=expected)

        manifest = self._download_json(
            '%s%s.json' % (manifest_root, user_id), user_id)

        formats = []
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
                    format_id_list.append('%dp' % height)
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
                    continue
                formats.append(f)

        return {
            'id': user_id,
            'title': user_id,
            'is_live': True,
            'formats': formats,
            'age_limit': 18
        }
