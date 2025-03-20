from .common import InfoExtractor

# Speedrun.com has the ability to host twitch embeds as well which is why this
# script was needed.

class SpeedRunIE(InfoExtractor):
    IE_NAME = 'speedrun'
    _VALID_URL = r'https?://(?:www\.)?speedrun\.com/[^/?#]+/runs/(?P<id>[^?/#]+)'

    _TESTS = [{
        'url':'https://www.speedrun.com/smg1/runs/yvnjr9om',
        'only_matching': True,
    }, {
        'url':'https://www.speedrun.com/pm64/runs/y96x462y',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        embed_url = self._search_regex(
            r'<iframe [^>]*class="[^"]*block[^"]+" [^>]*src="([^"]+)', webpage, 'embed url')

        return self.url_result(embed_url)
