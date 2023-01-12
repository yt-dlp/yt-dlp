from .common import InfoExtractor
from .uplynk import UplynkPreplayIE
from ..utils import HEADRequest, float_or_none, make_archive_id, smuggle_url


class FoxSportsIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?foxsports\.com/watch/(?P<id>[\w-]+)'
    _TESTS = [{
        'url': 'https://www.foxsports.com/watch/play-612168c6700004b',
        'info_dict': {
            'id': 'b72f5bd8658140baa5791bb676433733',
            'ext': 'mp4',
            'display_id': 'play-612168c6700004b',
            'title': 'md5:e0c4ecac3a1f25295b4fae22fb5c126a',
            'description': 'md5:371bc43609708ae2b9e1a939229762af',
            'uploader_id': '06b4a36349624051a9ba52ac3a91d268',
            'upload_date': '20221205',
            'timestamp': 1670262586,
            'duration': 31.7317,
            'thumbnail': r're:^https?://.*\.jpg$',
            'extra_param_to_segment_url': str,
        },
        'params': {
            'skip_download': 'm3u8',
        },
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        json_ld = self._search_json_ld(webpage, video_id, expected_type='VideoObject', default={})
        data = self._download_json(
            f'https://api3.fox.com/v2.0/vodplayer/sportsclip/{video_id}',
            video_id, note='Downloading API JSON', headers={
                'x-api-key': 'cf289e299efdfa39fb6316f259d1de93',
            })
        preplay_url = self._request_webpage(
            HEADRequest(data['url']), video_id, 'Fetching preplay URL').geturl()

        return {
            '_type': 'url_transparent',
            'ie_key': UplynkPreplayIE.ie_key(),
            'url': smuggle_url(preplay_url, {'Origin': 'https://www.foxsports.com'}),
            'display_id': video_id,
            'title': data.get('name') or json_ld.get('title'),
            'description': data.get('description') or json_ld.get('description'),
            'duration': float_or_none(data.get('durationInSeconds')),
            'timestamp': json_ld.get('timestamp'),
            'thumbnails': json_ld.get('thumbnails'),
            '_old_archive_ids': [make_archive_id(self, video_id)],
        }
