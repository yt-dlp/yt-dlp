from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    UserNotLive,
)
from ..utils import (
    base_url as get_base_url,
)


class StripchatIE(InfoExtractor):
    _VALID_URL = r'https?://(?:vr\.)?stripchat\.com/(?:cam/)?(?P<id>[^/?&#]+)'
    _TESTS = [
        {
            'url': 'https://vr.stripchat.com/cam/Heather_Ivy',
            'info_dict': {
                'id': 'Heather_Ivy',
                'ext': 'mp4',
                'title': 're:^Heather_Ivy [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
                'age_limit': 18,
                'is_live': True,
            },
            'params': {
                'skip_download': True,
            },
            'skip': 'Stream might be offline',
        },
        {
            'url': 'https://stripchat.com/Heather_Ivy',
            'info_dict': {
                'id': 'Heather_Ivy',
                'ext': 'mp4',
                'title': 're:^Heather_Ivy [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
                'age_limit': 18,
                'is_live': True,
            },
            'params': {
                'skip_download': True,
            },
            'skip': 'Stream might be offline',
        },
    ]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        is_vr = get_base_url(url) in ('https://vr.stripchat.com/cam/', 'http://vr.stripchat.com/cam/')

        # The API is the same for both VR and non-VR
        # f'https://vr.stripchat.com/api/vr/v2/models/username/{video_id}'
        api_url = f'https://stripchat.com/api/vr/v2/models/username/{video_id}'
        api_json = self._download_json(api_url, video_id)

        model = api_json.get('model', {})

        if model.get('status', {}) == 'off':
            raise UserNotLive(video_id=video_id)

        cam = api_json.get('cam') or {}
        show = cam.get('show') or {}
        details = show.get('details') or {}

        if details.get('startMode') == 'private':
            raise ExtractorError('Room is currently in a private show', expected=True)

        # You can retrieve this value from "model.id," "streamName," or "cam.streamName"
        model_id = api_json.get('streamName')

        if is_vr:
            m3u8_url = f'https://edge-hls.doppiocdn.net/hls/{model_id}_vr/master/{model_id}_vr_auto.m3u8'
        else:
            m3u8_url = f'https://edge-hls.doppiocdn.net/hls/{model_id}/master/{model_id}_auto.m3u8'

        formats = self._extract_m3u8_formats(
            m3u8_url, video_id, ext='mp4', m3u8_id='hls', fatal=False, live=True,
        )

        # You can also use previewUrlThumbBig and previewUrlThumbSmall
        preview_url = model.get('previewUrl', {})

        return {
            'id': video_id,
            'title': video_id,
            'thumbnail': preview_url,
            'is_live': True,
            'formats': formats,
            # Stripchat declares the RTA meta-tag, but in an non-standard format so _rta_search() can't be used
            'age_limit': 18,
        }
