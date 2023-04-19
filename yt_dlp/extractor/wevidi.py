from .common import InfoExtractor


class WeVidiIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?wevidi\.net/watch/(?P<id>[0-9A-Za-z_-]{11})'
    # _TESTS = [{
    #     'url': 'https://wevidi.net/watch/UOxjNMyp70w',
    #     'md5': 'TODO: md5 sum of the first 10241 bytes of the video file (use --test)',
    #     'info_dict': {
    #         'id': '42',
    #         'ext': 'mp4',
    #         'title': 'Video title goes here',
    #         'thumbnail': r're:^https?://.*\.jpg$',
    #         # TODO more properties, either as:
    #         # * A value
    #         # * MD5 checksum; start the string with md5:
    #         # * A regular expression; start the string with re:
    #         # * Any Python type, e.g. int or float
    #     }
    # }]

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
        }
