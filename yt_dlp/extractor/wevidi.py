from .common import InfoExtractor


class WeVidiIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?wevidi\.net/watch/(?P<id>[0-9A-Za-z_-]{11})'
    _TESTS = [{
        'url': 'https://wevidi.net/watch/UOxjNMyp70w',
        'md5': '59ec2ae20f1168f449f0b19f62296c3b',
        'info_dict': {
            'id': 'UOxjNMyp70w',
            'ext': 'mp4',
            'title': 'Serious Talk: YouTube Alternatives and Free Speech',
            'thumbnail': r're:^https?://.*\.jpg$',
            'description': 'md5:def38c01923e9143cf586ac8ac4229ed',
            'uploader': 'AliTZ13',
            'duration': 423.339,
        }
    }, {
        'url': 'https://wevidi.net/watch/ievRuuQHbPS',
        'md5': 'ce8a94989a959bff9003fa27ee572935',
        'info_dict': {
            'id': 'ievRuuQHbPS',
            'ext': 'mp4',
            'title': 'WeVidi Playlists',
            'thumbnail': r're:^https?://.*\.jpg$',
            'description': 'md5:32cdfca272687390d9bd9b0c9c6153ee',
            'uploader': 'WeVidi',
            'duration': 36.1999,
        }
    }, {
        'url': 'https://wevidi.net/watch/PcMzDWaQSWb',
        'md5': '55ee0d3434be5d9e5cc76b83f2bb57ec',
        'info_dict': {
            'id': 'PcMzDWaQSWb',
            'ext': 'mp4',
            'title': 'Cat blep',
            'thumbnail': r're:^https?://.*\.jpg$',
            'description': 'md5:e2c9e2b54b8bb424cc64937c8fdc068f',
            'uploader': 'WeVidi',
            'duration': 41.972,
        }
    }]

    def _extract_formats(self, webpage):
        # Taken from WeVidi player JS: https://wevidi.net/layouts/default/static/player.min.js
        resolution_map = {
            1: '144p',
            2: '240p',
            3: '360p',
            4: '480p',
            5: '720p',
            6: '1080p'
        }

        srcUID = self._search_regex(r'srcUID: "([0-9A-Za-z_-]{11})"', webpage, 'srcUID')
        srcVID = self._search_regex(r'srcVID: "([0-9A-Za-z_-]{11})"', webpage, 'srcVID')
        srcNAME = self._search_regex(r'srcNAME: "([0-9A-Za-z_-]{11})"', webpage, 'srcNAME')
        resolutions = [int(x) for x in self._search_regex(r'resolutions: \[([\d, ]+)]', webpage, 'resolutions').split(', ') if int(x) > 0]
        formats = []
        for resolution in resolutions:
            format_id = str(-(resolution // -2) - 1)
            formats.append({
                'acodec': 'mp4a.40.2',
                'ext': 'mp4',
                'format_id': format_id,
                'resolution': resolution_map[resolution],
                'url': f'https://www.wevidi.net/videoplayback/{srcVID}/{srcUID}/{srcNAME}/{format_id}',
                'vcodec': 'avc1.42E01E',
            })

        return formats

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        title = self._html_search_regex(r'<strong class="video_title">(.+?)</strong>', webpage, 'title')
        formats = self._extract_formats(webpage)

        return {
            'id': video_id,
            'title': title,
            'description': self._html_search_regex(r'<div class="descr_long">(.+?)</div>', webpage, 'description'),
            'uploader': self._html_search_regex(r'<a href="/user/(.+?)" class="username">', webpage, 'uploader', fatal=False),
            'formats': self._extract_formats(webpage),
            'thumbnail': self._og_search_thumbnail(webpage),
            'duration': float(self._search_regex(r'duration: ([\d.]+)', webpage, 'duration')),
        }
