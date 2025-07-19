import urllib.parse

from .common import InfoExtractor


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
        is_vr = urllib.parse.urlparse(url).hostname == 'vr.stripchat.com'

        # The API is the same for both VR and non-VR
        # f'https://vr.stripchat.com/api/vr/v2/models/username/{video_id}'
        api_url = f'https://stripchat.com/api/vr/v2/models/username/{video_id}'
        api_json = self._download_json(api_url, video_id)

        # You can retrieve this value from "model.id," "streamName," or "cam.streamName"
        model_id = api_json.get('streamName')

        # Contains 'eu23', for example, with server '20' as the fallback
        host_str = api_json.get('model', {}).get('broadcastServer', '')
        host = ''.join([c for c in host_str if c.isdigit()]) or 20

        if is_vr:
            base_url = f'https://media-hls.doppiocdn.net/b-hls-{host}/{model_id}_vr/{model_id}_vr'
            # e.g. ['2160p60', '1440p60']
            video_presets = api_json.get('broadcastSettings', {}).get('presets', {}).get('vr', {})
        else:
            base_url = f'https://media-hls.doppiocdn.net/b-hls-{host}/{model_id}/{model_id}'
            # e.g. ['960p', '480p', '240p', '160p', '160p_blurred']
            video_presets = api_json.get('broadcastSettings', {}).get('presets', {}).get('default', {})

        formats = []

        # This does not work because the m3u8 url is incorrect
        # formats = self._extract_m3u8_formats(
        #        f'{base_url}_auto.m3u8',
        #        video_id, ext='mp4', m3u8_id='hls', fatal=False, live=True
        # )

        # The resolution should be omitted for best quality (source) that is often much higher than 2160p60 on VR
        formats.append({
            'url': f'{base_url}.m3u8',
            'ext': 'mp4',
            'protocol': 'm3u8_native',
            'format_id': 'source',
            'quality': 10,
            'is_live': True,
        })

        # Add all other available presets
        for index, resolution in enumerate(video_presets):
            if isinstance(resolution, str):
                formats.append({
                    'url': f'{base_url}_{resolution}.m3u8',
                    'ext': 'mp4',
                    'protocol': 'm3u8_native',
                    'format_id': f'hls_{resolution}',
                    # The qualities are already sorted by entry point
                    'quality': 9 - index,
                    'is_live': True,
                })

        # You can also use previewUrlThumbBig and previewUrlThumbSmall
        preview_url = api_json.get('model', {}).get('previewUrl', {})

        return {
            'id': video_id,
            'title': video_id,
            'thumbnail': preview_url,
            'is_live': True,
            'formats': formats,
            # Stripchat declares the RTA meta-tag, but in an non-standard format so _rta_search() can't be used
            'age_limit': 18,
        }
