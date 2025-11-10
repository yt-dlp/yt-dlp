from yt_dlp.extractor.brightcove import BrightcoveNewIE

from ..utils import ExtractorError, smuggle_url


class NetAppIE(BrightcoveNewIE):
    IE_NAME = 'netapp'
    _VALID_URL = r'https?://media\.netapp\.com/(?:(?:video-detail/(?P<id>[0-9a-f-]+))|(?P<path>[^?#]+))'

    _TESTS = [
        {
            'url': 'https://media.netapp.com/video-detail/da25fc01-82ad-5284-95bc-26920200a222/seamless-storage-for-modern-kubernetes-deployments',
            'info_dict': {
                'id': '1827763651899981973',
                'ext': 'mp4',
                'title': 'Seamless Storage for Modern Kubernetes Deployments',
            },
            'params': {'skip_download': True},
        },
    ]

    _ACCOUNT_ID = 6255154784001
    def _real_extract(self, url):
        netapp_id = self._match_id(url)
        netapp_data = self._download_json(f'https://api.media.netapp.com/client/detail/{netapp_id}', netapp_id)

        video_id = None
        for section in netapp_data.get('sections', []):
            if section.get('type') == 'Player' and section.get('video'):
                video_id = section['video']
                break

        if not video_id:
            raise ExtractorError('Netapp ID not found in API')

        netapp_url = (
            f'https://players.brightcove.net/{self._ACCOUNT_ID}/default_default/index.html?videoId={video_id}'
        )

        return self.url_result(
            smuggle_url(netapp_url, {'referrer': url}),
            'BrightcoveNew',
            video_id,
        )
