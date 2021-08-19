from __future__ import unicode_literals

from .common import InfoExtractor


class WorldStarHipHopIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www|m)\.worldstar(?:candy|hiphop)\.com/(?:videos|android)/video\.php\?.*?\bv=(?P<id>[^&]+)'
    _TESTS = [{
        'url': 'http://www.worldstarhiphop.com/videos/video.php?v=wshh6a7q1ny0G34ZwuIO',
        'md5': '9d04de741161603bf7071bbf4e883186',
        'info_dict': {
            'id': 'wshh6a7q1ny0G34ZwuIO',
            'ext': 'mp4',
            'title': 'KO Of The Week: MMA Fighter Gets Knocked Out By Swift Head Kick!'
        }
    }, {
        'url': 'http://m.worldstarhiphop.com/android/video.php?v=wshh6a7q1ny0G34ZwuIO',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        entries = self._parse_html5_media_entries(url, webpage, video_id)

        if not entries:
            return self.url_result(url, 'Generic')

        title = self._html_search_regex(
            [r'(?s)<div class="content-heading">\s*<h1>(.*?)</h1>',
             r'<span[^>]+class="tc-sp-pinned-title">(.*)</span>'],
            webpage, 'title')

        info = entries[0]
        info.update({
            'id': video_id,
            'title': title,
        })
        return info
