from .once import OnceIE
from ..compat import compat_urllib_parse_unquote


class GameSpotIE(OnceIE):
    _VALID_URL = r'https?://(?:www\.)?gamespot\.com/(?:video|article|review)s/(?:[^/]+/\d+-|embed/)(?P<id>\d+)'
    _TESTS = [{
        'url': 'http://www.gamespot.com/videos/arma-3-community-guide-sitrep-i/2300-6410818/',
        'md5': 'b2a30deaa8654fcccd43713a6b6a4825',
        'info_dict': {
            'id': 'gs-2300-6410818',
            'ext': 'mp4',
            'title': 'Arma 3 - Community Guide: SITREP I',
            'description': 'Check out this video where some of the basics of Arma 3 is explained.',
        },
        'skip': 'manifest URL give HTTP Error 404: Not Found',
    }, {
        'url': 'http://www.gamespot.com/videos/the-witcher-3-wild-hunt-xbox-one-now-playing/2300-6424837/',
        'md5': '173ea87ad762cf5d3bf6163dceb255a6',
        'info_dict': {
            'id': 'gs-2300-6424837',
            'ext': 'mp4',
            'title': 'Now Playing - The Witcher 3: Wild Hunt',
            'description': 'Join us as we take a look at the early hours of The Witcher 3: Wild Hunt and more.',
        },
    }, {
        'url': 'https://www.gamespot.com/videos/embed/6439218/',
        'only_matching': True,
    }, {
        'url': 'https://www.gamespot.com/articles/the-last-of-us-2-receives-new-ps4-trailer/1100-6454469/',
        'only_matching': True,
    }, {
        'url': 'https://www.gamespot.com/reviews/gears-of-war-review/1900-6161188/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        page_id = self._match_id(url)
        webpage = self._download_webpage(url, page_id)
        data_video = self._parse_json(self._html_search_regex(
            r'data-video=(["\'])({.*?})\1', webpage,
            'video data', group=2), page_id)
        title = compat_urllib_parse_unquote(data_video['title'])
        streams = data_video['videoStreams']
        formats = []

        m3u8_url = streams.get('adaptive_stream')
        if m3u8_url:
            m3u8_formats = self._extract_m3u8_formats(
                m3u8_url, page_id, 'mp4', 'm3u8_native',
                m3u8_id='hls', fatal=False)
            for f in m3u8_formats:
                formats.append(f)
                http_f = f.copy()
                del http_f['manifest_url']
                http_f.update({
                    'format_id': f['format_id'].replace('hls-', 'http-'),
                    'protocol': 'http',
                    'url': f['url'].replace('.m3u8', '.mp4'),
                })
                formats.append(http_f)

        mpd_url = streams.get('adaptive_dash')
        if mpd_url:
            formats.extend(self._extract_mpd_formats(
                mpd_url, page_id, mpd_id='dash', fatal=False))

        self._sort_formats(formats)

        return {
            'id': data_video.get('guid') or page_id,
            'display_id': page_id,
            'title': title,
            'formats': formats,
            'description': self._html_search_meta('description', webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
        }
