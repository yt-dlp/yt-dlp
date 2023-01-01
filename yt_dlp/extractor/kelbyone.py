from .common import InfoExtractor
from ..utils import int_or_none


class KelbyOneIE(InfoExtractor):
    _VALID_URL = r'https?://members\.kelbyone\.com/course/(?P<id>[^$&?#/]+)'

    _TESTS = [{
        'url': 'https://members.kelbyone.com/course/glyn-dewis-mastering-selections/',
        'playlist_mincount': 1,
        'info_dict': {
            'id': 'glyn-dewis-mastering-selections',
            'title': 'Trailer - Mastering Selections in Photoshop',
        },
        'playlist': [{
            'info_dict': {
                'id': 'MkiOnLqK',
                'ext': 'mp4',
                'title': 'Trailer - Mastering Selections in Photoshop',
                'description': 'md5:d41d8cd98f00b204e9800998ecf8427e',
                'thumbnail': 'https://content.jwplatform.com/v2/media/MkiOnLqK/poster.jpg?width=720',
                'timestamp': 1601568639,
                'duration': 90,
                'upload_date': '20201001',
            },
        }]
    }]

    def _entries(self, playlist):
        for item in playlist:
            video_id = item['mediaid']
            thumbnails = [{
                'url': image.get('src'),
                'width': int_or_none(image.get('width')),
            } for image in item.get('images') or []]
            formats, subtitles = [], {}
            for source in item.get('sources') or []:
                if not source.get('file'):
                    continue
                if source.get('type') == 'application/vnd.apple.mpegurl':
                    fmts, subs = self._extract_m3u8_formats_and_subtitles(source['file'], video_id)
                    formats.extend(fmts)
                    subtitles = self._merge_subtitles(subs, subtitles)
                elif source.get('type') == 'audio/mp4':
                    formats.append({
                        'format_id': source.get('label'),
                        'url': source['file'],
                        'vcodec': 'none',
                    })
                else:
                    formats.append({
                        'format_id': source.get('label'),
                        'height': source.get('height'),
                        'width': source.get('width'),
                        'url': source['file'],
                    })
            for track in item.get('tracks'):
                if track.get('kind') == 'captions' and track.get('file'):
                    subtitles.setdefault('en', []).append({
                        'url': track['file'],
                    })
            yield {
                'id': video_id,
                'title': item['title'],
                'description': item.get('description'),
                'thumbnails': thumbnails,
                'thumbnail': item.get('image'),
                'timestamp': item.get('pubdate'),
                'duration': item.get('duration'),
                'formats': formats,
                'subtitles': subtitles,
            }

    def _real_extract(self, url):
        item_id = self._match_id(url)
        webpage = self._download_webpage(url, item_id)
        playlist_url = self._html_search_regex(r'playlist"\:"(https.*content\.jwplatform\.com.*json)"', webpage, 'playlist url').replace('\\', '')
        course_data = self._download_json(playlist_url, item_id)
        return self.playlist_result(self._entries(course_data['playlist']), item_id,
                                    course_data.get('title'), course_data.get('description'))
