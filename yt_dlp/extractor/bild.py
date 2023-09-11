from .common import InfoExtractor
from ..utils import (
    int_or_none,
    traverse_obj,
    unescapeHTML,
)


class BildIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?bild\.de/(?:[^/]+/)+(?P<display_id>[^/]+)-(?P<id>\d+)(?:,auto=true)?\.bild\.html'
    IE_DESC = 'Bild.de'
    _TESTS = [{
        'note': 'static MP4 only',
        'url': 'http://www.bild.de/video/clip/apple-ipad-air/das-koennen-die-neuen-ipads-38184146.bild.html',
        'md5': 'dd495cbd99f2413502a1713a1156ac8a',
        'info_dict': {
            'id': '38184146',
            'ext': 'mp4',
            'title': 'Das können die  neuen iPads',
            'description': 'md5:a4058c4fa2a804ab59c00d7244bbf62f',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 196,
        }
    }, {
        'note': 'static MP4 and HLS',
        'url': 'https://www.bild.de/video/clip/news-ausland/deftiger-abgang-vom-10m-turm-bademeister-sorgt-fuer-skandal-85158620.bild.html',
        'md5': 'fb0ed4f09c495d4ba7ce2eee0bb90de1',
        'info_dict': {
            'id': '85158620',
            'ext': 'mp4',
            'title': 'Der Sprungturm-Skandal',
            'description': 'md5:709b543c24dc31bbbffee73bccda34ad',
            'thumbnail': r're:^https?://.*\.jpg$',
            'duration': 69,
        }
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        video_data = self._download_json(
            url.split('.bild.html')[0] + ',view=json.bild.html', video_id)

        formats = []
        for src in traverse_obj(video_data, ('clipList', 0, 'srces', lambda _, v: v['src'])):
            src_type = src.get('type')
            if src_type == 'application/x-mpegURL':
                formats.extend(
                    self._extract_m3u8_formats(
                        src['src'], video_id, 'mp4', m3u8_id='hls', fatal=False))
            elif src_type == 'video/mp4':
                formats.append({'url': src['src'], 'format_id': 'http-mp4'})
            else:
                self.report_warning(f'Skipping unsupported format type: "{src_type}"')

        return {
            'id': video_id,
            'title': unescapeHTML(video_data['title']).strip(),
            'description': unescapeHTML(video_data.get('description')),
            'formats': formats,
            'thumbnail': video_data.get('poster'),
            'duration': int_or_none(video_data.get('durationSec')),
        }
