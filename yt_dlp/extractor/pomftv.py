import random
from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    remove_start,
    UserNotLive,
    unescapeHTML,
    int_or_none,
    str_or_none,
    urljoin,
)


def _load_balance():
    subdomains = ['eu1', 'us1', 'us2', 'us3', 'asia1', 'asia2']
    random.shuffle(subdomains)
    return subdomains[0]


class PomfTVLiveIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?pomf\.tv/stream/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'https://pomf.tv/stream/MegaRadio',
        'info_dict': {
            'id': 'MegaRadio',
            'thumbnail': r're:^https?://www\.pomf\.tv/img/streamonline/MegaRadio.jpg',
            'description': 'md5:57eb6431c6d9a359124bc480c351838c',
            'title': str,
            'alt_title': str,
            'age_limit': 18,
            'live_status': 'is_live',
            'ext': 'm3u8',
            'channel_follower_count': int,
        },
        'skip': 'livestream not always online'
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        try:
            stream_data = self._download_json(
                'https://www.pomf.tv/api/streams/getinfo.php',
                channel_id, query={'data': 'streamdata', 'stream': channel_id})
        except ExtractorError as e:
            self.report_warning(f'Could not get stream info JSON: {e}', channel_id)
            stream_data = {}
        else:
            if not stream_data.get('stream_online'):
                raise UserNotLive(video_id=channel_id)

        webpage = self._download_webpage(url, channel_id)

        subdomain = _load_balance()

        return {
            'id': channel_id,
            'age_limit': 18,
            'title': (str_or_none(stream_data.get('streamtitle'))
                      or remove_start(self._og_search_title(webpage), 'Pomf.TV : ')),
            'alt_title': str_or_none(stream_data.get('streaminfo')),
            'is_live': True,
            'live_status': 'is_live',
            'thumbnail': urljoin('https://www.pomf.tv/img/streamonline/',
                                 str_or_none(stream_data.get('streambanner'))),
            'description': unescapeHTML(str_or_none(stream_data.get('streamdesc'))),
            'channel_follower_count': int_or_none(stream_data.get('followers')),
            'formats': [{'url': f'https://{subdomain}.pomf.tv/hls-live/{channel_id}_hd720/index.m3u8',
                         'format_id': 'mp4_h264_aac_hd', 'height': 720, 'width': 1280},
                        {'url': f'https://{subdomain}.pomf.tv/hls-live/{channel_id}_mq/index.m3u8',
                         'format_id': 'mp4_h264_aac_mq', 'height': 404, 'width': 720},
                        {'url': f'https://{subdomain}.pomf.tv/hls-live/{channel_id}_lq/index.m3u8',
                         'format_id': 'mp4_h264_aac_lq', 'height': 270, 'width': 480}]}
