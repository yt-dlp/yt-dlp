from .common import InfoExtractor


class SlutloadIE(InfoExtractor):
    _VALID_URL = r'https?://(?:\w+\.)?slutload\.com/(?:video/[^/]+|embed_player|watch)/(?P<id>[^/]+)'
    _TESTS = [{
        'url': 'http://www.slutload.com/video/virginie-baisee-en-cam/TD73btpBqSxc/',
        'md5': '868309628ba00fd488cf516a113fd717',
        'info_dict': {
            'id': 'TD73btpBqSxc',
            'ext': 'mp4',
            'title': 'virginie baisee en cam',
            'age_limit': 18,
            'thumbnail': r're:https?://.*?\.jpg',
        },
    }, {
        # mobile site
        'url': 'http://mobile.slutload.com/video/masturbation-solo/fviFLmc6kzJ/',
        'only_matching': True,
    }, {
        'url': 'http://www.slutload.com/embed_player/TD73btpBqSxc/',
        'only_matching': True,
    }, {
        'url': 'http://www.slutload.com/watch/TD73btpBqSxc/Virginie-Baisee-En-Cam.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        embed_page = self._download_webpage(
            f'http://www.slutload.com/embed_player/{video_id}', video_id,
            'Downloading embed page', fatal=False)

        if embed_page:
            def extract(what):
                return self._html_search_regex(
                    rf'data-video-{what}=(["\'])(?P<url>(?:(?!\1).)+)\1',
                    embed_page, f'video {what}', default=None, group='url')

            video_url = extract('url')
            if video_url:
                title = self._html_search_regex(
                    r'<title>([^<]+)', embed_page, 'title', default=video_id)
                return {
                    'id': video_id,
                    'url': video_url,
                    'title': title,
                    'thumbnail': extract('preview'),
                    'age_limit': 18,
                }

        webpage = self._download_webpage(
            f'http://www.slutload.com/video/_/{video_id}/', video_id)
        title = self._html_search_regex(
            r'<h1><strong>([^<]+)</strong>', webpage, 'title').strip()
        info = self._parse_html5_media_entries(url, webpage, video_id)[0]
        info.update({
            'id': video_id,
            'title': title,
            'age_limit': 18,
        })
        return info
