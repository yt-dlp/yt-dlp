from .common import InfoExtractor
from ..utils import smuggle_url


class HTML5MediaEmbedIE(InfoExtractor):
    _VALID_URL = False
    IE_NAME = 'html5'
    _WEBPAGE_TESTS = [
        {
            'url': 'https://html.com/media/',
            'info_dict': {
                'title': 'HTML5 Media',
                'description': 'md5:933b2d02ceffe7a7a0f3c8326d91cc2a',
            },
            'playlist_count': 2
        }
    ]

    def _extract_from_webpage(self, url, webpage):
        video_id, title = self._generic_id(url), self._generic_title(url)
        entries = self._parse_html5_media_entries(url, webpage, video_id, m3u8_id='hls') or []
        for num, entry in enumerate(entries, start=1):
            entry.update({
                'id': f'{video_id}-{num}',
                'title': f'{title} ({num})',
                '_old_archive_ids': [
                    f'Generic {f"{video_id}-{num}" if len(entries) > 1 else video_id}',
                ],
            })
            self._sort_formats(entry['formats'])
            yield entry


class JSONLDEmbedIE(InfoExtractor):
    _VALID_URL = False
    IE_NAME = 'JSON LD'
    _WEBPAGE_TESTS = [
        {
            'note': 'JSON LD with multiple @type',
            'url': 'https://www.nu.nl/280161/video/hoe-een-bladvlo-dit-verwoestende-japanse-onkruid-moet-vernietigen.html',
            'md5': 'c7949f34f57273013fb7ccb1156393db',
            'info_dict': {
                'id': 'ipy2AcGL',
                'ext': 'mp4',
                'description': 'md5:6a9d644bab0dc2dc06849c2505d8383d',
                'thumbnail': 'https://cdn.jwplayer.com/v2/media/ipy2AcGL/poster.jpg?width=720',
                'title': 'Hoe een bladvlo dit verwoestende Japanse onkruid moet vernietigen',
                'timestamp': 1586577474,
                'upload_date': '20200411',
                'duration': 111.0,
            }
        },
    ]

    def _extract_from_webpage(self, url, webpage):
        # Looking for http://schema.org/VideoObject
        video_id = self._generic_id(url)
        json_ld = self._search_json_ld(webpage, video_id, default={})
        if json_ld.get('url') not in (url, None):
            yield {
                **json_ld,
                **{'_type': 'url_transparent', 'url': smuggle_url(json_ld['url'], {'force_videoid': video_id, 'to_generic': True})}
            }
