from .common import InfoExtractor
from ..utils import try_get


class ThetaStreamIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?theta\.tv/(?!video/)(?P<id>[a-z0-9-]+)'
    _TESTS = [{
        'url': 'https://www.theta.tv/davirus',
        'skip': 'The live may have ended',
        'info_dict': {
            'id': 'DaVirus',
            'ext': 'mp4',
            'title': 'I choose you - My Community is King -👀 - YO HABLO ESPANOL - CODE DAVIRUS',
            'thumbnail': r're:https://live-thumbnails-prod-theta-tv\.imgix\.net/thumbnail/.+\.jpg',
        }
    }, {
        'url': 'https://www.theta.tv/mst3k',
        'note': 'This channel is live 24/7',
        'info_dict': {
            'id': 'MST3K',
            'ext': 'mp4',
            'title': 'Mystery Science Theatre 3000 24/7 Powered by the THETA Network.',
            'thumbnail': r're:https://user-prod-theta-tv\.imgix\.net/.+\.jpg',
        }
    }, {
        'url': 'https://www.theta.tv/contv-anime',
        'info_dict': {
            'id': 'ConTVAnime',
            'ext': 'mp4',
            'title': 'CONTV ANIME 24/7. Powered by THETA Network.',
            'thumbnail': r're:https://user-prod-theta-tv\.imgix\.net/.+\.jpg',
        }
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        info = self._download_json(f'https://api.theta.tv/v1/channel?alias={channel_id}', channel_id)['body']

        m3u8_playlist = next(
            data['url'] for data in info['live_stream']['video_urls']
            if data.get('type') != 'embed' and data.get('resolution') in ('master', 'source'))

        formats = self._extract_m3u8_formats(m3u8_playlist, channel_id, 'mp4', m3u8_id='hls', live=True)

        channel = try_get(info, lambda x: x['user']['username'])  # using this field instead of channel_id due to capitalization

        return {
            'id': channel,
            'title': try_get(info, lambda x: x['live_stream']['title']),
            'channel': channel,
            'view_count': try_get(info, lambda x: x['live_stream']['view_count']),
            'is_live': True,
            'formats': formats,
            'thumbnail': try_get(info, lambda x: x['live_stream']['thumbnail_url']),
        }


class ThetaVideoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?theta\.tv/video/(?P<id>vid[a-z0-9]+)'
    _TEST = {
        'url': 'https://www.theta.tv/video/vidiq6aaet3kzf799p0',
        'md5': '633d8c29eb276bb38a111dbd591c677f',
        'info_dict': {
            'id': 'vidiq6aaet3kzf799p0',
            'ext': 'mp4',
            'title': 'Theta EdgeCast Tutorial',
            'uploader': 'Pixiekittie',
            'description': 'md5:e316253f5bdced8b5a46bb50ae60a09f',
            'thumbnail': r're:https://user-prod-theta-tv\.imgix\.net/.+/vod_thumb/.+.jpg',
        }
    }

    def _real_extract(self, url):
        video_id = self._match_id(url)
        info = self._download_json(f'https://api.theta.tv/v1/video/{video_id}/raw', video_id)['body']

        m3u8_playlist = try_get(info, lambda x: x['video_urls'][0]['url'])

        formats = self._extract_m3u8_formats(m3u8_playlist, video_id, 'mp4', m3u8_id='hls')

        return {
            'id': video_id,
            'title': info.get('title'),
            'uploader': try_get(info, lambda x: x['user']['username']),
            'description': info.get('description'),
            'view_count': info.get('view_count'),
            'like_count': info.get('like_count'),
            'formats': formats,
            'thumbnail': info.get('thumbnail_url'),
        }
