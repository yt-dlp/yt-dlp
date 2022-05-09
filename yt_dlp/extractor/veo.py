from .common import InfoExtractor

from ..utils import (
    int_or_none,
    mimetype2ext,
    str_or_none,
    unified_timestamp,
    url_or_none,
)


class VeoIE(InfoExtractor):
    _VALID_URL = r'https?://app\.veo\.co/matches/(?P<id>[0-9A-Za-z-_]+)'

    _TESTS = [{
        'url': 'https://app.veo.co/matches/20201027-last-period/',
        'info_dict': {
            'id': '20201027-last-period',
            'ext': 'mp4',
            'title': 'Akidemy u11s v Bradford Boys u11s (Game 3)',
            'thumbnail': 're:https://c.veocdn.com/.+/thumbnail.jpg',
            'upload_date': '20201028',
            'timestamp': 1603847208,
            'duration': 1916,
            'view_count': int,
        }
    }, {
        'url': 'https://app.veo.co/matches/20220313-2022-03-13_u15m-plsjq-vs-csl/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        metadata = self._download_json(
            'https://app.veo.co/api/app/matches/%s' % video_id, video_id)

        video_data = self._download_json(
            'https://app.veo.co/api/app/matches/%s/videos' % video_id, video_id, 'Downloading video data')

        formats = []
        for fmt in video_data:
            mimetype = str_or_none(fmt.get('mime_type'))
            format_url = url_or_none(fmt.get('url'))
            # skip configuration file for panoramic video
            if not format_url or mimetype == 'video/mp2t':
                continue

            height = int_or_none(fmt.get('height'))
            render_type = str_or_none(fmt.get('render_type'))
            format_id = f'{render_type}-{height}p' if render_type and height else None

            # Veo returns panoramic video information even if panoramic video is not available.
            # e.g. https://app.veo.co/matches/20201027-last-period/
            if render_type == 'panorama':
                if not self._is_valid_url(format_url, video_id, format_id):
                    continue

            formats.append({
                'url': format_url,
                'format_id': format_id,
                'ext': mimetype2ext(mimetype),
                'width': int_or_none(fmt.get('width')),
                'height': height,
                'vbr': int_or_none(fmt.get('bit_rate'), scale=1000),
            })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': str_or_none(metadata.get('title')),
            'formats': formats,
            'thumbnail': url_or_none(metadata.get('thumbnail')),
            'timestamp': unified_timestamp(metadata.get('created')),
            'view_count': int_or_none(metadata.get('view_count')),
            'duration': int_or_none(metadata.get('duration')),
        }
