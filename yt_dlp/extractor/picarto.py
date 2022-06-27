from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    js_to_json,
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
        self._sort_formats(formats)

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
    _VALID_URL = r'https?://(?:www.)?picarto\.tv/videopopout/(?P<id>[^/?#&]+)'
    _TESTS = [{
        'url': 'https://picarto.tv/videopopout/ArtofZod_2017.12.12.00.13.23.flv',
        'md5': '3ab45ba4352c52ee841a28fb73f2d9ca',
        'info_dict': {
            'id': 'ArtofZod_2017.12.12.00.13.23.flv',
            'ext': 'mp4',
            'title': 'ArtofZod_2017.12.12.00.13.23.flv',
            'thumbnail': r're:^https?://.*\.jpg'
        },
    }, {
        'url': 'https://picarto.tv/videopopout/Plague',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        vod_info = self._parse_json(
            self._search_regex(
                r'(?s)#vod-player["\']\s*,\s*(\{.+?\})\s*\)', webpage,
                'vod player'),
            video_id, transform_source=js_to_json)

        formats = self._extract_m3u8_formats(
            vod_info['vod'], video_id, 'mp4', entry_protocol='m3u8_native',
            m3u8_id='hls')
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': video_id,
            'thumbnail': vod_info.get('vodThumb'),
            'formats': formats,
        }
