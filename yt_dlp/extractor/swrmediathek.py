from .common import InfoExtractor
from ..utils import (
    parse_duration,
    int_or_none,
    determine_protocol,
)


class SWRMediathekIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?swrmediathek\.de/(?:content/)?player\.htm\?show=(?P<id>[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})'

    _TESTS = [{
        'url': 'http://swrmediathek.de/player.htm?show=849790d0-dab8-11e3-a953-0026b975f2e6',
        'md5': '8c5f6f0172753368547ca8413a7768ac',
        'info_dict': {
            'id': '849790d0-dab8-11e3-a953-0026b975f2e6',
            'ext': 'mp4',
            'title': 'SWR odysso',
            'description': 'md5:2012e31baad36162e97ce9eb3f157b8a',
            'thumbnail': r're:^http:.*\.jpg$',
            'duration': 2602,
            'upload_date': '20140515',
            'uploader': 'SWR Fernsehen',
            'uploader_id': '990030',
        },
    }, {
        'url': 'http://swrmediathek.de/player.htm?show=0e1a8510-ddf2-11e3-9be3-0026b975f2e6',
        'md5': 'b10ab854f912eecc5a6b55cd6fc1f545',
        'info_dict': {
            'id': '0e1a8510-ddf2-11e3-9be3-0026b975f2e6',
            'ext': 'mp4',
            'title': 'Nachtcafé - Alltagsdroge Alkohol - zwischen Sektempfang und Komasaufen',
            'description': 'md5:e0a3adc17e47db2c23aab9ebc36dbee2',
            'thumbnail': r're:http://.*\.jpg',
            'duration': 5305,
            'upload_date': '20140516',
            'uploader': 'SWR Fernsehen',
            'uploader_id': '990030',
        },
        'skip': 'redirect to http://swrmediathek.de/index.htm?hinweis=swrlink',
    }, {
        'url': 'http://swrmediathek.de/player.htm?show=bba23e10-cb93-11e3-bf7f-0026b975f2e6',
        'md5': '4382e4ef2c9d7ce6852535fa867a0dd3',
        'info_dict': {
            'id': 'bba23e10-cb93-11e3-bf7f-0026b975f2e6',
            'ext': 'mp3',
            'title': 'Saša Stanišic: Vor dem Fest',
            'description': 'md5:5b792387dc3fbb171eb709060654e8c9',
            'thumbnail': r're:http://.*\.jpg',
            'duration': 3366,
            'upload_date': '20140520',
            'uploader': 'SWR 2',
            'uploader_id': '284670',
        },
        'skip': 'redirect to http://swrmediathek.de/index.htm?hinweis=swrlink',
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video = self._download_json(
            'http://swrmediathek.de/AjaxEntry?ekey=%s' % video_id,
            video_id, 'Downloading video JSON')

        attr = video['attr']
        title = attr['entry_title']
        media_type = attr.get('entry_etype')

        formats = []
        for entry in video.get('sub', []):
            if entry.get('name') != 'entry_media':
                continue

            entry_attr = entry.get('attr', {})
            f_url = entry_attr.get('val2')
            if not f_url:
                continue
            codec = entry_attr.get('val0')
            if codec == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    f_url, video_id, 'mp4', 'm3u8_native',
                    m3u8_id='hls', fatal=False))
            elif codec == 'f4m':
                formats.extend(self._extract_f4m_formats(
                    f_url + '?hdcore=3.7.0', video_id,
                    f4m_id='hds', fatal=False))
            else:
                formats.append({
                    'format_id': determine_protocol({'url': f_url}),
                    'url': f_url,
                    'quality': int_or_none(entry_attr.get('val1')),
                    'vcodec': codec if media_type == 'Video' else 'none',
                    'acodec': codec if media_type == 'Audio' else None,
                })

        upload_date = None
        entry_pdatet = attr.get('entry_pdatet')
        if entry_pdatet:
            upload_date = entry_pdatet[:-4]

        return {
            'id': video_id,
            'title': title,
            'description': attr.get('entry_descl'),
            'thumbnail': attr.get('entry_image_16_9'),
            'duration': parse_duration(attr.get('entry_durat')),
            'upload_date': upload_date,
            'uploader': attr.get('channel_title'),
            'uploader_id': attr.get('channel_idkey'),
            'formats': formats,
        }
