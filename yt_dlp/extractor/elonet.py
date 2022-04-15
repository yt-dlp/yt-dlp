from .common import InfoExtractor
from ..utils import determine_ext


class ElonetIE(InfoExtractor):
    _VALID_URL = r'https?://elonet\.finna\.fi/Record/kavi\.elonet_elokuva_(?P<id>[0-9]+)'
    _TESTS = [{
        'url': 'https://elonet.finna.fi/Record/kavi.elonet_elokuva_107867',
        'info_dict': {
            'id': '107867',
            'ext': 'mp4',
            'title': 'Valkoinen peura',
            'thumbnail': r're:^https?://elonet\.finna\.fi/Cover/Show\?id=kavi\.elonet_elokuva_107867.+',
            'description': 'md5:bded4201c9677fab10854884fe8f7312',
        },
        'params': {'skip_download': 'dash'},
    }, {
        # DASH with subtitles
        'url': 'https://elonet.finna.fi/Record/kavi.elonet_elokuva_116539',
        'info_dict': {
            'id': '116539',
            'ext': 'mp4',
            'title': 'Minulla on tiikeri',
            'thumbnail': r're:^https?://elonet\.finna\.fi/Cover/Show\?id=kavi\.elonet_elokuva_116539.+',
            'description': 'md5:5ab72b3fe76d3414e46cc8f277104419',
        },
        'params': {'skip_download': 'dash'},
    }, {
        # Page with multiple videos, download the main one
        'url': 'https://elonet.finna.fi/Record/kavi.elonet_elokuva_117396',
        'info_dict': {
            'id': '117396',
            'ext': 'mp4',
            'title': 'Sampo',
            'thumbnail': r're:^https?://elonet\.finna\.fi/Cover/Show\?id=kavi\.elonet_elokuva_117396.+',
            'description': 'md5:ec69572a5b054d0ecafe8086b1fa96f7',
        },
        'params': {'skip_download': 'dash'},
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        src = self._parse_json(self._html_search_regex(
            r'id=\'video-data\'[^>]+data-video-sources="([^"]+)"', webpage, 'json'), video_id)[0]['src']
        ext = determine_ext(src)

        if ext == 'm3u8':
            formats, subtitles = self._extract_m3u8_formats_and_subtitles(src, video_id, fatal=False)
        elif ext == 'mpd':
            formats, subtitles = self._extract_mpd_formats_and_subtitles(src, video_id, fatal=False)
        else:
            formats, subtitles = [], {}
            self.raise_no_formats(f'Unknown streaming format {ext}')
        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': self._og_search_title(webpage),
            'description': self._og_search_description(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
            'formats': formats,
            'subtitles': subtitles,
        }
