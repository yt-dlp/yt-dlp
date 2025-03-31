from .common import InfoExtractor
from ..utils import ExtractorError


class GinikoIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?giniko\.com/watch\.php\?id=(?P<id>-?\d+)'
    _TESTS = [{
        'url': 'https://www.giniko.com/watch.php?id=186',
        'info_dict': {
            'id': '186',
            'title': r're:Jordan TV \d{4}-\d{2}-\d{2} \d{2}:\d{2}',
            'ext': 'mp4',
            'is_live': True,
            'live_status': 'is_live',
        },
    }, {
        'url': 'https://www.giniko.com/watch.php?id=-1',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        channel_id = self._match_id(url)
        xml = self._download_xml(f'https://www.giniko.com/xml/secure/plist.php?ch={channel_id}', channel_id)

        title = None
        stream_url = None
        is_live = None
        for dvr in xml.findall('.//array/dict'):
            keys = dvr.findall('key')
            values = dvr.findall('string')

            key_map = {key.text: values[i].text for i, key in enumerate(keys) if i < len(values)}

            is_live = key_map.get('isVOD') == 'false'
            if is_live:
                stream_url = key_map.get('HlsStreamURL')
                title = key_map.get('name', title)
                if isinstance(title, str):
                    title = title.replace(' - Live', '')
                break

        if not stream_url:
            raise ExtractorError('Failed to extract stream')

        return {
            'id': channel_id,
            'title': title,
            'formats': self._extract_m3u8_formats(stream_url, channel_id, 'mp4', m3u8_id='hls', live=True),
            'is_live': is_live,
        }
