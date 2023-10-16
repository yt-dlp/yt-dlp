import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    str_or_none,
    traverse_obj,
)


class PicartoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www.)?picarto\.tv/(?P<id>[a-zA-Z0-9]+)'
    _TEST = {
        'url': 'https://picarto.tv/Setz',
        'info_dict': {
            'id': 'Setz',
            'ext': 'mp4',
            'title': 're:^Setz [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}$',
            'timestamp': int,
            'is_live': True
        },
        'skip': 'Stream is offline',
    }

    @classmethod
    def suitable(cls, url):
        return False if PicartoVodIE.suitable(url) else super(PicartoIE, cls).suitable(url)

    def _real_extract(self, url):
        channel_id = self._match_id(url)

        data = self._download_json(
            'https://ptvintern.picarto.tv/ptvapi', channel_id, query={
                'query': '''{
  channel(name: "%s") {
    adult
    id
    online
    stream_name
    title
  }
  getLoadBalancerUrl(channel_name: "%s") {
    url
  }
}''' % (channel_id, channel_id),
            })['data']
        metadata = data['channel']

        if metadata.get('online') == 0:
            raise ExtractorError('Stream is offline', expected=True)
        title = metadata['title']

        cdn_data = self._download_json(
            data['getLoadBalancerUrl']['url'] + '/stream/json_' + metadata['stream_name'] + '.js',
            channel_id, 'Downloading load balancing info')

        formats = []
        for source in (cdn_data.get('source') or []):
            source_url = source.get('url')
            if not source_url:
                continue
            source_type = source.get('type')
            if source_type == 'html5/application/vnd.apple.mpegurl':
                formats.extend(self._extract_m3u8_formats(
                    source_url, channel_id, 'mp4', m3u8_id='hls', fatal=False))
            elif source_type == 'html5/video/mp4':
                formats.append({
                    'url': source_url,
                })

        mature = metadata.get('adult')
        if mature is None:
            age_limit = None
        else:
            age_limit = 18 if mature is True else 0

        return {
            'id': channel_id,
            'title': title.strip(),
            'is_live': True,
            'channel': channel_id,
            'channel_id': metadata.get('id'),
            'channel_url': 'https://picarto.tv/%s' % channel_id,
            'age_limit': age_limit,
            'formats': formats,
        }


class PicartoVodIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?picarto\.tv/(?:videopopout|\w+/videos)/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://picarto.tv/videopopout/ArtofZod_2017.12.12.00.13.23.flv',
        'md5': '3ab45ba4352c52ee841a28fb73f2d9ca',
        'info_dict': {
            'id': 'ArtofZod_2017.12.12.00.13.23.flv',
            'ext': 'mp4',
            'title': 'ArtofZod_2017.12.12.00.13.23.flv',
            'thumbnail': r're:^https?://.*\.jpg'
        },
        'skip': 'The VOD does not exist',
    }, {
        'url': 'https://picarto.tv/ArtofZod/videos/772650',
        'md5': '00067a0889f1f6869cc512e3e79c521b',
        'info_dict': {
            'id': '772650',
            'ext': 'mp4',
            'title': 'Art of Zod - Drawing and Painting',
            'thumbnail': r're:^https?://.*\.jpg',
            'channel': 'ArtofZod',
            'age_limit': 18,
        }
    }, {
        'url': 'https://picarto.tv/videopopout/Plague',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        data = self._download_json(
            'https://ptvintern.picarto.tv/ptvapi', video_id, query={
                'query': f'''{{
  video(id: "{video_id}") {{
    id
    title
    adult
    file_name
    video_recording_image_url
    channel {{
      name
    }}
  }}
}}'''
            })['data']['video']

        file_name = data['file_name']
        netloc = urllib.parse.urlparse(data['video_recording_image_url']).netloc

        formats = self._extract_m3u8_formats(
            f'https://{netloc}/stream/hls/{file_name}/index.m3u8', video_id, 'mp4', m3u8_id='hls')

        return {
            'id': video_id,
            **traverse_obj(data, {
                'id': ('id', {str_or_none}),
                'title': ('title', {str}),
                'thumbnail': 'video_recording_image_url',
                'channel': ('channel', 'name', {str}),
                'age_limit': ('adult', {lambda x: 18 if x else 0}),
            }),
            'formats': formats,
        }
